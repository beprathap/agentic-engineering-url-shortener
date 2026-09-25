"""Workflow resumption after interruption (FR-ORC-011, User Story 8).

Dispatches based on WorkflowInstance.current_stage, loaded fresh from
persisted state — this works whether the calling process is the one that
was interrupted or a brand new process reconnecting to the same database,
which is the actual guarantee FR-ORC-011 requires.
"""

from __future__ import annotations

import sqlite3
import threading

from src.orchestration.engine import OrchestrationEngine

# Stages that are pure re-entry points: resuming here means simply recording
# that resumption occurred, then letting the normal caller-driven flow
# (API request, next test step, etc.) continue from this stage. No node's
# side-effecting work is re-executed by this dispatcher itself.
_RESUMABLE_STAGES = ("N1", "N2", "N3", "N4", "N4b", "N5", "N6", "N7", "N8", "N9", "N13")


class UnresumableStateError(RuntimeError):
    """Raised when a workflow's persisted state cannot be safely resumed
    (e.g., a corrupted or unrecognized current_stage) — refuses silent
    resumption and surfaces the condition for human decision (edge case)."""


def resume_workflow(
    engine: OrchestrationEngine,
    conn: sqlite3.Connection,
    lock: threading.Lock,
    run_id: str,
) -> None:
    instance = engine._workflow_repo.get(run_id)
    if instance is None:
        raise UnresumableStateError(f"no WorkflowInstance found for run_id={run_id}")

    if instance.status == "completed":
        return  # nothing to resume; already terminal

    if instance.current_stage not in _RESUMABLE_STAGES and instance.current_stage != "SAFE_STOP":
        raise UnresumableStateError(
            f"run {run_id} has unrecognized current_stage={instance.current_stage!r}; refusing silent resumption"
        )

    engine.emit(
        run_id,
        actor_type="system",
        action="workflow_resumed",
        result="success",
        affected_artifact=instance.current_stage,
    )
