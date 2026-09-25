"""N12 - Security & Risk Validation (contracts/orchestration-state-machine.md, parallel with N10/N11)."""

from __future__ import annotations

from src.orchestration.engine import OrchestrationEngine, utcnow
from src.persistence.orchestration_store import PolicyCheckResult, PolicyCheckResultRepository, new_id
from src.policy.checks import POLICY_VERSION, default_policy_checks


def evaluate_security_policies(
    engine: OrchestrationEngine,
    policy_repo: PolicyCheckResultRepository,
    run_id: str,
) -> list[PolicyCheckResult]:
    """N12: evaluate every applicable policy check, recording exactly one
    PolicyCheckResult per policy (FR-ORC-016). This node evaluates and records;
    N13 is responsible for aggregating into an overall release-readiness outcome.
    """
    results = []
    for check in default_policy_checks():
        outcome = "PASS" if check.evaluate() else "FAIL"
        result = PolicyCheckResult(
            result_id=new_id(),
            run_id=run_id,
            policy_id=check.policy_id,
            policy_version=POLICY_VERSION,
            outcome=outcome,
            evaluated_at=utcnow(),
        )
        policy_repo.create(result)
        engine.emit(
            run_id,
            actor_type="system",
            action="policy_check_evaluated",
            result="success",
            affected_artifact=check.policy_id,
        )
        results.append(result)
    return results
