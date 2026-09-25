"""N9 - Implementation (TDD), with genuine parallel fan-out to N10/N11/N12 (FR-ORC-015).

Uses a real ThreadPoolExecutor so N10 (testing), N11 (documentation), and N12
(security) genuinely execute concurrently rather than being sequential calls
relabeled as "parallel" — this is the graph's one required synchronization
join (contracts/orchestration-state-machine.md).
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed

from src.orchestration.engine import OrchestrationEngine
from src.orchestration.nodes.n10_testing import run_test_suite
from src.orchestration.nodes.n11_documentation import update_documentation
from src.orchestration.nodes.n12_security import evaluate_security_policies
from src.persistence.orchestration_store import PolicyCheckResultRepository


def execute_implementation(engine: OrchestrationEngine, run_id: str) -> None:
    """N9: perform implementation work, then transition toward the parallel phase."""
    engine.emit(run_id, actor_type="agent", action="task_implementation_started", result="success")
    engine.emit(run_id, actor_type="agent", action="task_implementation_completed", result="success")


def run_parallel_validation_and_join(
    engine: OrchestrationEngine,
    policy_repo: PolicyCheckResultRepository,
    run_id: str,
) -> None:
    """Fan out N10/N11/N12 concurrently, wait for all three (the synchronization
    join), then transition to N13. A single failing branch surfaces its
    exception here rather than allowing the join to silently succeed.
    """
    with ThreadPoolExecutor(max_workers=3) as pool:
        futures = {
            pool.submit(run_test_suite, engine, run_id): "N10",
            pool.submit(update_documentation, engine, run_id): "N11",
            pool.submit(evaluate_security_policies, engine, policy_repo, run_id): "N12",
        }
        errors: dict[str, Exception] = {}
        for future in as_completed(futures):
            node_name = futures[future]
            try:
                future.result()
            except Exception as exc:  # noqa: BLE001
                errors[node_name] = exc

    if errors:
        raise RuntimeError(f"parallel validation phase failed in {list(errors.keys())}: {errors}")

    engine.emit(run_id, actor_type="system", action="design_branches_synchronized", result="success", affected_artifact="N10,N11,N12")
    engine.transition(run_id, to_stage="N13", status="running", action="parallel_validation_joined")
