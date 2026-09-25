"""Helper script run as a genuinely separate OS process by test_resumption.py.

Performs N1 (ingestion) + N2 (normalization), prints the run_id, then hard-exits
via os._exit() *before* N3 runs — simulating an abrupt process kill mid-workflow,
not a graceful shutdown. This is invoked via subprocess.run() from the test, so
it is a real, separate OS process, not an in-process function call pretending
to be one (Section 14 Independent Reviewer Gate correction, 2026-09-24).
"""

import os
import sys
import threading

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from src.orchestration.clock import SystemClock
from src.orchestration.engine import OrchestrationEngine
from src.orchestration.nodes.n1_ingestion import ingest_requirement
from src.orchestration.nodes.n2_normalization import normalize_requirement
from src.persistence.db import ensure_db
from src.persistence.orchestration_store import AuditEventRepository, WorkflowInstanceRepository

if __name__ == "__main__":
    db_path = sys.argv[1]
    conn = ensure_db(db_path)
    lock = threading.Lock()
    engine = OrchestrationEngine(WorkflowInstanceRepository(conn, lock), AuditEventRepository(conn, lock))

    result = ingest_requirement(engine, conn, lock, raw_input="Add redirect_count to the detail view.")
    normalize_requirement(engine, conn, lock, result.run_id, result.requirement_id, clock=SystemClock())

    print(result.run_id)
    sys.stdout.flush()
    os._exit(137)  # hard kill, no cleanup - simulates SIGKILL/crash, not graceful exit
