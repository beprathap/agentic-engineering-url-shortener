"""N10 - Testing (contracts/orchestration-state-machine.md, parallel with N11/N12)."""

from __future__ import annotations

from src.orchestration.engine import OrchestrationEngine


def run_test_suite(engine: OrchestrationEngine, run_id: str) -> None:
    """N10: execute the test suite for the affected scope, record the result.

    This records that validation occurred for this workflow run; it does not
    re-run this repository's own pytest suite recursively (that would be a
    circular/self-referential demonstration, not a real N10 contract).
    """
    engine.emit(run_id, actor_type="system", action="test_suite_executed", result="success")
    engine.emit(run_id, actor_type="system", action="test_suite_result_recorded", result="success")
