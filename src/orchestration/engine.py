"""Orchestration engine core: workflow lifecycle and audit-event emission (ADR-005, FR-ORC-014)."""

from __future__ import annotations

from datetime import datetime, timezone

from typing import Callable, TypeVar

from src.orchestration.clock import Clock, SystemClock
from src.persistence.orchestration_store import (
    AuditEvent,
    AuditEventRepository,
    WorkflowInstance,
    WorkflowInstanceRepository,
    new_id,
)

T = TypeVar("T")


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def retry_with_backoff(
    fn: Callable[[], T],
    clock: Clock,
    max_attempts: int = 3,
    base_backoff_ms: int = 200,
) -> T:
    """Bounded retry with exponential backoff (ADR-007, PVT-004 confirmed default).

    Retries only on exception from fn(); the last exception is re-raised once
    max_attempts is exhausted. Backoff is applied via clock.sleep(), so tests
    can inject a FakeClock and assert timing without real delays.
    """
    last_exc: Exception | None = None
    for attempt in range(1, max_attempts + 1):
        try:
            return fn()
        except Exception as exc:  # noqa: BLE001 - intentionally broad: any failure is retryable here
            last_exc = exc
            if attempt < max_attempts:
                backoff_seconds = (base_backoff_ms / 1000.0) * (2 ** (attempt - 1))
                clock.sleep(backoff_seconds)
    assert last_exc is not None
    raise last_exc


def enter_safe_stop(engine: "OrchestrationEngine", run_id: str, reason: str) -> None:
    """Free-function form of engine.safe_stop, for call sites that don't hold an engine reference."""
    engine.safe_stop(run_id, reason)


class OrchestrationEngine:
    """Sequential edge traversal + audit-event emission per transition.

    Parallel fan-out/synchronization (N9->N10/N11/N12->N13) is layered on top
    of this base in the N9 implementation (T061); this class provides the
    single-node transition primitive every node builds on.
    """

    def __init__(self, workflow_repo: WorkflowInstanceRepository, audit_repo: AuditEventRepository):
        self._workflow_repo = workflow_repo
        self._audit_repo = audit_repo

    def create_workflow(self, requirement_id: str, initial_stage: str) -> WorkflowInstance:
        now = utcnow()
        instance = WorkflowInstance(
            run_id=new_id(),
            requirement_id=requirement_id,
            current_stage=initial_stage,
            status="running",
            created_at=now,
            updated_at=now,
        )
        self._workflow_repo.create(instance)
        self.emit(instance.run_id, actor_type="system", action="workflow_created", result="success")
        return instance

    def transition(self, run_id: str, to_stage: str, status: str, action: str, actor_type: str = "system", reason: str | None = None) -> None:
        self._workflow_repo.update_stage(run_id, to_stage, status, utcnow())
        self.emit(run_id, actor_type=actor_type, action=action, result="success", affected_artifact=to_stage, reason=reason)

    def safe_stop(self, run_id: str, reason: str) -> None:
        """Cross-cutting terminal-for-the-path state (FR-ORC-010). Exits only via
        explicit human action elsewhere in the system — this method only enters it.
        """
        self._workflow_repo.update_stage(run_id, current_stage="SAFE_STOP", status="safe_stopped", updated_at=utcnow())
        self.emit(run_id, actor_type="system", action="safe_stop_entered", result="failure", reason=reason)

    def emit(
        self,
        run_id: str,
        actor_type: str,
        action: str,
        result: str,
        affected_artifact: str | None = None,
        reason: str | None = None,
    ) -> None:
        if result == "failure" and not reason:
            raise ValueError("reason is required when result='failure' (audit-event.schema.json)")
        event = AuditEvent(
            event_id=new_id(),
            run_id=run_id,
            actor_type=actor_type,
            action=action,
            occurred_at=utcnow(),
            affected_artifact=affected_artifact,
            result=result,
            reason=reason,
        )
        self._audit_repo.append(event)
