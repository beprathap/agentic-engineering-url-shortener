"""Integration test confirming no authentication is required (D-001, FR-SVC-012, ADR-013)."""

from fastapi.testclient import TestClient


def test_all_url_shortener_endpoints_respond_without_authorization_header():
    from src.api.app import app

    client = TestClient(app)

    create = client.post("/v1/links", json={"target_url": "https://example.com/no-auth-test"})
    assert create.status_code == 201
    assert "authorization" not in [h.lower() for h in create.request.headers.keys()]

    code = create.json()["short_code"]

    redirect = client.get(f"/{code}", follow_redirects=False)
    assert redirect.status_code == 302

    detail = client.get(f"/v1/links/{code}")
    assert detail.status_code == 200

    health = client.get("/healthz")
    assert health.status_code == 200
