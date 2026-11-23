"""Short-term memory: per-review session state.

Tracks the current review's conversation context, intermediate findings,
and pending questions. Isolated between reviews — one session per case.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


class SessionMemory:
    """In-memory session state for a single KYC review."""

    def __init__(self, case_id: str):
        self.case_id = case_id
        self.created_at = datetime.now(timezone.utc).isoformat()
        self._conversation: list[dict] = []
        self._findings: list[dict] = []
        self._pending_questions: list[str] = []
        self._context: dict[str, Any] = {}

    def add_message(self, role: str, content: str, step: str = "") -> None:
        self._conversation.append({
            "role": role,
            "content": content,
            "step": step,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

    def add_finding(self, finding: str, source: str = "", severity: str = "info") -> None:
        self._findings.append({
            "finding": finding,
            "source": source,
            "severity": severity,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

    def add_pending_question(self, question: str) -> None:
        self._pending_questions.append(question)

    def resolve_question(self, question: str) -> None:
        if question in self._pending_questions:
            self._pending_questions.remove(question)

    def set_context(self, key: str, value: Any) -> None:
        self._context[key] = value

    def get_context(self, key: str, default: Any = None) -> Any:
        return self._context.get(key, default)

    def get_conversation_summary(self, max_messages: int = 10) -> str:
        recent = self._conversation[-max_messages:]
        lines = []
        for msg in recent:
            prefix = f"[{msg['step']}] " if msg['step'] else ""
            lines.append(f"{prefix}{msg['role']}: {msg['content'][:200]}")
        return "\n".join(lines)

    def get_findings_summary(self) -> str:
        if not self._findings:
            return "No findings recorded yet."
        lines = []
        for f in self._findings:
            source_tag = f" (source: {f['source']})" if f['source'] else ""
            lines.append(f"[{f['severity'].upper()}] {f['finding']}{source_tag}")
        return "\n".join(lines)

    @property
    def pending_questions(self) -> list[str]:
        return list(self._pending_questions)

    @property
    def findings(self) -> list[dict]:
        return list(self._findings)

    def to_dict(self) -> dict:
        return {
            "case_id": self.case_id,
            "created_at": self.created_at,
            "conversation_length": len(self._conversation),
            "findings_count": len(self._findings),
            "pending_questions": self._pending_questions,
            "context_keys": list(self._context.keys()),
        }
