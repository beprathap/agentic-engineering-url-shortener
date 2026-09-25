"""Unit test for N1 Requirement Ingestion (FR-ORC-001)."""

import threading

import pytest


def _make_engine(tmp_path, name="n1_test.db"):
    from src.orchestration.engine import OrchestrationEngine
    from src.persistence.db import ensure_db
    from src.persistence.orchestration_store import AuditEventRepository, WorkflowInstanceRepository

    conn = ensure_db(str(tmp_path / name))
    lock = threading.Lock()
    return OrchestrationEngine(WorkflowInstanceRepository(conn, lock), AuditEventRepository(conn, lock)), conn, lock


def test_n1_ingest_creates_requirement_and_workflow_instance(tmp_path):
    from src.orchestration.nodes.n1_ingestion import ingest_requirement
    from src.persistence.orchestration_store import new_id

    engine, conn, lock = _make_engine(tmp_path)

    result = ingest_requirement(engine, conn, lock, raw_input="Add a feature.")

    assert result.run_id
    assert result.requirement_id
    instance = engine._workflow_repo.get(result.run_id)
    assert instance is not None
    assert instance.current_stage == "N2"


def test_n1_rejects_empty_input_without_creating_workflow_instance(tmp_path):
    from src.orchestration.nodes.n1_ingestion import EmptyRequirementError, ingest_requirement

    engine, conn, lock = _make_engine(tmp_path)

    with pytest.raises(EmptyRequirementError):
        ingest_requirement(engine, conn, lock, raw_input="")

    # No workflow instance should exist at all.
    row = conn.execute("SELECT COUNT(*) AS c FROM workflow_instances").fetchone()
    assert row["c"] == 0
