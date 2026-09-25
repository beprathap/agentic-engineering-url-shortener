"""Unit test for analytics aggregation (FR-SVC-007, ADR-014)."""

from fastapi.testclient import TestClient


def test_detail_endpoint_reports_redirect_count_and_last_accessed():
    from src.api.app import app

    client = TestClient(app)
    create = client.post("/v1/links", json={"target_url": "https://example.com/analytics-test"})
    code = create.json()["short_code"]

    client.get(f"/{code}", follow_redirects=False)
    client.get(f"/{code}", follow_redirects=False)
    client.get(f"/{code}", follow_redirects=False)

    detail = client.get(f"/v1/links/{code}")

    assert detail.status_code == 200
    body = detail.json()
    assert body["redirect_count"] == 3
    assert body["last_accessed_at"] is not None
