"""Unit test: N6/N7/N11 apply the shared bounded-retry utility on transient failure
(contracts/orchestration-state-machine.md specifies retry policy for each; convergence finding F3)."""

import threading
from unittest.mock import patch


def _engine(tmp_path, name):
    from src.orchestration.engine import OrchestrationEngine
    from src.persistence.db import ensure_db
    from src.persistence.orchestration_store import AuditEventRepository, WorkflowInstanceRepository

    conn = ensure_db(str(tmp_path / name))
    lock = threading.Lock()
    return OrchestrationEngine(WorkflowInstanceRepository(conn, lock), AuditEventRepository(conn, lock))


def test_n6_retries_on_transient_failure(tmp_path):
    from src.orchestration.clock import FakeClock
    from src.orchestration.nodes.n6_decomposition import decompose_tasks

    engine = _engine(tmp_path, "n6_retry_test.db")
    instance = engine.create_workflow(requirement_id="req-1", initial_stage="N6")

    attempts = {"n": 0}
    original_transition = engine.transition

    def flaky_transition(*args, **kwargs):
        attempts["n"] += 1
        if attempts["n"] < 2:
            raise TimeoutError("transient")
        return original_transition(*args, **kwargs)

    with patch.object(engine, "transition", side_effect=flaky_transition):
        decompose_tasks(engine, instance.run_id, clock=FakeClock())

    assert attempts["n"] == 2, "N6 must retry a transient failure via the shared retry utility"


def test_n7_retries_on_transient_failure(tmp_path):
    from src.orchestration.clock import FakeClock
    from src.orchestration.nodes.n7_design import design_architecture

    engine = _engine(tmp_path, "n7_retry_test.db")
    instance = engine.create_workflow(requirement_id="req-1", initial_stage="N7")

    attempts = {"n": 0}
    original_emit = engine.emit

    def flaky_emit(*args, **kwargs):
        attempts["n"] += 1
        if attempts["n"] < 2:
            raise TimeoutError("transient")
        return original_emit(*args, **kwargs)

    with patch.object(engine, "emit", side_effect=flaky_emit):
        design_architecture(engine, instance.run_id, clock=FakeClock())

    assert attempts["n"] >= 2, "N7 must retry a transient failure via the shared retry utility"


def test_n11_retries_on_transient_failure(tmp_path):
    from src.orchestration.clock import FakeClock
    from src.orchestration.nodes.n11_documentation import update_documentation

    engine = _engine(tmp_path, "n11_retry_test.db")
    instance = engine.create_workflow(requirement_id="req-1", initial_stage="N11")

    attempts = {"n": 0}
    original_emit = engine.emit

    def flaky_emit(*args, **kwargs):
        attempts["n"] += 1
        if attempts["n"] < 2:
            raise TimeoutError("transient")
        return original_emit(*args, **kwargs)

    with patch.object(engine, "emit", side_effect=flaky_emit):
        update_documentation(engine, instance.run_id, clock=FakeClock())

    assert attempts["n"] >= 2, "N11 must retry a transient failure via the shared retry utility"
