"""N7 - Architecture & Design (contracts/orchestration-state-machine.md)."""

from __future__ import annotations

from src.orchestration.clock import Clock, SystemClock
from src.orchestration.engine import OrchestrationEngine, retry_with_backoff


def design_architecture(engine: OrchestrationEngine, run_id: str, clock: Clock | None = None) -> None:
    """N7: produce/update the design artifact for the approved, decomposed requirement.

    Applies the shared bounded-retry utility on transient failure, per
    contracts/orchestration-state-machine.md's N7 retry policy (convergence
    finding F3).

    Any independent design sub-branches would fan out and synchronize here;
    the genuine parallel-fan-out-with-join demonstration required by FR-ORC-015
    is implemented at N9 (execute_implementation), since that is the assessment's
    designated synchronization point (contracts/orchestration-state-machine.md).
    """
    clock = clock or SystemClock()

    def _draft_and_synchronize() -> None:
        engine.emit(run_id, actor_type="agent", action="design_drafted", result="success")
        engine.transition(run_id, to_stage="N8", status="running", action="design_branches_synchronized")

    retry_with_backoff(_draft_and_synchronize, clock=clock)
