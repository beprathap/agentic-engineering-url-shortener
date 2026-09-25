"""Contract test for GET /v1/workflows/{run_id}/audit (FR-ORC-014, User Story 6)."""

from fastapi.testclient import TestClient


def test_audit_endpoint_returns_every_event_with_required_fields():
    from src.api.app import app

    client = TestClient(app)
    create = client.post("/v1/workflows", json={"raw_input": "Add redirect_count to the detail view."})
    run_id = create.json()["run_id"]

    response = client.get(f"/v1/workflows/{run_id}/audit")

    assert response.status_code == 200
    events = response.json()
    assert len(events) >= 1
    for event in events:
        assert set(event.keys()) >= {"event_id", "run_id", "actor_type", "action", "occurred_at", "result"}
        assert event["run_id"] == run_id
