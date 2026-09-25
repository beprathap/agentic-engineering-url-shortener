"""Unit test: replanned work re-enters N8 approval before resuming N9 - no bypass (FR-ORC-013, User Story 9)."""

import threading


def test_replanned_design_requires_fresh_architecture_approval(tmp_path):
    from src.orchestration.engine import OrchestrationEngine
    from src.orchestration.gates import approve_architecture_gate, request_architecture_gate
    from src.orchestration.nodes.n7_design import design_architecture
    from src.orchestration.replanning import register_design_version, revise_design
    from src.persistence.db import ensure_db
    from src.persistence.orchestration_store import AuditEventRepository, DecisionRepository, WorkflowInstanceRepository

    conn = ensure_db(str(tmp_path / "replanning_governance_test.db"))
    lock = threading.Lock()
    engine = OrchestrationEngine(WorkflowInstanceRepository(conn, lock), AuditEventRepository(conn, lock))
    decision_repo = DecisionRepository(conn, lock)
    instance = engine.create_workflow(requirement_id="req-1", initial_stage="N9")

    v1 = register_design_version(conn, lock, instance.run_id, contract_shape={"fields": ["a"]})

    # Material change: workflow is suspended back to N7.
    revise_design(engine, conn, lock, instance.run_id, new_contract_shape={"fields": ["a", "b"]}, built_against_version=v1.version)
    instance_after_staleness = engine._workflow_repo.get(instance.run_id)
    assert instance_after_staleness.current_stage == "N7"

    # The replanned design must go through N7 -> N8 again, with a fresh approval -
    # it cannot jump straight back to N9.
    design_architecture(engine, instance.run_id)
    instance_at_gate = engine._workflow_repo.get(instance.run_id)
    assert instance_at_gate.current_stage == "N8"

    from src.orchestration.clock import FakeClock
    request_architecture_gate(engine, instance.run_id, clock=FakeClock())
    approve_architecture_gate(engine, decision_repo, instance.run_id, actor_role_capacity="reviewer_approver", rationale="re-approved after replanning")

    instance_final = engine._workflow_repo.get(instance.run_id)
    assert instance_final.current_stage == "N9"

    decisions = decision_repo.list_for_run(instance.run_id)
    approvals = [d for d in decisions if d.decision_type == "approval"]
    assert len(approvals) == 1, "the replanned design requires its own fresh approval decision"
