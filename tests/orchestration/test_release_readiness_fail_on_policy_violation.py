"""Integration test: an injected FAIL policy check yields overall FAIL, never silent PASS (SC-006)."""

import threading
from datetime import datetime, timezone


def test_injected_policy_failure_blocks_release_readiness_end_to_end(tmp_path):
    from src.orchestration.engine import OrchestrationEngine
    from src.orchestration.nodes.n13_release_readiness import evaluate_release_readiness
    from src.persistence.db import ensure_db
    from src.persistence.orchestration_store import (
        AuditEventRepository,
        DecisionRepository,
        PolicyCheckResult,
        PolicyCheckResultRepository,
        WorkflowInstanceRepository,
        new_id,
    )

    conn = ensure_db(str(tmp_path / "release_readiness_scenario.db"))
    lock = threading.Lock()
    engine = OrchestrationEngine(WorkflowInstanceRepository(conn, lock), AuditEventRepository(conn, lock))
    decision_repo = DecisionRepository(conn, lock)
    policy_repo = PolicyCheckResultRepository(conn, lock)
    instance = engine.create_workflow(requirement_id="req-1", initial_stage="N13")

    # Simulate N12 having evaluated the standard checks, with one injected FAIL.
    for policy_id, outcome in [
        ("no-auth-scope-confirmed", "PASS"),
        ("url-validation-present", "PASS"),
        ("audit-append-only", "PASS"),
        ("dependency-license-scan", "FAIL"),  # injected failure
    ]:
        policy_repo.create(PolicyCheckResult(
            result_id=new_id(), run_id=instance.run_id, policy_id=policy_id,
            policy_version="1.0.0", outcome=outcome, evaluated_at=datetime.now(timezone.utc),
        ))

    outcome = evaluate_release_readiness(engine, policy_repo, decision_repo, instance.run_id, actor_role_capacity="release_owner")

    assert outcome.overall == "FAIL"
    assert outcome.failing_policies == ["dependency-license-scan"]

    # The rejection must be recorded as a Decision, not silently swallowed.
    decisions = decision_repo.list_for_run(instance.run_id)
    assert any(d.decision_type == "rejection" and "FAIL" in d.rationale for d in decisions)

    final_instance = engine._workflow_repo.get(instance.run_id)
    assert final_instance.current_stage == "N14"  # still proceeds to summary, per contracts/orchestration-state-machine.md
