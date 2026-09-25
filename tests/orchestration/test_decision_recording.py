"""Unit test: approval Decision records actor_role_capacity, timestamp, and conditions (User Story 4)."""

import threading


def test_approval_decision_captures_role_capacity_timestamp_and_conditions(tmp_path):
    from src.orchestration.engine import OrchestrationEngine
    from src.orchestration.gates import approve_requirements_gate
    from src.persistence.db import ensure_db
    from src.persistence.orchestration_store import AuditEventRepository, DecisionRepository, WorkflowInstanceRepository

    conn = ensure_db(str(tmp_path / "decision_recording_test.db"))
    lock = threading.Lock()
    engine = OrchestrationEngine(WorkflowInstanceRepository(conn, lock), AuditEventRepository(conn, lock))
    decision_repo = DecisionRepository(conn, lock)
    instance = engine.create_workflow(requirement_id="req-1", initial_stage="N5")

    approve_requirements_gate(
        engine, decision_repo, instance.run_id,
        actor_role_capacity="reviewer_approver",
        rationale="approved with a condition",
        conditions="Must add a follow-up analytics test within the next task group.",
    )

    decisions = decision_repo.list_for_run(instance.run_id)
    assert len(decisions) == 1
    decision = decisions[0]
    assert decision.actor_role_capacity == "reviewer_approver"
    assert decision.created_at is not None
    assert decision.conditions == "Must add a follow-up analytics test within the next task group."
