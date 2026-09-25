"""Contract test for POST /v1/links (FR-SVC-001, FR-SVC-002)."""

import re

from fastapi.testclient import TestClient

SHORT_CODE_PATTERN = re.compile(r"^[0-9a-zA-Z]{7}$")


def test_create_short_link_returns_201_with_short_link_schema():
    from src.api.app import app

    client = TestClient(app)
    response = client.post("/v1/links", json={"target_url": "https://example.com/some/long/path"})

    assert response.status_code == 201
    body = response.json()
    assert SHORT_CODE_PATTERN.match(body["short_code"])
    assert body["target_url"] == "https://example.com/some/long/path"
    assert body["status"] == "active"
    assert "created_at" in body


def test_create_short_link_rejects_disallowed_scheme():
    from src.api.app import app

    client = TestClient(app)
    response = client.post("/v1/links", json={"target_url": "javascript:alert(1)"})

    assert response.status_code == 400
    body = response.json()
    assert body["error_code"] == "INVALID_URL"


def test_create_short_link_never_deduplicates_against_prior_target_url():
    from src.api.app import app

    client = TestClient(app)
    r1 = client.post("/v1/links", json={"target_url": "https://example.com/dedup-test"})
    r2 = client.post("/v1/links", json={"target_url": "https://example.com/dedup-test"})

    assert r1.json()["short_code"] != r2.json()["short_code"]
