"""Integration test: an assessment reviewer reconstructs a run from audit evidence alone (SC-008, User Story 6)."""

from fastapi.testclient import TestClient


def test_reviewer_can_reconstruct_greenfield_run_from_audit_endpoint_alone():
    from src.api.app import app

    client = TestClient(app)
    create = client.post("/v1/workflows", json={"raw_input": "Add redirect_count to the detail view."})
    run_id = create.json()["run_id"]

    audit = client.get(f"/v1/workflows/{run_id}/audit")
    events = audit.json()

    # Reconstruction requires: run_id present on every event, chronological
    # ordering, and enough named actions to reconstruct "what happened".
    assert all(e["run_id"] == run_id for e in events)
    occurred_ats = [e["occurred_at"] for e in events]
    assert occurred_ats == sorted(occurred_ats), "events must be retrievable in chronological order"

    action_names = {e["action"] for e in events}
    assert "workflow_created" in action_names
    assert "requirement_ingested" in action_names

    for event in events:
        assert event["actor_type"] in ("human", "system", "agent")
        assert event["result"] in ("success", "failure", "pending")
