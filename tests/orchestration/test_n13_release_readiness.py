"""Unit test: N13 aggregation yields FAIL when any mandatory check FAILs (FR-ORC-017)."""

import threading
from datetime import datetime, timezone


def test_release_readiness_fails_when_any_mandatory_check_fails(tmp_path):
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

    conn = ensure_db(str(tmp_path / "n13_fail_test.db"))
    lock = threading.Lock()
    engine = OrchestrationEngine(WorkflowInstanceRepository(conn, lock), AuditEventRepository(conn, lock))
    decision_repo = DecisionRepository(conn, lock)
    policy_repo = PolicyCheckResultRepository(conn, lock)
    instance = engine.create_workflow(requirement_id="req-1", initial_stage="N13")

    policy_repo.create(PolicyCheckResult(
        result_id=new_id(), run_id=instance.run_id, policy_id="dependency-scan",
        policy_version="1.0.0", outcome="FAIL", evaluated_at=datetime.now(timezone.utc),
    ))
    policy_repo.create(PolicyCheckResult(
        result_id=new_id(), run_id=instance.run_id, policy_id="url-validation-present",
        policy_version="1.0.0", outcome="PASS", evaluated_at=datetime.now(timezone.utc),
    ))

    outcome = evaluate_release_readiness(engine, policy_repo, decision_repo, instance.run_id, actor_role_capacity="release_owner")

    assert outcome.overall == "FAIL"
    assert "dependency-scan" in outcome.failing_policies


def test_release_readiness_passes_when_all_checks_pass(tmp_path):
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

    conn = ensure_db(str(tmp_path / "n13_pass_test.db"))
    lock = threading.Lock()
    engine = OrchestrationEngine(WorkflowInstanceRepository(conn, lock), AuditEventRepository(conn, lock))
    decision_repo = DecisionRepository(conn, lock)
    policy_repo = PolicyCheckResultRepository(conn, lock)
    instance = engine.create_workflow(requirement_id="req-1", initial_stage="N13")

    policy_repo.create(PolicyCheckResult(
        result_id=new_id(), run_id=instance.run_id, policy_id="url-validation-present",
        policy_version="1.0.0", outcome="PASS", evaluated_at=datetime.now(timezone.utc),
    ))

    outcome = evaluate_release_readiness(engine, policy_repo, decision_repo, instance.run_id, actor_role_capacity="release_owner")

    assert outcome.overall == "PASS"
    assert outcome.failing_policies == []
