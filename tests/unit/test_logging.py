"""Unit test for structured JSON logging tagged with run_id (plan.md §Observability, ADR-010)."""

import json
import logging


def test_log_line_is_json_and_includes_run_id(caplog):
    from src.telemetry.logging import get_logger, log_event

    logger = get_logger("test")
    with caplog.at_level(logging.INFO):
        log_event(logger, run_id="run-123", action="workflow_created", message="test event")

    assert len(caplog.records) == 1
    parsed = json.loads(caplog.records[0].message)
    assert parsed["run_id"] == "run-123"
    assert parsed["action"] == "workflow_created"
    assert parsed["message"] == "test event"
    assert "timestamp" in parsed
