"""Unit test: computed metrics carry a demonstration-data marker (FR-ORC-020)."""

import threading


def test_workflow_metrics_labeled_as_demonstration_data(tmp_path):
    from src.persistence.db import ensure_db
    from src.persistence.orchestration_store import AuditEventRepository, WorkflowInstanceRepository
    from src.telemetry.metrics import compute_workflow_metrics

    conn = ensure_db(str(tmp_path / "metrics_labeling_test.db"))
    lock = threading.Lock()
    workflow_repo = WorkflowInstanceRepository(conn, lock)
    audit_repo = AuditEventRepository(conn, lock)

    metrics = compute_workflow_metrics(workflow_repo, audit_repo, conn, lock)

    assert metrics.is_demonstration_data is True
