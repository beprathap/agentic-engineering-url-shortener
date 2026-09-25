"""Human approval gates (N5, N8, N13): request/approve/reject/timeout (ADR-006, FR-ORC-005/006).

Generic gate mechanism shared by every mandatory human gate in the graph.
A "gate timeout" is checked lazily against a persisted request timestamp
rather than a blocking sleep, so it works whether or not the process stays
alive for the full 24-hour window (Section 14 reviewer-gate correction).
"""

from __future__ import annotations

from datetime import datetime, timedelta

from src.orchestration.clock import Clock
from src.orchestration.engine import OrchestrationEngine, utcnow
from src.persistence.orchestration_store import Decision, DecisionRepository, new_id

GATE_TIMEOUT_SECONDS = 24 * 60 * 60  # confirmed parameter, 2026-09-24


def request_requirements_gate(
    engine: OrchestrationEngine,
    run_id: str,
    classification: str,
    clock: Clock,
) -> datetime:
    """N5: request human approval. For a well-specified greenfield requirement,
    pre-populate an auto-qualified rationale — but this is only a suggested
    rationale for the human to review, not an auto-approval (FR-ORC-006).
    """
    requested_at = clock.now()
    if classification == "greenfield":
        reason = "auto-qualified: passed completeness/consistency/testability/in-policy checks"
    else:
        reason = f"requirements approval requested for classification={classification}"
    engine.emit(
        run_id,
        actor_type="system",
        action="requirements_approval_requested",
        result="pending",
        reason=reason,
    )
    return requested_at


def approve_requirements_gate(
    engine: OrchestrationEngine,
    decision_repo: DecisionRepository,
    run_id: str,
    actor_role_capacity: str,
    rationale: str,
    conditions: str | None = None,
) -> None:
    decision_repo.create(
        Decision(
            decision_id=new_id(),
            run_id=run_id,
            decision_type="approval",
            actor_role_capacity=actor_role_capacity,
            rationale=rationale,
            conditions=conditions,
            created_at=utcnow(),
        )
    )
    engine.transition(run_id, to_stage="N6", status="running", action="requirements_approved", actor_type="human")


def reject_requirements_gate(
    engine: OrchestrationEngine,
    decision_repo: DecisionRepository,
    run_id: str,
    actor_role_capacity: str,
    rationale: str,
    return_to_stage: str,
) -> None:
    decision_repo.create(
        Decision(
            decision_id=new_id(),
            run_id=run_id,
            decision_type="rejection",
            actor_role_capacity=actor_role_capacity,
            rationale=rationale,
            created_at=utcnow(),
        )
    )
    engine.transition(run_id, to_stage=return_to_stage, status="running", action="requirements_rejected", actor_type="human")


def request_architecture_gate(engine: OrchestrationEngine, run_id: str, clock: Clock) -> datetime:
    """N8: mandatory human approval of the design, regardless of whether N4
    (clarification) was skipped (User Story 1 acceptance scenario 3)."""
    requested_at = clock.now()
    engine.emit(
        run_id,
        actor_type="system",
        action="architecture_approval_requested",
        result="pending",
        reason="design artifact ready for human review",
    )
    return requested_at


def approve_architecture_gate(
    engine: OrchestrationEngine,
    decision_repo: DecisionRepository,
    run_id: str,
    actor_role_capacity: str,
    rationale: str,
) -> None:
    decision_repo.create(
        Decision(
            decision_id=new_id(),
            run_id=run_id,
            decision_type="approval",
            actor_role_capacity=actor_role_capacity,
            rationale=rationale,
            created_at=utcnow(),
        )
    )
    engine.transition(run_id, to_stage="N9", status="running", action="architecture_approved", actor_type="human")


def reject_architecture_gate(
    engine: OrchestrationEngine,
    decision_repo: DecisionRepository,
    run_id: str,
    actor_role_capacity: str,
    rationale: str,
) -> None:
    decision_repo.create(
        Decision(
            decision_id=new_id(),
            run_id=run_id,
            decision_type="rejection",
            actor_role_capacity=actor_role_capacity,
            rationale=rationale,
            created_at=utcnow(),
        )
    )
    engine.transition(run_id, to_stage="N7", status="running", action="architecture_rejected", actor_type="human")


def request_clarification(
    engine: OrchestrationEngine,
    run_id: str,
    question: str,
    impact: str,
    current_assumption: str,
    owner: str,
    clock: Clock,
) -> datetime:
    """N4: present a structured clarification request (User Story 3). No default
    is guessed here — Constitution Principle III forbids silently resolving
    material ambiguity.
    """
    requested_at = clock.now()
    engine._workflow_repo.update_stage(run_id, current_stage="N4", status="clarification_pending", updated_at=requested_at)
    engine.emit(
        run_id,
        actor_type="system",
        action="clarification_requested",
        result="pending",
        reason=f"question={question!r}; impact={impact!r}; current_assumption={current_assumption!r}; owner={owner!r}",
    )
    return requested_at


def answer_clarification(
    engine: OrchestrationEngine,
    decision_repo: DecisionRepository,
    run_id: str,
    actor_role_capacity: str,
    answer: str,
) -> None:
    """Record the human's clarification answer and resume at N2 (re-normalize
    with the clarified input), not from zero (User Story 3 acceptance scenario 2).
    """
    decision_repo.create(
        Decision(
            decision_id=new_id(),
            run_id=run_id,
            decision_type="clarification_answer",
            actor_role_capacity=actor_role_capacity,
            rationale=answer,
            created_at=utcnow(),
        )
    )
    engine.transition(run_id, to_stage="N2", status="running", action="clarification_answered", actor_type="human")


def check_gate_timeout(
    engine: OrchestrationEngine,
    run_id: str,
    gate_name: str,
    requested_at: datetime,
    clock: Clock,
    timeout_seconds: int = GATE_TIMEOUT_SECONDS,
) -> bool:
    """Return True (and enter SAFE_STOP) if the gate has been pending longer
    than timeout_seconds since requested_at; otherwise return False and leave
    the workflow pending. Never auto-approves (FR-ORC-006).
    """
    elapsed = (clock.now() - requested_at).total_seconds()
    if elapsed <= timeout_seconds:
        return False

    engine.emit(
        run_id,
        actor_type="system",
        action=f"{gate_name}_gate_timed_out",
        result="failure",
        reason=f"{gate_name} gate exceeded {timeout_seconds}s timeout with no human response",
    )
    engine.safe_stop(run_id, reason=f"{gate_name}_gate_timeout")
    return True
