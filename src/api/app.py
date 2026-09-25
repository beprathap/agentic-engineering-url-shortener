"""FastAPI app wiring (T007+). No authentication middleware is registered on any route
in this app, by design (D-001, ADR-013) — do not add auth here without a governed
brownfield workflow.
"""

from __future__ import annotations

import threading

from fastapi import FastAPI
from pydantic import BaseModel

from src.api.links import register_links_routes, router as links_router
from src.api.workflows import register_workflow_routes, router as workflows_router
from src.config import load_settings
from src.orchestration.engine import OrchestrationEngine
from src.persistence.db import ensure_db
from src.persistence.orchestration_store import AuditEventRepository, WorkflowInstanceRepository
from src.persistence.short_links import ShortLinkRepository

app = FastAPI(title="Agentic URL Shortener API", version="1.0.0")

_settings = load_settings()
_conn = ensure_db(_settings.db_path)
_lock = threading.Lock()
_short_link_repo = ShortLinkRepository(_conn, _lock)
_workflow_repo = WorkflowInstanceRepository(_conn, _lock)
_audit_repo = AuditEventRepository(_conn, _lock)
_engine = OrchestrationEngine(_workflow_repo, _audit_repo)

class HealthStatus(BaseModel):
    status: str
    details: str | None = None


@app.get("/healthz", response_model=HealthStatus)
def get_health() -> HealthStatus:
    try:
        _conn.execute("SELECT 1").fetchone()
        return HealthStatus(status="ready")
    except Exception as exc:  # pragma: no cover - defensive
        return HealthStatus(status="not_ready", details=str(exc))


register_workflow_routes(workflows_router, _engine, _workflow_repo, _audit_repo, _conn, _lock)
app.include_router(workflows_router)

# IMPORTANT: registered last. links_router contains a catch-all GET /{short_code}
# route; any literal path registered after it would be shadowed by that pattern.
register_links_routes(links_router, _short_link_repo)
app.include_router(links_router)
