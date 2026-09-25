"""Unit test for idempotency-key handling (FR-SVC-008)."""

from fastapi.testclient import TestClient


def test_identical_idempotency_key_returns_same_short_code():
    from src.api.app import app

    client = TestClient(app)
    headers = {"Idempotency-Key": "test-idem-key-1"}
    payload = {"target_url": "https://example.com/idem-test"}

    r1 = client.post("/v1/links", json=payload, headers=headers)
    r2 = client.post("/v1/links", json=payload, headers=headers)

    assert r1.status_code == 201
    assert r2.status_code == 201
    assert r1.json()["short_code"] == r2.json()["short_code"]
