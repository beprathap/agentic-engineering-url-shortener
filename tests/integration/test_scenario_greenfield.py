"""Integration test: full Greenfield scenario, N1->N14, no clarification (SC-002, User Story 1)."""

import threading


def test_well_specified_requirement_completes_without_clarification(tmp_path):
    from src.orchestration.clock import FakeClock
    from src.orchestration.engine import OrchestrationEngine
    from src.orchestration.gates import approve_requirements_gate
    from src.orchestration.nodes.n1_ingestion import ingest_requirement
    from src.orchestration.nodes.n2_normalization import normalize_requirement
    from src.orchestration.nodes.n3_classification import classify_requirement
    from src.orchestration.nodes.n6_decomposition import decompose_tasks
    from src.orchestration.nodes.n7_design import design_architecture
    from src.orchestration.gates import approve_architecture_gate
    from src.orchestration.nodes.n9_implementation import execute_implementation, run_parallel_validation_and_join
    from src.orchestration.nodes.n13_release_readiness import evaluate_release_readiness
    from src.orchestration.nodes.n14_summary import generate_final_summary
    from src.persistence.db import ensure_db
    from src.persistence.orchestration_store import AuditEventRepository, DecisionRepository, PolicyCheckResultRepository, WorkflowInstanceRepository

    conn = ensure_db(str(tmp_path / "greenfield_scenario.db"))
    lock = threading.Lock()
    engine = OrchestrationEngine(WorkflowInstanceRepository(conn, lock), AuditEventRepository(conn, lock))
    decision_repo = DecisionRepository(conn, lock)
    policy_repo = PolicyCheckResultRepository(conn, lock)
    clock = FakeClock()

    ingestion = ingest_requirement(
        engine, conn, lock,
        raw_input="Add redirect_count and last_accessed_at fields to the ShortLinkDetail response, already defined in the schema.",
    )
    run_id = ingestion.run_id
    requirement_id = ingestion.requirement_id

    normalize_requirement(engine, conn, lock, run_id, requirement_id, clock=clock)
    classification = classify_requirement(engine, conn, lock, run_id, requirement_id)
    assert classification.classification == "greenfield"

    from src.orchestration.gates import request_requirements_gate
    request_requirements_gate(engine, run_id, classification="greenfield", clock=clock)
    approve_requirements_gate(
        engine, decision_repo, run_id,
        actor_role_capacity="reviewer_approver",
        rationale="auto-qualified: passed completeness/consistency/testability/in-policy checks",
    )

    decompose_tasks(engine, run_id)
    design_architecture(engine, run_id)

    from src.orchestration.gates import request_architecture_gate
    request_architecture_gate(engine, run_id, clock=clock)
    approve_architecture_gate(engine, decision_repo, run_id, actor_role_capacity="reviewer_approver", rationale="design reviewed and approved")

    execute_implementation(engine, run_id)
    run_parallel_validation_and_join(engine, policy_repo, run_id)

    outcome = evaluate_release_readiness(engine, policy_repo, decision_repo, run_id, actor_role_capacity="release_owner")
    generate_final_summary(engine, run_id)

    final_instance = engine._workflow_repo.get(run_id)
    assert final_instance.status == "completed"

    events = engine._audit_repo.list_for_run(run_id)
    assert not any(e.action == "clarification_requested" for e in events), (
        "well-specified greenfield requirement must not trigger clarification (SC-002)"
    )
    assert any(e.action == "final_summary_generated" for e in events)
