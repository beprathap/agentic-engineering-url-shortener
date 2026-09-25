"""Contract test: AuditEvent conforms to contracts/schemas/audit-event.schema.json (FR-ORC-014)."""

import json
from pathlib import Path

import jsonschema
import pytest

SCHEMA_PATH = Path(__file__).parents[2] / "specs" / "001-agentic-url-shortener" / "contracts" / "schemas" / "audit-event.schema.json"


@pytest.fixture
def schema():
    return json.loads(SCHEMA_PATH.read_text())


def _to_schema_dict(event) -> dict:
    return {
        "event_id": event.event_id,
        "run_id": event.run_id,
        "actor_type": event.actor_type,
        "action": event.action,
        "occurred_at": event.occurred_at.isoformat(),
        "affected_artifact": event.affected_artifact,
        "result": event.result,
        "reason": event.reason,
    }


def test_success_audit_event_validates_against_schema(schema):
    from datetime import datetime, timezone

    from src.persistence.orchestration_store import AuditEvent, new_id

    event = AuditEvent(
        event_id=new_id(),
        run_id=new_id(),
        actor_type="system",
        action="workflow_created",
        occurred_at=datetime.now(timezone.utc),
        result="success",
    )

    jsonschema.validate(instance=_to_schema_dict(event), schema=schema)


def test_failure_audit_event_without_reason_fails_schema_validation(schema):
    from datetime import datetime, timezone

    from src.persistence.orchestration_store import AuditEvent, new_id

    event = AuditEvent(
        event_id=new_id(),
        run_id=new_id(),
        actor_type="system",
        action="node_failed",
        occurred_at=datetime.now(timezone.utc),
        result="failure",
        reason=None,
    )

    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(instance=_to_schema_dict(event), schema=schema)
