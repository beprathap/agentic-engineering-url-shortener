"""Unit test: AuditEvent repository exposes no update/delete operation (NFR-006, ADR-010)."""


def test_audit_event_repository_has_no_update_or_delete_method():
    from src.persistence.orchestration_store import AuditEventRepository

    forbidden = {"update", "delete", "modify", "remove"}
    public_methods = {name for name in dir(AuditEventRepository) if not name.startswith("_")}

    overlap = public_methods & forbidden
    assert not overlap, f"AuditEventRepository must not expose {overlap} (append-only invariant, NFR-006)"
