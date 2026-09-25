"""N1 - Requirement Ingestion (contracts/orchestration-state-machine.md, FR-ORC-001)."""

from __future__ import annotations

import sqlite3
import threading
from dataclasses import dataclass
from datetime import datetime, timezone

from src.orchestration.engine import OrchestrationEngine
from src.persistence.orchestration_store import new_id


class EmptyRequirementError(ValueError):
    """Raised when raw_input is empty/whitespace-only; no WorkflowInstance is created."""


@dataclass
class IngestionResult:
    run_id: str
    requirement_id: str


def ingest_requirement(
    engine: OrchestrationEngine,
    conn: sqlite3.Connection,
    lock: threading.Lock,
    raw_input: str,
) -> IngestionResult:
    """N1: accept raw requirement text, create Requirement + WorkflowInstance.

    Permanent failure (empty input) is rejected before any WorkflowInstance
    is created — this is a validation rejection, not a transient/retryable
    condition (contracts/orchestration-state-machine.md N1).
    """
    if not raw_input or not raw_input.strip():
        raise EmptyRequirementError("raw_input must not be empty")

    requirement_id = new_id()
    with lock:
        conn.execute(
            "INSERT INTO requirements (requirement_id, raw_input, created_at) VALUES (?, ?, ?)",
            (requirement_id, raw_input, datetime.now(timezone.utc).isoformat()),
        )
        conn.commit()

    instance = engine.create_workflow(requirement_id=requirement_id, initial_stage="N1")
    engine.transition(instance.run_id, to_stage="N2", status="running", action="requirement_ingested")

    return IngestionResult(run_id=instance.run_id, requirement_id=requirement_id)
