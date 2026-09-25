"""N2 - Requirement Normalization (contracts/orchestration-state-machine.md)."""

from __future__ import annotations

import sqlite3
import threading

from src.orchestration.clock import Clock
from src.orchestration.engine import OrchestrationEngine, retry_with_backoff


def _normalize_text(raw_input: str) -> str:
    """Minimal normalization: trim whitespace and collapse internal whitespace runs.

    This is intentionally simple for the assessment's scope — the contract this
    node must satisfy is "produces a non-null normalized_description", not a
    sophisticated NLP pipeline.
    """
    return " ".join(raw_input.split())


def normalize_requirement(
    engine: OrchestrationEngine,
    conn: sqlite3.Connection,
    lock: threading.Lock,
    run_id: str,
    requirement_id: str,
    clock: Clock,
) -> str:
    """N2: transform raw_input into normalized_description, then transition to N3.

    Uses the shared retry utility (T040/ADR-007) for transient failures.
    """

    def _do_normalize() -> str:
        with lock:
            row = conn.execute(
                "SELECT raw_input FROM requirements WHERE requirement_id = ?", (requirement_id,)
            ).fetchone()
        return _normalize_text(row["raw_input"])

    normalized = retry_with_backoff(_do_normalize, clock=clock, max_attempts=3, base_backoff_ms=200)

    with lock:
        conn.execute(
            "UPDATE requirements SET normalized_description = ? WHERE requirement_id = ?",
            (normalized, requirement_id),
        )
        conn.commit()

    engine.transition(run_id, to_stage="N3", status="running", action="requirement_normalized")
    return normalized
