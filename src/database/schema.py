"""SQLite database schema for the compliance review system."""

import sqlite3
from pathlib import Path

SCHEMA_SQL = """
-- Customer profiles
CREATE TABLE IF NOT EXISTS customers (
    customer_id TEXT PRIMARY KEY,
    customer_type TEXT NOT NULL CHECK(customer_type IN ('individual', 'corporate')),
    full_name TEXT NOT NULL,
    nationality TEXT,
    country_of_residence TEXT,
    date_of_birth TEXT,
    occupation TEXT,
    employer TEXT,
    annual_income REAL,
    income_currency TEXT DEFAULT 'USD',
    risk_rating TEXT CHECK(risk_rating IN ('low', 'medium', 'high')),
    risk_score INTEGER,
    status TEXT DEFAULT 'pending' CHECK(status IN ('pending', 'active', 'suspended', 'closed')),
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now'))
);

-- KYC review cases
CREATE TABLE IF NOT EXISTS reviews (
    review_id TEXT PRIMARY KEY,
    case_id TEXT NOT NULL UNIQUE,
    customer_id TEXT NOT NULL,
    review_type TEXT NOT NULL DEFAULT 'onboarding',
    status TEXT DEFAULT 'pending' CHECK(status IN (
        'pending', 'in_progress', 'awaiting_info',
        'under_review', 'escalated', 'approved', 'rejected'
    )),
    assigned_analyst TEXT,
    risk_rating TEXT CHECK(risk_rating IN ('low', 'medium', 'high')),
    risk_score INTEGER,
    due_diligence_level TEXT CHECK(due_diligence_level IN ('standard', 'enhanced', 'simplified')),
    decision TEXT CHECK(decision IN ('approve', 'reject', 'request_more_info', 'escalate')),
    decision_rationale TEXT,
    submitted_at TEXT,
    started_at TEXT,
    completed_at TEXT,
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
);

-- Identification documents submitted for review
CREATE TABLE IF NOT EXISTS documents (
    document_id INTEGER PRIMARY KEY AUTOINCREMENT,
    review_id TEXT NOT NULL,
    document_type TEXT NOT NULL,
    document_category TEXT,
    document_number TEXT,
    issuing_country TEXT,
    issue_date TEXT,
    expiry_date TEXT,
    verified BOOLEAN DEFAULT FALSE,
    verification_notes TEXT,
    created_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (review_id) REFERENCES reviews(review_id)
);

-- Screening results (sanctions, PEP, adverse media)
CREATE TABLE IF NOT EXISTS screening_results (
    screening_id INTEGER PRIMARY KEY AUTOINCREMENT,
    review_id TEXT NOT NULL,
    screening_type TEXT NOT NULL CHECK(screening_type IN ('sanctions', 'pep', 'adverse_media')),
    result TEXT NOT NULL CHECK(result IN ('clear', 'potential_match', 'confirmed_match')),
    matched_list TEXT,
    match_confidence REAL,
    match_details TEXT,
    disposition TEXT CHECK(disposition IN ('pending', 'dismissed', 'confirmed', 'escalated')),
    disposition_reason TEXT,
    screened_at TEXT DEFAULT (datetime('now')),
    resolved_at TEXT,
    resolved_by TEXT,
    FOREIGN KEY (review_id) REFERENCES reviews(review_id)
);

-- Risk assessment breakdown
CREATE TABLE IF NOT EXISTS risk_assessments (
    assessment_id INTEGER PRIMARY KEY AUTOINCREMENT,
    review_id TEXT NOT NULL,
    customer_type_score INTEGER CHECK(customer_type_score BETWEEN 1 AND 3),
    geography_score INTEGER CHECK(geography_score BETWEEN 1 AND 3),
    product_score INTEGER CHECK(product_score BETWEEN 1 AND 3),
    transaction_score INTEGER CHECK(transaction_score BETWEEN 1 AND 3),
    source_of_funds_score INTEGER CHECK(source_of_funds_score BETWEEN 1 AND 3),
    total_score INTEGER,
    calculated_rating TEXT,
    override_rating TEXT,
    override_reason TEXT,
    assessed_at TEXT DEFAULT (datetime('now')),
    assessed_by TEXT,
    FOREIGN KEY (review_id) REFERENCES reviews(review_id)
);

-- Audit trail of all review steps and decisions
CREATE TABLE IF NOT EXISTS audit_log (
    log_id INTEGER PRIMARY KEY AUTOINCREMENT,
    review_id TEXT NOT NULL,
    step_name TEXT NOT NULL,
    action TEXT NOT NULL,
    details TEXT,
    sources_used TEXT,
    performed_by TEXT DEFAULT 'system',
    timestamp TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (review_id) REFERENCES reviews(review_id)
);

-- Review notes and comments
CREATE TABLE IF NOT EXISTS review_notes (
    note_id INTEGER PRIMARY KEY AUTOINCREMENT,
    review_id TEXT NOT NULL,
    author TEXT NOT NULL,
    content TEXT NOT NULL,
    note_type TEXT DEFAULT 'comment' CHECK(note_type IN ('comment', 'decision', 'escalation', 'info_request')),
    created_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (review_id) REFERENCES reviews(review_id)
);
"""


def init_database(db_path: str = "data/compliance.db") -> sqlite3.Connection:
    """Initialize the database with the schema."""
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA_SQL)
    conn.commit()
    return conn


def get_connection(db_path: str = "data/compliance.db") -> sqlite3.Connection:
    """Get a database connection."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn
