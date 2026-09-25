"""Unit test: material revision to an approved N7 artifact triggers replanning (FR-ORC-012, User Story 9)."""

import threading


def test_material_design_revision_suspends_downstream_work(tmp_path):
    from src.orchestration.engine import OrchestrationEngine
    from src.orchestration.replanning import DesignVersion, register_design_version, revise_design
    from src.persistence.db import ensure_db
    from src.persistence.orchestration_store import AuditEventRepository, WorkflowInstanceRepository

    conn = ensure_db(str(tmp_path / "replanning_test.db"))
    lock = threading.Lock()
    engine = OrchestrationEngine(WorkflowInstanceRepository(conn, lock), AuditEventRepository(conn, lock))
    instance = engine.create_workflow(requirement_id="req-1", initial_stage="N9")

    v1 = register_design_version(conn, lock, instance.run_id, contract_shape={"fields": ["a", "b"]})
    assert v1.version == 1

    # Downstream (N9) recorded it was built against v1.
    v2 = revise_design(
        engine, conn, lock, instance.run_id,
        new_contract_shape={"fields": ["a", "b", "c"]},  # material: field added
        built_against_version=v1.version,
    )

    assert v2.version == 2
    events = engine._audit_repo.list_for_run(instance.run_id)
    assert any(e.action == "dependency_staleness_detected" for e in events)
    assert any(e.action == "replanning_triggered" for e in events)

    instance_after = engine._workflow_repo.get(instance.run_id)
    assert instance_after.current_stage == "N7", "staleness must suspend downstream work back to N7"


def test_cosmetic_design_revision_does_not_trigger_replanning(tmp_path):
    from src.orchestration.engine import OrchestrationEngine
    from src.orchestration.replanning import register_design_version, revise_design
    from src.persistence.db import ensure_db
    from src.persistence.orchestration_store import AuditEventRepository, WorkflowInstanceRepository

    conn = ensure_db(str(tmp_path / "replanning_cosmetic_test.db"))
    lock = threading.Lock()
    engine = OrchestrationEngine(WorkflowInstanceRepository(conn, lock), AuditEventRepository(conn, lock))
    instance = engine.create_workflow(requirement_id="req-1", initial_stage="N9")

    v1 = register_design_version(conn, lock, instance.run_id, contract_shape={"fields": ["a", "b"]})

    v_same = revise_design(
        engine, conn, lock, instance.run_id,
        new_contract_shape={"fields": ["a", "b"]},  # identical shape: cosmetic
        built_against_version=v1.version,
    )

    assert v_same.version == v1.version, "a cosmetic (non-shape-changing) revision must not bump the version"
    events = engine._audit_repo.list_for_run(instance.run_id)
    assert not any(e.action == "replanning_triggered" for e in events)
