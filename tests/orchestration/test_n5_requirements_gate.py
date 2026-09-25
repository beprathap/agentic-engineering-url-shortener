"""Unit test for N5 Human Approval Gate: Requirements (FR-ORC-005/006, ADR-006, User Story 1)."""

import threading
from datetime import datetime, timezone


def _setup(tmp_path, name="n5_test.db"):
    from src.orchestration.engine import OrchestrationEngine
    from src.persistence.db import ensure_db
    from src.persistence.orchestration_store import AuditEventRepository, DecisionRepository, WorkflowInstanceRepository

    conn = ensure_db(str(tmp_path / name))
    lock = threading.Lock()
    engine = OrchestrationEngine(WorkflowInstanceRepository(conn, lock), AuditEventRepository(conn, lock))
    decision_repo = DecisionRepository(conn, lock)
    instance = engine.create_workflow(requirement_id="req-1", initial_stage="N3")
    return engine, decision_repo, instance.run_id


def test_greenfield_gate_auto_qualified_rationale_still_requires_recorded_approval(tmp_path):
    from src.orchestration.clock import FakeClock
    from src.orchestration.gates import approve_requirements_gate, request_requirements_gate

    engine, decision_repo, run_id = _setup(tmp_path)
    clock = FakeClock()

    request_requirements_gate(engine, run_id, classification="greenfield", clock=clock)

    events = engine._audit_repo.list_for_run(run_id)
    requested = [e for e in events if e.action == "requirements_approval_requested"]
    assert len(requested) == 1
    assert "auto-qualified" in requested[0].reason.lower()

    # Not yet approved: workflow must still be pending, not advanced.
    instance = engine._workflow_repo.get(run_id)
    assert instance.status != "running" or instance.current_stage != "N6"

    approve_requirements_gate(
        engine, decision_repo, run_id,
        actor_role_capacity="reviewer_approver",
        rationale="auto-qualified: passed completeness/consistency/testability/in-policy checks",
    )

    instance = engine._workflow_repo.get(run_id)
    assert instance.current_stage == "N6"
    decisions = decision_repo.list_for_run(run_id)
    assert any(d.decision_type == "approval" for d in decisions)


def test_gate_timeout_after_24_hours_enters_safe_stop(tmp_path):
    from src.orchestration.clock import FakeClock
    from src.orchestration.gates import check_gate_timeout, request_requirements_gate

    engine, decision_repo, run_id = _setup(tmp_path)
    clock = FakeClock()

    requested_at = request_requirements_gate(engine, run_id, classification="greenfield", clock=clock)
    clock.advance_hours(24.01)

    timed_out = check_gate_timeout(engine, run_id, gate_name="requirements", requested_at=requested_at, clock=clock)

    assert timed_out is True
    instance = engine._workflow_repo.get(run_id)
    assert instance.status == "safe_stopped"
    events = engine._audit_repo.list_for_run(run_id)
    assert any(e.action == "safe_stop_entered" and "requirements" in (e.reason or "") for e in events)
