"""Long-term memory: policy version tracking (intentionally thin).

Design decision
---------------
Long-term memory intentionally kept thin. Knowledge reuse is handled through
retrospective case review documents ingested into RAG
(see ``src/knowledge/documents/case_reviews/``), not opaque memory entries.

Why: an earlier iteration stored free-form "experience" and "precedent" rows
(edge-case learnings, observed patterns, confidence scores) and recalled them
into the prompt. Those entries were hard to audit, hard to correct, and could
not be traced back to a human-reviewed source, which is a poor fit for a
compliance setting. Retrospective documents are human-readable, reviewable,
versioned, and retrieved through the same cited RAG path as policy text.

The one thing that does not fit a RAG document is a small structured fact:
"which policy version was active when case X was reviewed". That is what this
layer stores, and nothing else. It is metadata for audit/reproducibility, not
context injected into the agent's prompt.

Per-case state lives in ``short_term.SessionMemory``; customer data and the
audit trail live in the main SQLite tables.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Optional


# NOTE: the legacy ``agent_memory`` table (experience / precedent storage) is
# no longer created or written by this module. Existing databases may still
# contain it; it is simply ignored.
POLICY_VERSION_SCHEMA = """
CREATE TABLE IF NOT EXISTS policy_version_log (
    log_id INTEGER PRIMARY KEY AUTOINCREMENT,
    case_id TEXT NOT NULL,
    document_id TEXT NOT NULL,
    version TEXT NOT NULL,
    recorded_at TEXT DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_policy_version_case ON policy_version_log(case_id);
"""


class LongTermMemory:
    """Thin SQLite-backed record of policy versions used per reviewed case."""

    def __init__(self, db_path: str = "data/compliance.db"):
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(db_path)
        conn.executescript(POLICY_VERSION_SCHEMA)
        conn.commit()
        conn.close()

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def record_policy_version(self, case_id: str, document_id: str, version: str) -> int:
        """Record that ``document_id`` at ``version`` was active for ``case_id``."""
        conn = self._get_conn()
        cursor = conn.execute(
            "INSERT INTO policy_version_log (case_id, document_id, version) VALUES (?, ?, ?)",
            (case_id, document_id, version),
        )
        conn.commit()
        log_id = cursor.lastrowid
        conn.close()
        return log_id

    def get_policy_versions(self, case_id: str) -> list[dict]:
        """Return the policy versions recorded for a case."""
        conn = self._get_conn()
        rows = conn.execute(
            "SELECT document_id, version, recorded_at FROM policy_version_log "
            "WHERE case_id = ? ORDER BY log_id",
            (case_id,),
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def get_stats(self) -> dict:
        """Counts for the sidebar: tracked policy versions and cases covered."""
        conn = self._get_conn()
        total = conn.execute("SELECT COUNT(*) FROM policy_version_log").fetchone()[0]
        cases = conn.execute(
            "SELECT COUNT(DISTINCT case_id) FROM policy_version_log"
        ).fetchone()[0]
        conn.close()
        return {"policy_versions_tracked": total, "cases_covered": cases}

    # --- Removed in the "keep memory thin" refactor -------------------------
    # store(), recall(), recall_for_context(), store_review_outcome():
    # free-form experience/precedent memory. Replaced by retrospective
    # documents in RAG (see module docstring).
