"""Unit test: irreversible actions require a preceding approval Decision (NFR-011)."""

import threading

import pytest


def test_irreversible_action_blocked_without_prior_approval(tmp_path):
    from src.orchestration.engine import IrreversibleActionNotApproved, require_prior_approval
    from src.persistence.db import ensure_db
    from src.persistence.orchestration_store import DecisionRepository, new_id

    conn = ensure_db(str(tmp_path / "autonomy_test.db"))
    lock = threading.Lock()
    decision_repo = DecisionRepository(conn, lock)
    run_id = new_id()

    with pytest.raises(IrreversibleActionNotApproved):
        require_prior_approval(decision_repo, run_id)


def test_irreversible_action_allowed_after_recorded_approval(tmp_path):
    from datetime import datetime, timezone

    from src.orchestration.engine import require_prior_approval
    from src.persistence.db import ensure_db
    from src.persistence.orchestration_store import Decision, DecisionRepository, new_id

    conn = ensure_db(str(tmp_path / "autonomy_test2.db"))
    lock = threading.Lock()
    decision_repo = DecisionRepository(conn, lock)
    run_id = new_id()

    decision_repo.create(
        Decision(
            decision_id=new_id(),
            run_id=run_id,
            decision_type="approval",
            actor_role_capacity="release_owner",
            rationale="approved for this run",
            created_at=datetime.now(timezone.utc),
        )
    )

    require_prior_approval(decision_repo, run_id)  # must not raise
