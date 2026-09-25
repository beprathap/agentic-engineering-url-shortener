"""Unit test for N3 Ambiguity Detection & Classification (FR-ORC-003/004, User Story 1)."""

import threading


def _setup(tmp_path, raw_input, name="n3_test.db"):
    from src.orchestration.engine import OrchestrationEngine
    from src.persistence.db import ensure_db
    from src.persistence.orchestration_store import AuditEventRepository, WorkflowInstanceRepository

    conn = ensure_db(str(tmp_path / name))
    lock = threading.Lock()
    engine = OrchestrationEngine(WorkflowInstanceRepository(conn, lock), AuditEventRepository(conn, lock))
    instance = engine.create_workflow(requirement_id="req-1", initial_stage="N2")
    with lock:
        conn.execute(
            "INSERT INTO requirements (requirement_id, raw_input, normalized_description, created_at) VALUES (?, ?, ?, ?)",
            ("req-1", raw_input, raw_input, "2026-01-01T00:00:00+00:00"),
        )
        conn.commit()
    return engine, conn, lock, instance.run_id


def test_well_specified_requirement_classified_as_greenfield_and_does_not_trigger_n4(tmp_path):
    from src.orchestration.nodes.n3_classification import classify_requirement

    engine, conn, lock, run_id = _setup(
        tmp_path,
        "Add redirect_count and last_accessed_at fields to the ShortLinkDetail response, already defined in the schema.",
    )

    result = classify_requirement(engine, conn, lock, run_id, "req-1")

    assert result.classification == "greenfield"
    events = engine._audit_repo.list_for_run(run_id)
    assert not any(e.action == "clarification_requested" for e in events)
    assert any(e.action == "classification_assigned" for e in events)


def test_incomplete_requirement_classified_as_ambiguous(tmp_path):
    from src.orchestration.nodes.n3_classification import classify_requirement

    engine, conn, lock, run_id = _setup(tmp_path, "Make links expire eventually.")

    result = classify_requirement(engine, conn, lock, run_id, "req-1")

    assert result.classification == "ambiguous"
    assert result.quality_check_failures, "an ambiguous classification must record which check(s) failed"
