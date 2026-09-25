"""Unit test: every audit event emitted by the engine also produces a structured log line (ADR-010)."""

import json
import logging
import threading


def test_engine_emit_also_logs_structured_json(caplog):
    from src.orchestration.engine import OrchestrationEngine
    from src.persistence.db import ensure_db
    from src.persistence.orchestration_store import AuditEventRepository, WorkflowInstanceRepository

    conn = ensure_db(":memory:")
    lock = threading.Lock()
    engine = OrchestrationEngine(WorkflowInstanceRepository(conn, lock), AuditEventRepository(conn, lock))

    with caplog.at_level(logging.INFO):
        instance = engine.create_workflow(requirement_id="req-1", initial_stage="N1")

    json_lines = [r.message for r in caplog.records if r.message.startswith("{")]
    assert json_lines, "engine.emit() must produce at least one structured log line"
    parsed = [json.loads(line) for line in json_lines]
    assert any(p["run_id"] == instance.run_id and p["action"] == "workflow_created" for p in parsed)
