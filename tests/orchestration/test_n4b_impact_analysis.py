"""Unit test for N4b Impact Analysis (User Story 2 acceptance scenario 1)."""

import threading


def test_impact_analysis_contains_all_required_categories(tmp_path):
    from src.orchestration.engine import OrchestrationEngine
    from src.orchestration.nodes.n4b_impact_analysis import REQUIRED_CATEGORIES, perform_impact_analysis
    from src.persistence.db import ensure_db
    from src.persistence.orchestration_store import AuditEventRepository, WorkflowInstanceRepository

    conn = ensure_db(str(tmp_path / "n4b_test.db"))
    lock = threading.Lock()
    engine = OrchestrationEngine(WorkflowInstanceRepository(conn, lock), AuditEventRepository(conn, lock))
    instance = engine.create_workflow(requirement_id="req-1", initial_stage="N3")

    artifact = perform_impact_analysis(
        engine, conn, lock, instance.run_id,
        requirement_description="Fix: redirect resolution returns 302 instead of 410 for expired codes.",
    )

    for category in REQUIRED_CATEGORIES:
        assert category in artifact.categories, f"impact analysis missing required category: {category}"
        assert artifact.categories[category], f"category {category} must not be empty"

    instance_after = engine._workflow_repo.get(instance.run_id)
    assert instance_after.current_stage == "N5"
