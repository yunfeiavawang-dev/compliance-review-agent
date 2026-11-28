"""Enterprise audit logger for compliance-grade traceability.

Financial regulators (MAS, HKMA, OCC) require that every human action
on a compliance case is recorded with: who, what, when, from where,
and with what authority. This logger supplements the existing
LangGraph audit_trail (which captures AI steps) with structured
records of human operations.

Storage: SQLite for the demo; in production this would write to an
append-only, tamper-evident store (e.g. AWS QLDB, immutable database
table with row-level encryption).

Key design choices:
  - Append-only: no UPDATE or DELETE on audit records
  - Actor identity: user_id + role + tenant from RBAC UserContext
  - IP capture: for access-pattern anomaly detection
  - Action taxonomy: standardized verbs for regulatory reporting
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Optional

from src.auth.rbac import UserContext, get_current_user


class AuditAction(str, Enum):
    """Standardized action taxonomy for regulatory reporting."""
    # Authentication
    LOGIN = "login"
    LOGOUT = "logout"
    SESSION_START = "session_start"

    # Case lifecycle
    CASE_VIEW = "case_view"
    CASE_START_REVIEW = "case_start_review"
    CASE_SUBMIT_DECISION = "case_submit_decision"
    CASE_OVERRIDE_AI = "case_override_ai"
    CASE_ESCALATE = "case_escalate"
    CASE_EXPORT = "case_export"

    # Information handling
    INFO_SUBMIT = "info_submit"
    DOCUMENT_VIEW = "document_view"
    PII_ACCESS = "pii_access"

    # Access control
    PERMISSION_DENIED = "permission_denied"

    # Administrative
    SETTING_CHANGE = "setting_change"
    USER_ROLE_CHANGE = "user_role_change"
    AUDIT_LOG_EXPORT = "audit_log_export"


ENTERPRISE_AUDIT_SCHEMA = """
CREATE TABLE IF NOT EXISTS enterprise_audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    user_id TEXT NOT NULL,
    username TEXT NOT NULL,
    role TEXT NOT NULL,
    tenant_id TEXT NOT NULL,
    ip_address TEXT,
    action TEXT NOT NULL,
    resource_type TEXT,
    resource_id TEXT,
    details TEXT,
    risk_level TEXT,
    ai_decision TEXT,
    human_decision TEXT,
    ai_human_agreement INTEGER,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_audit_user ON enterprise_audit_log(user_id);
CREATE INDEX IF NOT EXISTS idx_audit_tenant ON enterprise_audit_log(tenant_id);
CREATE INDEX IF NOT EXISTS idx_audit_action ON enterprise_audit_log(action);
CREATE INDEX IF NOT EXISTS idx_audit_resource ON enterprise_audit_log(resource_type, resource_id);
CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON enterprise_audit_log(timestamp);
"""


class AuditLogger:
    """Append-only audit logger for human operations.

    Every method captures the full actor context (user, role, tenant,
    IP) automatically from the RBAC module, so callers only need to
    describe *what* happened.

    Usage:
        logger = AuditLogger()
        logger.log_case_action(
            action=AuditAction.CASE_SUBMIT_DECISION,
            case_id="KYC-2024-001",
            details={"decision": "approve", "notes": "All clear"},
        )
    """

    def __init__(self, db_path: str = "data/compliance.db"):
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _init_schema(self):
        conn = sqlite3.connect(self.db_path)
        conn.executescript(ENTERPRISE_AUDIT_SCHEMA)
        conn.commit()
        conn.close()

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def log(
        self,
        action: AuditAction,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
        user: Optional[UserContext] = None,
        risk_level: Optional[str] = None,
        ai_decision: Optional[str] = None,
        human_decision: Optional[str] = None,
    ) -> int:
        """Record an audit event. Returns the log entry ID."""
        if user is None:
            user = get_current_user()

        ai_human_agree = None
        if ai_decision and human_decision:
            ai_human_agree = 1 if ai_decision == human_decision else 0

        conn = self._get_conn()
        cursor = conn.execute(
            """INSERT INTO enterprise_audit_log
               (timestamp, user_id, username, role, tenant_id, ip_address,
                action, resource_type, resource_id, details,
                risk_level, ai_decision, human_decision, ai_human_agreement)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                datetime.now(timezone.utc).isoformat(),
                user.user_id,
                user.username,
                user.role.value,
                user.tenant_id,
                user.ip_address,
                action.value,
                resource_type,
                resource_id,
                json.dumps(details, default=str) if details else None,
                risk_level,
                ai_decision,
                human_decision,
                ai_human_agree,
            ),
        )
        log_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return log_id

    def log_case_action(
        self,
        action: AuditAction,
        case_id: str,
        details: Optional[dict[str, Any]] = None,
        **kwargs,
    ) -> int:
        """Convenience wrapper for case-related actions."""
        return self.log(
            action=action,
            resource_type="case",
            resource_id=case_id,
            details=details,
            **kwargs,
        )

    def query_by_case(self, case_id: str, limit: int = 100) -> list[dict]:
        """Retrieve audit history for a specific case (regulatory inquiry)."""
        conn = self._get_conn()
        rows = conn.execute(
            """SELECT * FROM enterprise_audit_log
               WHERE resource_type = 'case' AND resource_id = ?
               ORDER BY timestamp DESC LIMIT ?""",
            (case_id, limit),
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def query_by_user(self, user_id: str, limit: int = 100) -> list[dict]:
        """Retrieve all actions by a specific user (compliance review)."""
        conn = self._get_conn()
        rows = conn.execute(
            """SELECT * FROM enterprise_audit_log
               WHERE user_id = ? ORDER BY timestamp DESC LIMIT ?""",
            (user_id, limit),
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def query_overrides(self, tenant_id: Optional[str] = None, limit: int = 50) -> list[dict]:
        """Find all cases where human overrode AI — key regulatory metric."""
        conn = self._get_conn()
        query = """SELECT * FROM enterprise_audit_log
                   WHERE ai_human_agreement = 0"""
        params: list = []
        if tenant_id:
            query += " AND tenant_id = ?"
            params.append(tenant_id)
        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)
        rows = conn.execute(query, params).fetchall()
        conn.close()
        return [dict(r) for r in rows]
