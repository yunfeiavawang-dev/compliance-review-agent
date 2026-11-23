"""Long-term memory: cross-review accumulated experience.

Stores patterns the agent learns across reviews: common issues, analyst
preferences, edge case precedents, and review quality signals. This is
the agent's own experience, NOT customer data (which lives in the database).
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


MEMORY_SCHEMA = """
CREATE TABLE IF NOT EXISTS agent_memory (
    memory_id INTEGER PRIMARY KEY AUTOINCREMENT,
    category TEXT NOT NULL,
    content TEXT NOT NULL,
    source_case_id TEXT,
    relevance_tags TEXT,
    confidence REAL DEFAULT 1.0,
    access_count INTEGER DEFAULT 0,
    created_at TEXT DEFAULT (datetime('now')),
    last_accessed TEXT,
    expires_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_memory_category ON agent_memory(category);
CREATE INDEX IF NOT EXISTS idx_memory_tags ON agent_memory(relevance_tags);
"""


class LongTermMemory:
    """SQLite-backed long-term memory for the compliance review agent."""

    def __init__(self, db_path: str = "data/compliance.db"):
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(db_path)
        conn.executescript(MEMORY_SCHEMA)
        conn.commit()
        conn.close()

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def store(self, category: str, content: str, source_case_id: str = "",
              tags: list[str] = None, confidence: float = 1.0) -> int:
        """Store a new memory entry."""
        conn = self._get_conn()
        cursor = conn.execute(
            """INSERT INTO agent_memory (category, content, source_case_id, relevance_tags, confidence)
               VALUES (?, ?, ?, ?, ?)""",
            (category, content, source_case_id, ",".join(tags or []), confidence),
        )
        conn.commit()
        memory_id = cursor.lastrowid
        conn.close()
        return memory_id

    def recall(self, category: str = None, tags: list[str] = None,
               limit: int = 5) -> list[dict]:
        """Recall memories matching the category and/or tags."""
        conn = self._get_conn()
        query = "SELECT * FROM agent_memory WHERE 1=1"
        params = []

        if category:
            query += " AND category = ?"
            params.append(category)

        if tags:
            tag_conditions = " OR ".join("relevance_tags LIKE ?" for _ in tags)
            query += f" AND ({tag_conditions})"
            params.extend(f"%{tag}%" for tag in tags)

        query += " ORDER BY confidence DESC, created_at DESC LIMIT ?"
        params.append(limit)

        rows = conn.execute(query, params).fetchall()
        results = []
        for row in rows:
            conn.execute(
                "UPDATE agent_memory SET access_count = access_count + 1, last_accessed = ? WHERE memory_id = ?",
                (datetime.now(timezone.utc).isoformat(), row["memory_id"]),
            )
            results.append(dict(row))

        conn.commit()
        conn.close()
        return results

    def recall_for_context(self, case_tags: list[str], limit: int = 3) -> str:
        """Recall and format memories relevant to the current review context."""
        memories = self.recall(tags=case_tags, limit=limit)
        if not memories:
            return ""

        lines = ["## Relevant past experience:"]
        for m in memories:
            lines.append(f"- [{m['category']}] {m['content']} (confidence: {m['confidence']:.1f})")
        return "\n".join(lines)

    def store_review_outcome(self, case_id: str, outcome: dict) -> None:
        """Store learnings from a completed review."""
        if outcome.get("edge_case_learning"):
            self.store(
                category="edge_case",
                content=outcome["edge_case_learning"],
                source_case_id=case_id,
                tags=outcome.get("tags", []),
                confidence=0.8,
            )

        if outcome.get("pattern_observed"):
            self.store(
                category="pattern",
                content=outcome["pattern_observed"],
                source_case_id=case_id,
                tags=outcome.get("tags", []),
                confidence=0.7,
            )

    def get_stats(self) -> dict:
        """Get memory statistics."""
        conn = self._get_conn()
        total = conn.execute("SELECT COUNT(*) FROM agent_memory").fetchone()[0]
        by_category = conn.execute(
            "SELECT category, COUNT(*) as count FROM agent_memory GROUP BY category"
        ).fetchall()
        conn.close()
        return {
            "total_memories": total,
            "by_category": {row["category"]: row["count"] for row in by_category},
        }
