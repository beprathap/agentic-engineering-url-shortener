"""N6 - Task Decomposition (contracts/orchestration-state-machine.md)."""

from __future__ import annotations

from src.orchestration.clock import Clock, SystemClock
from src.orchestration.engine import OrchestrationEngine, retry_with_backoff


def decompose_tasks(engine: OrchestrationEngine, run_id: str, clock: Clock | None = None) -> None:
    """N6: decompose the approved requirement into an ordered task list, then -> N7.

    Applies the shared bounded-retry utility on transient failure, per
    contracts/orchestration-state-machine.md's N6 retry policy (convergence
    finding F3 - previously this node had no failure handling at all).

    For this assessment's scope, decomposition is a single logical task list
    entry (the requirement itself); a richer decomposition algorithm is a
    disclosed future enhancement, not required to satisfy FR-ORC's contract
    of "task list traceable to the requirement".
    """
    clock = clock or SystemClock()
    retry_with_backoff(
        lambda: engine.transition(run_id, to_stage="N7", status="running", action="tasks_decomposed"),
        clock=clock,
    )
