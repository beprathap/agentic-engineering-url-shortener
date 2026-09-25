"""Unit test: an expired PolicyException reverts its check to FAIL (data-model.md invariant, FR-ORC-018)."""

import threading
from datetime import datetime, timedelta, timezone


def test_expired_exception_causes_release_readiness_to_fail(tmp_path):
    from src.orchestration.engine import OrchestrationEngine
    from src.orchestration.nodes.n13_release_readiness import evaluate_release_readiness
    from src.persistence.db import ensure_db
    from src.persistence.orchestration_store import (
        AuditEventRepository,
        DecisionRepository,
        PolicyCheckResult,
        PolicyCheckResultRepository,
        PolicyException,
        PolicyExceptionRepository,
        WorkflowInstanceRepository,
        new_id,
    )

    conn = ensure_db(str(tmp_path / "exception_expiry_test.db"))
    lock = threading.Lock()
    engine = OrchestrationEngine(WorkflowInstanceRepository(conn, lock), AuditEventRepository(conn, lock))
    decision_repo = DecisionRepository(conn, lock)
    policy_repo = PolicyCheckResultRepository(conn, lock)
    exception_repo = PolicyExceptionRepository(conn, lock)
    instance = engine.create_workflow(requirement_id="req-1", initial_stage="N13")

    now = datetime.now(timezone.utc)
    exception_id = new_id()
    exception_repo.create(PolicyException(
        exception_id=exception_id,
        applicable_policy="dependency-scan",
        reason="known low-severity CVE, fix pending upstream",
        scope="this run only",
        approving_authority="release_owner",
        compensating_control="manual review completed",
        approved_at=now - timedelta(days=10),
        expires_at=now - timedelta(days=1),  # already expired
    ))
    policy_repo.create(PolicyCheckResult(
        result_id=new_id(), run_id=instance.run_id, policy_id="dependency-scan",
        policy_version="1.0.0", outcome="EXCEPTION_REQUESTED", evaluated_at=now,
        exception_id=exception_id,
    ))

    outcome = evaluate_release_readiness(
        engine, policy_repo, decision_repo, instance.run_id,
        actor_role_capacity="release_owner", exception_repo=exception_repo,
    )

    assert outcome.overall == "FAIL"
    assert "dependency-scan" in outcome.failing_policies


def test_non_expired_exception_does_not_block_release(tmp_path):
    from src.orchestration.engine import OrchestrationEngine
    from src.orchestration.nodes.n13_release_readiness import evaluate_release_readiness
    from src.persistence.db import ensure_db
    from src.persistence.orchestration_store import (
        AuditEventRepository,
        DecisionRepository,
        PolicyCheckResult,
        PolicyCheckResultRepository,
        PolicyException,
        PolicyExceptionRepository,
        WorkflowInstanceRepository,
        new_id,
    )

    conn = ensure_db(str(tmp_path / "exception_valid_test.db"))
    lock = threading.Lock()
    engine = OrchestrationEngine(WorkflowInstanceRepository(conn, lock), AuditEventRepository(conn, lock))
    decision_repo = DecisionRepository(conn, lock)
    policy_repo = PolicyCheckResultRepository(conn, lock)
    exception_repo = PolicyExceptionRepository(conn, lock)
    instance = engine.create_workflow(requirement_id="req-1", initial_stage="N13")

    now = datetime.now(timezone.utc)
    exception_id = new_id()
    exception_repo.create(PolicyException(
        exception_id=exception_id,
        applicable_policy="dependency-scan",
        reason="known low-severity CVE, fix pending upstream",
        scope="this run only",
        approving_authority="release_owner",
        compensating_control="manual review completed",
        approved_at=now,
        expires_at=now + timedelta(days=30),  # still valid
    ))
    policy_repo.create(PolicyCheckResult(
        result_id=new_id(), run_id=instance.run_id, policy_id="dependency-scan",
        policy_version="1.0.0", outcome="EXCEPTION_REQUESTED", evaluated_at=now,
        exception_id=exception_id,
    ))

    outcome = evaluate_release_readiness(
        engine, policy_repo, decision_repo, instance.run_id,
        actor_role_capacity="release_owner", exception_repo=exception_repo,
    )

    assert outcome.overall == "PASS"
