"""Contract test for GET /v1/workflows/{run_id} (FR-ORC-002, closes analyze finding F7)."""

import json
from pathlib import Path

import jsonschema
from fastapi.testclient import TestClient

SCHEMA_PATH = Path(__file__).parents[2] / "specs" / "001-agentic-url-shortener" / "contracts" / "schemas" / "workflow-state.schema.json"


def test_get_workflow_returns_current_stage_and_status():
    from src.api.app import app

    client = TestClient(app)
    create = client.post("/v1/workflows", json={"raw_input": "Add redirect_count to the detail view."})
    run_id = create.json()["run_id"]

    response = client.get(f"/v1/workflows/{run_id}")

    assert response.status_code == 200
    body = response.json()
    schema = json.loads(SCHEMA_PATH.read_text())
    jsonschema.validate(instance=body, schema=schema)
    assert body["current_stage"] == "N2"
    assert body["status"] == "running"


def test_get_unknown_workflow_returns_404():
    from src.api.app import app

    client = TestClient(app)
    response = client.get("/v1/workflows/00000000-0000-0000-0000-000000000000")

    assert response.status_code == 404
