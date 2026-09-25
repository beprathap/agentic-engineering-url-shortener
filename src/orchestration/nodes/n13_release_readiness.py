"""N13 - Release-Readiness Determination (FR-ORC-016/017, contracts/orchestration-state-machine.md)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from src.orchestration.engine import OrchestrationEngine
from src.persistence.orchestration_store import Decision, DecisionRepository, PolicyCheckResultRepository, PolicyExceptionRepository, new_id


@dataclass
class ReleaseReadinessOutcome:
    overall: str  # "PASS" | "FAIL"
    failing_policies: list[str]


def evaluate_release_readiness(
    engine: OrchestrationEngine,
    policy_repo: PolicyCheckResultRepository,
    decision_repo: DecisionRepository,
    run_id: str,
    actor_role_capacity: str,
    exception_repo: PolicyExceptionRepository | None = None,
) -> ReleaseReadinessOutcome:
    """N13: aggregate all PolicyCheckResults for this run. FAIL blocks release
    unless a non-expired exception exists (FR-ORC-017); overall outcome is
    recorded as a human decision (release_owner), never silently defaulted.
    """
    results = policy_repo.list_for_run(run_id)
    now = datetime.now(timezone.utc)
    failing: list[str] = []

    for result in results:
        if result.outcome == "PASS" or result.outcome == "NOT_APPLICABLE":
            continue
        if result.outcome == "EXCEPTION_REQUESTED" and result.exception_id and exception_repo is not None:
            exception = exception_repo.get(result.exception_id)
            if exception is not None and exception.expires_at > now:
                continue  # valid, non-expired exception covers this FAIL
        failing.append(result.policy_id)

    overall = "FAIL" if failing else "PASS"

    decision_repo.create(
        Decision(
            decision_id=new_id(),
            run_id=run_id,
            decision_type="approval" if overall == "PASS" else "rejection",
            actor_role_capacity=actor_role_capacity,
            rationale=f"release-readiness outcome: {overall}" + (f" (failing: {failing})" if failing else ""),
            created_at=now,
        )
    )
    engine.emit(
        run_id,
        actor_type="system",
        action="release_readiness_evaluated",
        result="success" if overall == "PASS" else "failure",
        affected_artifact=overall,
        reason=None if overall == "PASS" else f"mandatory policy check(s) failing: {failing}",
    )
    engine.transition(run_id, to_stage="N14", status="running", action="release_readiness_recorded")

    return ReleaseReadinessOutcome(overall=overall, failing_policies=failing)
