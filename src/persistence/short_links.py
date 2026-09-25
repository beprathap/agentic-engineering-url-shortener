"""Repository for ShortLink and RedirectEvent persistence (data-model.md, ADR-014)."""

from __future__ import annotations

import sqlite3
import threading
from dataclasses import dataclass
from datetime import datetime


@dataclass
class ShortLink:
    short_code: str
    target_url: str
    created_at: datetime
    expires_at: datetime | None
    status: str
    idempotency_key: str | None = None


def _to_iso(dt: datetime | None) -> str | None:
    return dt.isoformat() if dt is not None else None


def _from_iso(s: str | None) -> datetime | None:
    return datetime.fromisoformat(s) if s is not None else None


class ShortLinkRepository:
    """Thread-safe wrapper around a single shared SQLite connection.

    Python's sqlite3.Connection is not safe for concurrent statement execution
    from multiple threads even with check_same_thread=False (it serializes at
    the C level in a way that raises InterfaceError under real concurrent
    access, not just under simulated failure). A single lock around each
    logical operation serializes access to this connection; the connection
    itself is a WAL-mode SQLite file with real transactional guarantees
    (ADR-003), so this preserves genuine durability under concurrent load
    rather than merely working around a thread-safety bug (FR-SVC-009).
    """

    def __init__(self, conn: sqlite3.Connection):
        self._conn = conn
        self._lock = threading.Lock()

    def is_active_code_taken(self, short_code: str) -> bool:
        with self._lock:
            row = self._conn.execute(
                "SELECT 1 FROM short_links WHERE short_code = ? AND status = 'active'",
                (short_code,),
            ).fetchone()
            return row is not None

    def find_by_idempotency_key(self, idempotency_key: str) -> ShortLink | None:
        with self._lock:
            row = self._conn.execute(
                "SELECT * FROM short_links WHERE idempotency_key = ?",
                (idempotency_key,),
            ).fetchone()
            return self._row_to_link(row) if row else None

    def create(self, link: ShortLink) -> None:
        with self._lock:
            self._conn.execute(
                """
                INSERT INTO short_links (short_code, target_url, created_at, expires_at, status, idempotency_key)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    link.short_code,
                    link.target_url,
                    _to_iso(link.created_at),
                    _to_iso(link.expires_at),
                    link.status,
                    link.idempotency_key,
                ),
            )
            self._conn.commit()

    def get(self, short_code: str) -> ShortLink | None:
        with self._lock:
            row = self._conn.execute(
                "SELECT * FROM short_links WHERE short_code = ?",
                (short_code,),
            ).fetchone()
            return self._row_to_link(row) if row else None

    def record_redirect_event(self, short_code: str, occurred_at: datetime, outcome: str) -> None:
        with self._lock:
            self._conn.execute(
                "INSERT INTO redirect_events (short_code, occurred_at, outcome) VALUES (?, ?, ?)",
                (short_code, _to_iso(occurred_at), outcome),
            )
            self._conn.commit()

    def get_analytics(self, short_code: str) -> tuple[int, datetime | None]:
        with self._lock:
            row = self._conn.execute(
                """
                SELECT COUNT(*) AS redirect_count, MAX(occurred_at) AS last_accessed_at
                FROM redirect_events
                WHERE short_code = ? AND outcome = 'redirected'
                """,
                (short_code,),
            ).fetchone()
            count = row["redirect_count"] if row else 0
            last_accessed = _from_iso(row["last_accessed_at"]) if row and row["last_accessed_at"] else None
            return count, last_accessed

    @staticmethod
    def _row_to_link(row: sqlite3.Row) -> ShortLink:
        return ShortLink(
            short_code=row["short_code"],
            target_url=row["target_url"],
            created_at=_from_iso(row["created_at"]),
            expires_at=_from_iso(row["expires_at"]),
            status=row["status"],
            idempotency_key=row["idempotency_key"],
        )
