"""SQLite connection management in WAL mode (ADR-003, D-003, CON-002)."""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path


def connect(db_path: str) -> sqlite3.Connection:
    """Open a SQLite connection in WAL mode with foreign keys enforced.

    A distinct, real I/O boundary (not a pure in-memory dict) so persistence
    failures can be genuinely injected and tested (FR-SVC-010).
    """
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    conn.row_factory = sqlite3.Row
    return conn


@contextmanager
def transaction(conn: sqlite3.Connection):
    """Wrap a block of statements in an explicit transaction."""
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise


SCHEMA = """
CREATE TABLE IF NOT EXISTS short_links (
    short_code TEXT PRIMARY KEY,
    target_url TEXT NOT NULL,
    created_at TEXT NOT NULL,
    expires_at TEXT,
    status TEXT NOT NULL CHECK (status IN ('active', 'expired', 'deleted')),
    idempotency_key TEXT
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_short_links_idempotency_key
    ON short_links(idempotency_key) WHERE idempotency_key IS NOT NULL;

CREATE TABLE IF NOT EXISTS redirect_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    short_code TEXT NOT NULL,
    occurred_at TEXT NOT NULL,
    outcome TEXT NOT NULL CHECK (outcome IN ('redirected', 'not_found', 'expired'))
);

CREATE INDEX IF NOT EXISTS idx_redirect_events_short_code
    ON redirect_events(short_code);

CREATE TABLE IF NOT EXISTS workflow_instances (
    run_id TEXT PRIMARY KEY,
    requirement_id TEXT NOT NULL,
    current_stage TEXT NOT NULL,
    status TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS requirements (
    requirement_id TEXT PRIMARY KEY,
    raw_input TEXT NOT NULL,
    normalized_description TEXT,
    classification TEXT,
    quality_check_results TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS decisions (
    decision_id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL,
    decision_type TEXT NOT NULL,
    actor_role_capacity TEXT NOT NULL,
    rationale TEXT NOT NULL,
    conditions TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS audit_events (
    event_id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL,
    actor_type TEXT NOT NULL CHECK (actor_type IN ('human', 'system', 'agent')),
    action TEXT NOT NULL,
    occurred_at TEXT NOT NULL,
    affected_artifact TEXT,
    result TEXT NOT NULL CHECK (result IN ('success', 'failure', 'pending')),
    reason TEXT
);

CREATE TABLE IF NOT EXISTS policy_check_results (
    result_id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL,
    policy_id TEXT NOT NULL,
    policy_version TEXT NOT NULL,
    outcome TEXT NOT NULL CHECK (outcome IN ('PASS', 'FAIL', 'EXCEPTION_REQUESTED', 'NOT_APPLICABLE')),
    evaluated_at TEXT NOT NULL,
    exception_id TEXT
);

CREATE TABLE IF NOT EXISTS policy_exceptions (
    exception_id TEXT PRIMARY KEY,
    applicable_policy TEXT NOT NULL,
    reason TEXT NOT NULL,
    scope TEXT NOT NULL,
    approving_authority TEXT NOT NULL,
    compensating_control TEXT NOT NULL,
    approved_at TEXT NOT NULL,
    expires_at TEXT NOT NULL
);
"""


def init_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA)
    conn.commit()


def ensure_db(db_path: str) -> sqlite3.Connection:
    """Create parent directory if needed, connect, and ensure schema exists."""
    path = Path(db_path)
    if path.parent != Path("."):
        path.parent.mkdir(parents=True, exist_ok=True)
    conn = connect(db_path)
    init_schema(conn)
    return conn
