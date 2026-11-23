"""Database CRUD operations for compliance review system."""

from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime, timezone
from typing import Optional


def generate_id(prefix: str = "") -> str:
    return f"{prefix}{uuid.uuid4().hex[:8]}"


def create_customer(conn: sqlite3.Connection, data: dict) -> str:
    customer_id = generate_id("CUST-")
    conn.execute(
        """INSERT INTO customers
           (customer_id, customer_type, full_name, nationality, country_of_residence,
            date_of_birth, occupation, employer, annual_income, income_currency)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (customer_id, data.get("type", "individual"), data["full_name"],
         data.get("nationality"), data.get("country_of_residence"),
         data.get("date_of_birth"), data.get("occupation"),
         data.get("employer"), data.get("annual_income"),
         data.get("income_currency", "USD")),
    )
    conn.commit()
    return customer_id


def get_customer(conn: sqlite3.Connection, customer_id: str) -> dict | None:
    row = conn.execute("SELECT * FROM customers WHERE customer_id = ?", (customer_id,)).fetchone()
    return dict(row) if row else None


def create_review(conn: sqlite3.Connection, case_id: str, customer_id: str, submitted_at: str = None) -> str:
    review_id = generate_id("REV-")
    conn.execute(
        """INSERT INTO reviews (review_id, case_id, customer_id, submitted_at)
           VALUES (?, ?, ?, ?)""",
        (review_id, case_id, customer_id, submitted_at or datetime.now(timezone.utc).isoformat()),
    )
    conn.commit()
    return review_id


def update_review(conn: sqlite3.Connection, review_id: str, **fields) -> None:
    fields["updated_at"] = datetime.now(timezone.utc).isoformat()
    set_clause = ", ".join(f"{k} = ?" for k in fields)
    values = list(fields.values()) + [review_id]
    conn.execute(f"UPDATE reviews SET {set_clause} WHERE review_id = ?", values)
    conn.commit()


def get_review(conn: sqlite3.Connection, review_id: str) -> dict | None:
    row = conn.execute("SELECT * FROM reviews WHERE review_id = ?", (review_id,)).fetchone()
    return dict(row) if row else None


def get_review_by_case(conn: sqlite3.Connection, case_id: str) -> dict | None:
    row = conn.execute("SELECT * FROM reviews WHERE case_id = ?", (case_id,)).fetchone()
    return dict(row) if row else None


def add_document(conn: sqlite3.Connection, review_id: str, doc: dict) -> int:
    cursor = conn.execute(
        """INSERT INTO documents
           (review_id, document_type, document_category, document_number,
            issuing_country, issue_date, expiry_date, verified, verification_notes)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (review_id, doc["type"], doc.get("category"), doc.get("document_number"),
         doc.get("issuing_country"), doc.get("issue_date"), doc.get("expiry_date"),
         doc.get("verified", False), doc.get("verification_notes")),
    )
    conn.commit()
    return cursor.lastrowid


def add_screening_result(conn: sqlite3.Connection, review_id: str, screening: dict) -> int:
    cursor = conn.execute(
        """INSERT INTO screening_results
           (review_id, screening_type, result, matched_list, match_confidence,
            match_details, disposition)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (review_id, screening["screening_type"], screening["result"],
         screening.get("matched_list"), screening.get("match_confidence"),
         screening.get("match_details"), screening.get("disposition", "pending")),
    )
    conn.commit()
    return cursor.lastrowid


def add_risk_assessment(conn: sqlite3.Connection, review_id: str, assessment: dict) -> int:
    total = sum(assessment.get(k, 0) for k in
                ["customer_type_score", "geography_score", "product_score",
                 "transaction_score", "source_of_funds_score"])
    if total <= 8:
        calculated_rating = "low"
    elif total <= 12:
        calculated_rating = "medium"
    else:
        calculated_rating = "high"

    cursor = conn.execute(
        """INSERT INTO risk_assessments
           (review_id, customer_type_score, geography_score, product_score,
            transaction_score, source_of_funds_score, total_score, calculated_rating,
            override_rating, override_reason, assessed_by)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (review_id, assessment.get("customer_type_score"),
         assessment.get("geography_score"), assessment.get("product_score"),
         assessment.get("transaction_score"), assessment.get("source_of_funds_score"),
         total, calculated_rating,
         assessment.get("override_rating"), assessment.get("override_reason"),
         assessment.get("assessed_by", "system")),
    )
    conn.commit()
    return cursor.lastrowid


def add_audit_log(conn: sqlite3.Connection, review_id: str, step_name: str, action: str,
                  details: str = None, sources_used: str = None, performed_by: str = "system") -> int:
    cursor = conn.execute(
        """INSERT INTO audit_log (review_id, step_name, action, details, sources_used, performed_by)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (review_id, step_name, action, details, sources_used, performed_by),
    )
    conn.commit()
    return cursor.lastrowid


def get_audit_log(conn: sqlite3.Connection, review_id: str) -> list[dict]:
    rows = conn.execute(
        "SELECT * FROM audit_log WHERE review_id = ? ORDER BY timestamp", (review_id,)
    ).fetchall()
    return [dict(r) for r in rows]


def get_screening_results(conn: sqlite3.Connection, review_id: str) -> list[dict]:
    rows = conn.execute(
        "SELECT * FROM screening_results WHERE review_id = ?", (review_id,)
    ).fetchall()
    return [dict(r) for r in rows]


def get_risk_assessment(conn: sqlite3.Connection, review_id: str) -> dict | None:
    row = conn.execute(
        "SELECT * FROM risk_assessments WHERE review_id = ? ORDER BY assessed_at DESC LIMIT 1",
        (review_id,),
    ).fetchone()
    return dict(row) if row else None


def add_review_note(conn: sqlite3.Connection, review_id: str, author: str,
                    content: str, note_type: str = "comment") -> int:
    cursor = conn.execute(
        "INSERT INTO review_notes (review_id, author, content, note_type) VALUES (?, ?, ?, ?)",
        (review_id, author, content, note_type),
    )
    conn.commit()
    return cursor.lastrowid
