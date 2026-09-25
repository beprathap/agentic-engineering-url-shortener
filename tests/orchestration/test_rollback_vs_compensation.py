"""Unit test: irreversible-consequence brownfield changes classified as compensation, not rollback (ADR-008)."""

import threading


def _analyze(tmp_path, description, name):
    from src.orchestration.engine import OrchestrationEngine
    from src.orchestration.nodes.n4b_impact_analysis import perform_impact_analysis
    from src.persistence.db import ensure_db
    from src.persistence.orchestration_store import AuditEventRepository, WorkflowInstanceRepository

    conn = ensure_db(str(tmp_path / name))
    lock = threading.Lock()
    engine = OrchestrationEngine(WorkflowInstanceRepository(conn, lock), AuditEventRepository(conn, lock))
    instance = engine.create_workflow(requirement_id="req-1", initial_stage="N3")
    return perform_impact_analysis(engine, conn, lock, instance.run_id, description)


def test_irreversible_schema_change_classified_as_compensation(tmp_path):
    artifact = _analyze(
        tmp_path,
        "Fix: the short_code column needs an incompatible schema change to widen it, requiring a data migration.",
        "compensation_test.db",
    )
    assert artifact.reversibility == "compensation"
    assert "compensation" in artifact.categories["rollout_rollback_considerations"].lower()


def test_simple_fix_classified_as_rollback(tmp_path):
    artifact = _analyze(
        tmp_path,
        "Fix: redirect resolution returns 302 instead of 410 for expired codes.",
        "rollback_test.db",
    )
    assert artifact.reversibility == "rollback"
