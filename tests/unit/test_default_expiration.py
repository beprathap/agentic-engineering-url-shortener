"""Unit test for default expiration application (FR-SVC-006, PVT-001 confirmed 2026-09-24)."""

from datetime import datetime, timezone


def test_default_expiration_is_ninety_days_from_creation():
    from src.domain.short_link import compute_default_expiration

    created_at = datetime(2026, 1, 1, tzinfo=timezone.utc)
    expires_at = compute_default_expiration(created_at)

    assert (expires_at - created_at).days == 90


def test_create_short_link_applies_default_expiration_when_omitted():
    from fastapi.testclient import TestClient

    from src.api.app import app

    client = TestClient(app)
    response = client.post("/v1/links", json={"target_url": "https://example.com/expiry-test"})

    body = response.json()
    assert body["expires_at"] is not None
    created_at = datetime.fromisoformat(body["created_at"])
    expires_at = datetime.fromisoformat(body["expires_at"])
    assert (expires_at - created_at).days == 90
