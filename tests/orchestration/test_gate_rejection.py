"""Unit test: gate rejection routes back to the producing node with rationale attached (User Story 4)."""

import threading


def _setup(tmp_path, name="rejection_test.db"):
    from src.orchestration.engine import OrchestrationEngine
    from src.persistence.db import ensure_db
    from src.persistence.orchestration_store import AuditEventRepository, DecisionRepository, WorkflowInstanceRepository

    conn = ensure_db(str(tmp_path / name))
    lock = threading.Lock()
    engine = OrchestrationEngine(WorkflowInstanceRepository(conn, lock), AuditEventRepository(conn, lock))
    decision_repo = DecisionRepository(conn, lock)
    instance = engine.create_workflow(requirement_id="req-1", initial_stage="N5")
    return engine, decision_repo, instance.run_id


def test_requirements_gate_rejection_routes_back_to_n3(tmp_path):
    from src.orchestration.gates import reject_requirements_gate

    engine, decision_repo, run_id = _setup(tmp_path)

    reject_requirements_gate(
        engine, decision_repo, run_id,
        actor_role_capacity="reviewer_approver",
        rationale="requirement conflicts with an existing invariant",
        return_to_stage="N3",
    )

    instance = engine._workflow_repo.get(run_id)
    assert instance.current_stage == "N3"
    decisions = decision_repo.list_for_run(run_id)
    rejection = next(d for d in decisions if d.decision_type == "rejection")
    assert "conflicts" in rejection.rationale


def test_architecture_gate_rejection_routes_back_to_n7(tmp_path):
    from src.orchestration.gates import reject_architecture_gate

    engine, decision_repo, run_id = _setup(tmp_path, name="arch_rejection_test.db")

    reject_architecture_gate(
        engine, decision_repo, run_id,
        actor_role_capacity="reviewer_approver",
        rationale="design does not satisfy the API contract",
    )

    instance = engine._workflow_repo.get(run_id)
    assert instance.current_stage == "N7"
    decisions = decision_repo.list_for_run(run_id)
    assert any(d.decision_type == "rejection" for d in decisions)
