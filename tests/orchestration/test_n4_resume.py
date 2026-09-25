"""Unit test: after an accepted clarification, workflow resumes at N2, not from zero (User Story 3)."""

import threading


def test_answered_clarification_resumes_at_n2(tmp_path):
    from src.orchestration.clock import FakeClock
    from src.orchestration.engine import OrchestrationEngine
    from src.orchestration.gates import answer_clarification, request_clarification
    from src.persistence.db import ensure_db
    from src.persistence.orchestration_store import AuditEventRepository, DecisionRepository, WorkflowInstanceRepository

    conn = ensure_db(str(tmp_path / "n4_resume_test.db"))
    lock = threading.Lock()
    engine = OrchestrationEngine(WorkflowInstanceRepository(conn, lock), AuditEventRepository(conn, lock))
    decision_repo = DecisionRepository(conn, lock)
    instance = engine.create_workflow(requirement_id="req-1", initial_stage="N3")
    clock = FakeClock()

    request_clarification(
        engine, instance.run_id,
        question="What is the intended expiration duration?",
        impact="blocks decomposition",
        current_assumption="none",
        owner="human",
        clock=clock,
    )
    pending = engine._workflow_repo.get(instance.run_id)
    assert pending.status == "clarification_pending"

    answer_clarification(
        engine, decision_repo, instance.run_id,
        actor_role_capacity="reviewer_approver",
        answer="Default expiration is 90 days unless specified.",
    )

    resumed = engine._workflow_repo.get(instance.run_id)
    assert resumed.current_stage == "N2"
    assert resumed.status == "running"

    decisions = decision_repo.list_for_run(instance.run_id)
    assert any(d.decision_type == "clarification_answer" for d in decisions)
