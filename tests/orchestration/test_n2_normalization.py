"""Unit test for N2 Requirement Normalization (User Story 1)."""

import threading


def _make_engine(tmp_path, name="n2_test.db"):
    from src.orchestration.engine import OrchestrationEngine
    from src.persistence.db import ensure_db
    from src.persistence.orchestration_store import AuditEventRepository, WorkflowInstanceRepository

    conn = ensure_db(str(tmp_path / name))
    lock = threading.Lock()
    return OrchestrationEngine(WorkflowInstanceRepository(conn, lock), AuditEventRepository(conn, lock)), conn, lock


def test_n2_normalizes_and_persists_description(tmp_path):
    from src.orchestration.clock import FakeClock
    from src.orchestration.nodes.n2_normalization import normalize_requirement
    from src.persistence.orchestration_store import new_id

    engine, conn, lock = _make_engine(tmp_path)
    instance = engine.create_workflow(requirement_id=new_id(), initial_stage="N1")
    requirement_id = instance.requirement_id
    with lock:
        conn.execute(
            "INSERT INTO requirements (requirement_id, raw_input, created_at) VALUES (?, ?, ?)",
            (requirement_id, "Add redirect_count to the detail view.", "2026-01-01T00:00:00+00:00"),
        )
        conn.commit()

    clock = FakeClock()
    normalize_requirement(engine, conn, lock, instance.run_id, requirement_id, clock=clock)

    row = conn.execute(
        "SELECT normalized_description FROM requirements WHERE requirement_id = ?", (requirement_id,)
    ).fetchone()
    assert row["normalized_description"] is not None
    assert "redirect_count" in row["normalized_description"]

    updated_instance = engine._workflow_repo.get(instance.run_id)
    assert updated_instance.current_stage == "N3"
