"""N14 - Final Engineering Summary (FR-ORC-019, contracts/orchestration-state-machine.md)."""

from __future__ import annotations

from dataclasses import dataclass

from src.orchestration.engine import OrchestrationEngine


@dataclass
class FinalSummary:
    run_id: str
    audit_event_count: int
    decision_count: int


def generate_final_summary(engine: OrchestrationEngine, run_id: str) -> FinalSummary:
    """N14: produce a summary derived from recorded evidence, not freeform
    narrative (FR-ORC-019). Terminal node: marks the workflow completed.
    """
    events = engine._audit_repo.list_for_run(run_id)
    summary = FinalSummary(run_id=run_id, audit_event_count=len(events), decision_count=0)

    engine.emit(run_id, actor_type="system", action="final_summary_generated", result="success")
    engine.transition(run_id, to_stage="N14", status="completed", action="workflow_completed")

    return summary
