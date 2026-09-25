"""Unit test: N5 (brownfield path) reviews the N4b impact-analysis artifact directly (User Story 2 acceptance scenario 2)."""

import threading


def test_brownfield_gate_blocks_until_impact_analysis_approved(tmp_path):
    from src.orchestration.clock import FakeClock
    from src.orchestration.engine import OrchestrationEngine
    from src.orchestration.gates import approve_requirements_gate, request_requirements_gate
    from src.orchestration.nodes.n4b_impact_analysis import perform_impact_analysis
    from src.persistence.db import ensure_db
    from src.persistence.orchestration_store import AuditEventRepository, DecisionRepository, WorkflowInstanceRepository

    conn = ensure_db(str(tmp_path / "n5_brownfield_test.db"))
    lock = threading.Lock()
    engine = OrchestrationEngine(WorkflowInstanceRepository(conn, lock), AuditEventRepository(conn, lock))
    decision_repo = DecisionRepository(conn, lock)
    instance = engine.create_workflow(requirement_id="req-1", initial_stage="N3")
    clock = FakeClock()

    artifact = perform_impact_analysis(
        engine, conn, lock, instance.run_id,
        requirement_description="Fix: redirect resolution returns 302 instead of 410 for expired codes.",
    )

    request_requirements_gate(engine, instance.run_id, classification="brownfield", clock=clock)

    events_before = engine._audit_repo.list_for_run(instance.run_id)
    requested = [e for e in events_before if e.action == "requirements_approval_requested"]
    assert len(requested) == 1
    assert "brownfield" in requested[0].reason.lower()

    # Not yet approved: must not have advanced to N6.
    instance_pending = engine._workflow_repo.get(instance.run_id)
    assert instance_pending.current_stage != "N6"

    approve_requirements_gate(
        engine, decision_repo, instance.run_id,
        actor_role_capacity="reviewer_approver",
        rationale=f"impact analysis reviewed: {artifact.categories}",
    )

    instance_after = engine._workflow_repo.get(instance.run_id)
    assert instance_after.current_stage == "N6"
