"""Contract test for GET /{short_code} redirect resolution (FR-SVC-004, FR-SVC-005)."""

from fastapi.testclient import TestClient


def test_redirect_to_active_short_code_returns_302_with_location():
    from src.api.app import app

    client = TestClient(app)
    create = client.post("/v1/links", json={"target_url": "https://example.com/redirect-test"})
    code = create.json()["short_code"]

    response = client.get(f"/{code}", follow_redirects=False)

    assert response.status_code == 302
    assert response.headers["location"] == "https://example.com/redirect-test"


def test_redirect_to_unknown_short_code_returns_404_not_found():
    from src.api.app import app

    client = TestClient(app)
    response = client.get("/zzzzzzz", follow_redirects=False)

    assert response.status_code == 404
    assert response.json()["error_code"] == "NOT_FOUND"


def test_redirect_to_expired_short_code_returns_410_expired():
    from datetime import datetime, timedelta, timezone

    from src.api.app import app, _short_link_repo
    from src.persistence.short_links import ShortLink

    client = TestClient(app)
    expired_link = ShortLink(
        short_code="expire1",
        target_url="https://example.com/expired",
        created_at=datetime.now(timezone.utc) - timedelta(days=100),
        expires_at=datetime.now(timezone.utc) - timedelta(days=10),
        status="active",
    )
    _short_link_repo.create(expired_link)

    response = client.get("/expire1", follow_redirects=False)

    assert response.status_code == 410
    assert response.json()["error_code"] == "EXPIRED"
