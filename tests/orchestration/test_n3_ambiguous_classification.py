"""Unit test: N3 classifies incomplete/contradictory requirements as ambiguous (User Story 3)."""

import threading


def test_incomplete_requirement_with_vague_marker_classified_ambiguous(tmp_path):
    from src.orchestration.engine import OrchestrationEngine
    from src.orchestration.nodes.n3_classification import classify_requirement
    from src.persistence.db import ensure_db
    from src.persistence.orchestration_store import AuditEventRepository, WorkflowInstanceRepository

    conn = ensure_db(str(tmp_path / "n3_ambiguous_test.db"))
    lock = threading.Lock()
    engine = OrchestrationEngine(WorkflowInstanceRepository(conn, lock), AuditEventRepository(conn, lock))
    instance = engine.create_workflow(requirement_id="req-1", initial_stage="N2")
    raw = "Make links expire eventually."
    with lock:
        conn.execute(
            "INSERT INTO requirements (requirement_id, raw_input, normalized_description, created_at) VALUES (?, ?, ?, ?)",
            ("req-1", raw, raw, "2026-01-01T00:00:00+00:00"),
        )
        conn.commit()

    result = classify_requirement(engine, conn, lock, instance.run_id, "req-1")

    assert result.classification == "ambiguous"
    assert result.quality_check_failures
