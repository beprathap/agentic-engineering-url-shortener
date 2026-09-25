"""Load test: redirect path sustains >=50 req/s on a single local node (NFR-003, PVT-002)."""

import time

from fastapi.testclient import TestClient


def test_redirect_path_sustains_50_requests_per_second():
    from src.api.app import app

    client = TestClient(app)
    create = client.post("/v1/links", json={"target_url": "https://example.com/load-test"})
    code = create.json()["short_code"]

    request_count = 100
    start = time.perf_counter()
    for _ in range(request_count):
        response = client.get(f"/{code}", follow_redirects=False)
        assert response.status_code == 302
    elapsed = time.perf_counter() - start

    throughput = request_count / elapsed
    assert throughput >= 50, (
        f"redirect throughput {throughput:.1f} req/s is below the PVT-002 demonstration target of 50 req/s "
        "(in-process TestClient, single-threaded — see plan.md for scale caveats)"
    )
