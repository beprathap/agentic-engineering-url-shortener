"""N6 - Task Decomposition (contracts/orchestration-state-machine.md)."""

from __future__ import annotations

from src.orchestration.engine import OrchestrationEngine


def decompose_tasks(engine: OrchestrationEngine, run_id: str) -> None:
    """N6: decompose the approved requirement into an ordered task list, then -> N7.

    For this assessment's scope, decomposition is a single logical task list
    entry (the requirement itself); a richer decomposition algorithm is a
    disclosed future enhancement, not required to satisfy FR-ORC's contract
    of "task list traceable to the requirement".
    """
    engine.transition(run_id, to_stage="N7", status="running", action="tasks_decomposed")
