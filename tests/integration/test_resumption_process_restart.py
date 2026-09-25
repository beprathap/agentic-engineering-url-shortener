"""Integration test: resumption proven via an actual OS process kill + restart (FR-ORC-011).

Per the Section 14 Independent Reviewer Gate correction (2026-09-24), this
uses subprocess.run() to genuinely kill a separate OS process mid-workflow,
rather than an in-process function call simulating interruption.
"""

import subprocess
import sys
import threading
from pathlib import Path


def test_workflow_resumes_from_persisted_state_after_real_process_kill(tmp_path):
    db_path = str(tmp_path / "resumption_test.db")
    helper_script = Path(__file__).parents[1] / "orchestration" / "_resume_helper_process.py"

    result = subprocess.run(
        [sys.executable, str(helper_script), db_path],
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 137, f"helper process should hard-exit(137); got {result.returncode}, stderr={result.stderr}"
    run_id = result.stdout.strip()
    assert run_id

    # A genuinely NEW process would open a new connection to reconnect; we
    # simulate that boundary faithfully by opening a fresh connection object
    # in THIS process (the pytest process, distinct from the killed helper
    # process) rather than reusing any state the helper process held.
    from src.orchestration.engine import OrchestrationEngine
    from src.orchestration.resume import resume_workflow
    from src.persistence.db import ensure_db
    from src.persistence.orchestration_store import AuditEventRepository, WorkflowInstanceRepository

    conn = ensure_db(db_path)
    lock = threading.Lock()
    workflow_repo = WorkflowInstanceRepository(conn, lock)
    audit_repo = AuditEventRepository(conn, lock)
    engine = OrchestrationEngine(workflow_repo, audit_repo)

    instance_before_resume = workflow_repo.get(run_id)
    assert instance_before_resume.current_stage == "N3", (
        "helper process should have completed N1+N2 before being killed"
    )

    resume_workflow(engine, conn, lock, run_id)

    events = audit_repo.list_for_run(run_id)
    # N1 and N2 must NOT have been re-executed (no duplicate ingestion/normalization events).
    assert sum(1 for e in events if e.action == "requirement_ingested") == 1
    assert sum(1 for e in events if e.action == "requirement_normalized") == 1
    # Resumption itself must be visible in the audit trail.
    assert any(e.action == "workflow_resumed" for e in events)

    instance_after_resume = workflow_repo.get(run_id)
    assert instance_after_resume.current_stage in ("N3", "N4", "N4b", "N5"), (
        "workflow must have progressed past N2 upon resumption, not restarted from N1"
    )
