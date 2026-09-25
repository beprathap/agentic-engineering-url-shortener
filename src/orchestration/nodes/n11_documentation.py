"""N11 - Documentation (contracts/orchestration-state-machine.md, parallel with N10/N12)."""

from __future__ import annotations

from src.orchestration.clock import Clock, SystemClock
from src.orchestration.engine import OrchestrationEngine, retry_with_backoff


def update_documentation(engine: OrchestrationEngine, run_id: str, clock: Clock | None = None) -> None:
    """N11: record that documentation/traceability artifacts were updated for this run.

    Applies the shared bounded-retry utility on transient failure, per
    contracts/orchestration-state-machine.md's N11 retry policy (convergence
    finding F3).
    """
    clock = clock or SystemClock()
    retry_with_backoff(
        lambda: engine.emit(run_id, actor_type="agent", action="documentation_updated", result="success"),
        clock=clock,
    )
