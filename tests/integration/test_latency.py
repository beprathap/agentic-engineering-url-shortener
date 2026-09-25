"""Latency test: redirect resolution completes within 100ms at demonstration scale (NFR-007, PVT-003)."""

import time

from fastapi.testclient import TestClient


def test_redirect_resolution_completes_within_100ms():
    from src.api.app import app

    client = TestClient(app)
    create = client.post("/v1/links", json={"target_url": "https://example.com/latency-test"})
    code = create.json()["short_code"]

    # Warm up (first call may pay one-time import/connection costs).
    client.get(f"/{code}", follow_redirects=False)

    samples = []
    for _ in range(20):
        start = time.perf_counter()
        response = client.get(f"/{code}", follow_redirects=False)
        samples.append(time.perf_counter() - start)
        assert response.status_code == 302

    p95 = sorted(samples)[int(len(samples) * 0.95)]
    assert p95 < 0.1, f"p95 redirect latency {p95 * 1000:.1f}ms exceeds the PVT-003 demonstration target of 100ms"
