"""Demonstration-scale reliability metrics (plan.md §Observability and Metrics, FR-ORC-020).

All figures computed here are demonstration-data, explicitly labeled as such
(is_demonstration_data=True everywhere), never presented as production
measurements per Constitution Principle IX / FR-ORC-020.
"""

from __future__ import annotations

import sqlite3
import threading
from dataclasses import dataclass, field
from datetime import datetime

from src.persistence.orchestration_store import AuditEventRepository, WorkflowInstanceRepository


@dataclass
class RecoveryEvent:
    failure_detected_at: datetime
    recovery_start_at: datetime
    recovery_complete_at: datetime | None
    recovered: bool
    recovery_mechanism: str | None = None


@dataclass
class MTTRResult:
    mttr_seconds: float | None  # None (not 0) when there are zero recovered events
    recovered_count: int
    unrecovered_count: int


def compute_mttr(events: list[RecoveryEvent]) -> MTTRResult:
    """MTTR = total recovery duration across RECOVERED events / count of recovered events.

    Unrecovered failures are explicitly excluded from the denominator and
    reported separately, per plan.md's explicit instruction not to blend them.
    """
    recovered = [e for e in events if e.recovered and e.recovery_complete_at is not None]
    unrecovered = [e for e in events if not e.recovered]

    if not recovered:
        return MTTRResult(mttr_seconds=None, recovered_count=0, unrecovered_count=len(unrecovered))

    total_seconds = sum((e.recovery_complete_at - e.recovery_start_at).total_seconds() for e in recovered)
    mttr = total_seconds / len(recovered)
    return MTTRResult(mttr_seconds=mttr, recovered_count=len(recovered), unrecovered_count=len(unrecovered))


@dataclass
class WorkflowMetrics:
    total_workflows: int
    completed_count: int
    safe_stopped_count: int
    success_rate: float | None
    failure_rate: float | None
    retry_frequency: float | None
    is_demonstration_data: bool = field(default=True)


def compute_workflow_metrics(
    workflow_repo: WorkflowInstanceRepository,
    audit_repo: AuditEventRepository,
    conn: sqlite3.Connection,
    lock: threading.Lock,
) -> WorkflowMetrics:
    with lock:
        rows = conn.execute("SELECT run_id, status FROM workflow_instances").fetchall()
        retry_events = conn.execute(
            "SELECT COUNT(*) AS c FROM audit_events WHERE action LIKE '%retry%'"
        ).fetchone()

    total = len(rows)
    completed = sum(1 for r in rows if r["status"] == "completed")
    safe_stopped = sum(1 for r in rows if r["status"] == "safe_stopped")

    success_rate = (completed / total) if total else None
    failure_rate = (safe_stopped / total) if total else None
    retry_frequency = (retry_events["c"] / total) if total else None

    return WorkflowMetrics(
        total_workflows=total,
        completed_count=completed,
        safe_stopped_count=safe_stopped,
        success_rate=success_rate,
        failure_rate=failure_rate,
        retry_frequency=retry_frequency,
        is_demonstration_data=True,
    )
