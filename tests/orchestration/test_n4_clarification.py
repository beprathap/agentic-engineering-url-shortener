"""Unit test for N4 Human Clarification (FR-ORC-004, User Story 3)."""

import threading


def _setup(tmp_path, name="n4_test.db"):
    from src.orchestration.engine import OrchestrationEngine
    from src.persistence.db import ensure_db
    from src.persistence.orchestration_store import AuditEventRepository, DecisionRepository, WorkflowInstanceRepository

    conn = ensure_db(str(tmp_path / name))
    lock = threading.Lock()
    engine = OrchestrationEngine(WorkflowInstanceRepository(conn, lock), AuditEventRepository(conn, lock))
    decision_repo = DecisionRepository(conn, lock)
    instance = engine.create_workflow(requirement_id="req-1", initial_stage="N3")
    return engine, decision_repo, instance.run_id


def test_request_clarification_produces_structured_request(tmp_path):
    from src.orchestration.clock import FakeClock
    from src.orchestration.gates import request_clarification

    engine, decision_repo, run_id = _setup(tmp_path)
    clock = FakeClock()

    request_clarification(
        engine, run_id,
        question="What is the intended expiration duration?",
        impact="Cannot proceed to decomposition without a concrete duration",
        current_assumption="None",
        owner="human",
        clock=clock,
    )

    events = engine._audit_repo.list_for_run(run_id)
    requested = [e for e in events if e.action == "clarification_requested"]
    assert len(requested) == 1
    assert "expiration duration" in requested[0].reason.lower()

    instance = engine._workflow_repo.get(run_id)
    assert instance.status == "clarification_pending"


def test_clarification_gate_timeout_enters_safe_stop_never_auto_answers(tmp_path):
    from src.orchestration.clock import FakeClock
    from src.orchestration.gates import check_gate_timeout, request_clarification

    engine, decision_repo, run_id = _setup(tmp_path)
    clock = FakeClock()

    requested_at = request_clarification(
        engine, run_id, question="q", impact="i", current_assumption="none", owner="human", clock=clock,
    )
    clock.advance_hours(24.01)

    timed_out = check_gate_timeout(engine, run_id, gate_name="clarification", requested_at=requested_at, clock=clock)

    assert timed_out is True
    instance = engine._workflow_repo.get(run_id)
    assert instance.status == "safe_stopped"
