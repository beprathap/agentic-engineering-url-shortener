"""Integration test for concurrent creation/redirect requests (FR-SVC-009, SC-010)."""

from concurrent.futures import ThreadPoolExecutor

from fastapi.testclient import TestClient


def test_concurrent_creation_produces_no_duplicate_active_codes():
    from src.api.app import app

    client = TestClient(app)

    def create_one(i: int):
        return client.post("/v1/links", json={"target_url": f"https://example.com/concurrent-{i}"})

    with ThreadPoolExecutor(max_workers=10) as pool:
        responses = list(pool.map(create_one, range(30)))

    codes = [r.json()["short_code"] for r in responses]
    assert all(r.status_code == 201 for r in responses)
    assert len(codes) == len(set(codes)), "duplicate short codes were issued under concurrent load"


def test_concurrent_redirects_produce_consistent_analytics_count():
    from src.api.app import app

    client = TestClient(app)
    create = client.post("/v1/links", json={"target_url": "https://example.com/concurrent-redirect-test"})
    code = create.json()["short_code"]

    def redirect_once(_i: int):
        return client.get(f"/{code}", follow_redirects=False)

    with ThreadPoolExecutor(max_workers=10) as pool:
        list(pool.map(redirect_once, range(25)))

    detail = client.get(f"/v1/links/{code}")
    assert detail.json()["redirect_count"] == 25
