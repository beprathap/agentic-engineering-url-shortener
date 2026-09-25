"""Contract test for GET /healthz (FR-SVC-011). Must fail before src/api/app.py exists."""

from fastapi.testclient import TestClient


def test_healthz_returns_ready_status():
    from src.api.app import app  # imported inside test so the test fails for import-error first

    client = TestClient(app)
    response = client.get("/healthz")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] in ("ready", "not_ready", "degraded")
