"""Integration test: full Brownfield scenario, N1->N4b->N5->...->N14 (SC-003, User Story 2)."""

import threading


def test_brownfield_change_requires_impact_analysis_before_implementation(tmp_path):
    from src.orchestration.clock import FakeClock
    from src.orchestration.engine import OrchestrationEngine
    from src.orchestration.gates import approve_architecture_gate, approve_requirements_gate, request_architecture_gate, request_requirements_gate
    from src.orchestration.nodes.n1_ingestion import ingest_requirement
    from src.orchestration.nodes.n2_normalization import normalize_requirement
    from src.orchestration.nodes.n3_classification import classify_requirement
    from src.orchestration.nodes.n4b_impact_analysis import perform_impact_analysis
    from src.orchestration.nodes.n6_decomposition import decompose_tasks
    from src.orchestration.nodes.n7_design import design_architecture
    from src.orchestration.nodes.n9_implementation import execute_implementation, run_parallel_validation_and_join
    from src.orchestration.nodes.n13_release_readiness import evaluate_release_readiness
    from src.orchestration.nodes.n14_summary import generate_final_summary
    from src.persistence.db import ensure_db
    from src.persistence.orchestration_store import AuditEventRepository, DecisionRepository, PolicyCheckResultRepository, WorkflowInstanceRepository

    conn = ensure_db(str(tmp_path / "brownfield_scenario.db"))
    lock = threading.Lock()
    engine = OrchestrationEngine(WorkflowInstanceRepository(conn, lock), AuditEventRepository(conn, lock))
    decision_repo = DecisionRepository(conn, lock)
    policy_repo = PolicyCheckResultRepository(conn, lock)
    clock = FakeClock()

    ingestion = ingest_requirement(
        engine, conn, lock,
        raw_input="Fix: redirect resolution currently returns 302 for expired short codes instead of 410.",
    )
    run_id = ingestion.run_id

    normalize_requirement(engine, conn, lock, run_id, ingestion.requirement_id, clock=clock)
    classification = classify_requirement(engine, conn, lock, run_id, ingestion.requirement_id)
    assert classification.classification == "brownfield"

    # Impact analysis MUST occur, and no implementation task may be authorized before it.
    artifact = perform_impact_analysis(
        engine, conn, lock, run_id,
        requirement_description="Fix: redirect resolution currently returns 302 for expired short codes instead of 410.",
    )
    for category in ("impacted_components", "impacted_interfaces", "impacted_data_flows",
                      "impacted_tests", "impacted_documentation", "regression_risks",
                      "rollout_rollback_considerations"):
        assert artifact.categories[category]

    events_before_approval = engine._audit_repo.list_for_run(run_id)
    assert not any(e.action == "tasks_decomposed" for e in events_before_approval), (
        "implementation must not begin before the impact analysis is human-approved"
    )

    request_requirements_gate(engine, run_id, classification="brownfield", clock=clock)
    approve_requirements_gate(
        engine, decision_repo, run_id,
        actor_role_capacity="reviewer_approver",
        rationale="impact analysis reviewed and approved",
    )

    decompose_tasks(engine, run_id)
    design_architecture(engine, run_id)
    request_architecture_gate(engine, run_id, clock=clock)
    approve_architecture_gate(engine, decision_repo, run_id, actor_role_capacity="reviewer_approver", rationale="approved")

    execute_implementation(engine, run_id)
    run_parallel_validation_and_join(engine, policy_repo, run_id)
    evaluate_release_readiness(engine, policy_repo, decision_repo, run_id, actor_role_capacity="release_owner")
    generate_final_summary(engine, run_id)

    final_instance = engine._workflow_repo.get(run_id)
    assert final_instance.status == "completed"
