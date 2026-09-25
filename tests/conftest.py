from __future__ import annotations

import sys

import pytest


@pytest.fixture(autouse=True)
def isolated_test_db(monkeypatch, tmp_path):
    """Isolate each test from the repo's shared SQLite database and reload app modules."""
    db_path = tmp_path / "url_shortener.db"
    monkeypatch.setenv("DB_PATH", str(db_path))

    for module_name in [
        "src.config",
        "src.api.app",
        "src.api.links",
        "src.api.workflows",
        "src.persistence.db",
        "src.persistence.short_links",
        "src.persistence.orchestration_store",
    ]:
        sys.modules.pop(module_name, None)

    yield

    for module_name in [
        "src.config",
        "src.api.app",
        "src.api.links",
        "src.api.workflows",
        "src.persistence.db",
        "src.persistence.short_links",
        "src.persistence.orchestration_store",
    ]:
        sys.modules.pop(module_name, None)
