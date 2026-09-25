"""Integration test: N9 task-level failure is bulkheaded, unrelated parallel branches unaffected (User Story 7 acceptance scenario 2)."""

import threading
from unittest.mock import patch


def test_one_failing_branch_does_not_prevent_others_from_completing(tmp_path):
    from src.orchestration.engine import OrchestrationEngine
    from src.orchestration.nodes.n9_implementation import run_parallel_validation_and_join
    from src.persistence.db import ensure_db
    from src.persistence.orchestration_store import AuditEventRepository, PolicyCheckResultRepository, WorkflowInstanceRepository

    conn = ensure_db(str(tmp_path / "n9_bulkhead_test.db"))
    lock = threading.Lock()
    engine = OrchestrationEngine(WorkflowInstanceRepository(conn, lock), AuditEventRepository(conn, lock))
    policy_repo = PolicyCheckResultRepository(conn, lock)
    instance = engine.create_workflow(requirement_id="req-1", initial_stage="N9")

    with patch(
        "src.orchestration.nodes.n9_implementation.update_documentation",
        side_effect=RuntimeError("N11 failed"),
    ):
        try:
            run_parallel_validation_and_join(engine, policy_repo, instance.run_id)
        except RuntimeError:
            pass

    events = engine._audit_repo.list_for_run(instance.run_id)
    # N10 and N12 must still have executed and recorded their evidence,
    # even though N11 failed - this is the bulkheading property.
    assert any(e.action == "test_suite_executed" for e in events), "N10 must still run despite N11's failure"
    assert any(e.action == "policy_check_evaluated" for e in events), "N12 must still run despite N11's failure"

    # The join itself must not have silently succeeded.
    instance_after = engine._workflow_repo.get(instance.run_id)
    assert instance_after.current_stage != "N13", "join must not silently succeed when a branch failed"
