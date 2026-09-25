"""Contract test for POST /v1/workflows (FR-ORC-001)."""

import json
from pathlib import Path

import jsonschema
from fastapi.testclient import TestClient

SCHEMA_PATH = Path(__file__).parents[2] / "specs" / "001-agentic-url-shortener" / "contracts" / "schemas" / "workflow-state.schema.json"


def test_create_workflow_returns_run_id_conforming_to_schema():
    from src.api.app import app

    client = TestClient(app)
    response = client.post("/v1/workflows", json={"raw_input": "Add redirect_count to the detail view."})

    assert response.status_code == 201
    body = response.json()
    schema = json.loads(SCHEMA_PATH.read_text())
    jsonschema.validate(instance=body, schema=schema)
