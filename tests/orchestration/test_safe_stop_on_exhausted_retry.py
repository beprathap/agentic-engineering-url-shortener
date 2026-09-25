"""Unit test for SAFE_STOP entry on exhausted retries with no fallback (FR-ORC-010)."""

import pytest


def test_safe_stop_records_reason_and_marks_workflow_safe_stopped(tmp_path):
    from src.orchestration.clock import FakeClock
    from src.orchestration.engine import OrchestrationEngine, enter_safe_stop
    from src.persistence.db import ensure_db
    from src.persistence.orchestration_store import AuditEventRepository, WorkflowInstanceRepository
    import threading

    conn = ensure_db(str(tmp_path / "safe_stop_test.db"))
    lock = threading.Lock()
    workflow_repo = WorkflowInstanceRepository(conn, lock)
    audit_repo = AuditEventRepository(conn, lock)
    engine = OrchestrationEngine(workflow_repo, audit_repo)

    instance = engine.create_workflow(requirement_id="req-1", initial_stage="N2")

    enter_safe_stop(engine, instance.run_id, reason="retries_exhausted_no_fallback")

    updated = workflow_repo.get(instance.run_id)
    assert updated.status == "safe_stopped"

    events = audit_repo.list_for_run(instance.run_id)
    safe_stop_events = [e for e in events if e.action == "safe_stop_entered"]
    assert len(safe_stop_events) == 1
    assert safe_stop_events[0].reason == "retries_exhausted_no_fallback"
    assert safe_stop_events[0].result == "failure"


def test_retry_with_backoff_raising_can_be_routed_to_safe_stop():
    from src.orchestration.clock import FakeClock
    from src.orchestration.engine import retry_with_backoff

    clock = FakeClock()

    def always_fails():
        raise TimeoutError("permanently down")

    with pytest.raises(TimeoutError):
        retry_with_backoff(always_fails, clock=clock, max_attempts=3, base_backoff_ms=200)
    # Caller is responsible for catching this and calling enter_safe_stop;
    # verified together with test_safe_stop_records_reason_and_marks_workflow_safe_stopped above.
