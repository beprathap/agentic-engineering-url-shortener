"""Integration test for persistence-failure handling (FR-SVC-010)."""

from fastapi.testclient import TestClient


def test_create_link_returns_503_when_persistence_unavailable():
    from src.api.app import _short_link_repo, app

    client = TestClient(app)

    # Simulate persistence unavailability by closing the underlying connection.
    _short_link_repo._conn.close()
    try:
        response = client.post("/v1/links", json={"target_url": "https://example.com/db-down-test"})

        assert response.status_code == 503
        body = response.json()
        assert body["error_code"] == "STORE_UNAVAILABLE"
        # Must not leak internal implementation detail (e.g. raw exception text/traceback).
        assert "sqlite3" not in body["message"].lower()
        assert "traceback" not in body["message"].lower()
    finally:
        # Reconnect so subsequent tests in the same process are unaffected.
        import src.persistence.db as db_module
        from src.config import load_settings

        _short_link_repo._conn = db_module.ensure_db(load_settings().db_path)
