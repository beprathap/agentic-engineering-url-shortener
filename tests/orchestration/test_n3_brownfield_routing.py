"""Unit test: N3 routes brownfield classification to N4b before N5 (User Story 2)."""

import threading


def test_brownfield_requirement_classified_and_routed_correctly(tmp_path):
    from src.orchestration.engine import OrchestrationEngine
    from src.orchestration.nodes.n3_classification import classify_requirement
    from src.persistence.db import ensure_db
    from src.persistence.orchestration_store import AuditEventRepository, WorkflowInstanceRepository

    conn = ensure_db(str(tmp_path / "n3_brownfield_test.db"))
    lock = threading.Lock()
    engine = OrchestrationEngine(WorkflowInstanceRepository(conn, lock), AuditEventRepository(conn, lock))
    instance = engine.create_workflow(requirement_id="req-1", initial_stage="N2")
    raw = "Fix: redirect resolution currently returns 302 for expired short codes instead of 410."
    with lock:
        conn.execute(
            "INSERT INTO requirements (requirement_id, raw_input, normalized_description, created_at) VALUES (?, ?, ?, ?)",
            ("req-1", raw, raw, "2026-01-01T00:00:00+00:00"),
        )
        conn.commit()

    result = classify_requirement(engine, conn, lock, instance.run_id, "req-1")

    assert result.classification == "brownfield"
