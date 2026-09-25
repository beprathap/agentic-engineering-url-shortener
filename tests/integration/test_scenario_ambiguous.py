"""Integration test: full Ambiguous-Requirement scenario (SC-004, User Story 3)."""

import threading


def test_ambiguous_requirement_blocked_until_clarified_then_resumes(tmp_path):
    from src.orchestration.clock import FakeClock
    from src.orchestration.engine import OrchestrationEngine
    from src.orchestration.gates import answer_clarification, approve_requirements_gate, request_clarification, request_requirements_gate
    from src.orchestration.nodes.n1_ingestion import ingest_requirement
    from src.orchestration.nodes.n2_normalization import normalize_requirement
    from src.orchestration.nodes.n3_classification import classify_requirement
    from src.orchestration.nodes.n6_decomposition import decompose_tasks
    from src.persistence.db import ensure_db
    from src.persistence.orchestration_store import AuditEventRepository, DecisionRepository, WorkflowInstanceRepository

    conn = ensure_db(str(tmp_path / "ambiguous_scenario.db"))
    lock = threading.Lock()
    engine = OrchestrationEngine(WorkflowInstanceRepository(conn, lock), AuditEventRepository(conn, lock))
    decision_repo = DecisionRepository(conn, lock)
    clock = FakeClock()

    ingestion = ingest_requirement(engine, conn, lock, raw_input="Make links expire eventually.")
    run_id = ingestion.run_id
    requirement_id = ingestion.requirement_id

    normalize_requirement(engine, conn, lock, run_id, requirement_id, clock=clock)
    classification = classify_requirement(engine, conn, lock, run_id, requirement_id)
    assert classification.classification == "ambiguous"

    # Must never reach N6 (decomposition) before clarification is resolved.
    events_before = engine._audit_repo.list_for_run(run_id)
    assert not any(e.action == "tasks_decomposed" for e in events_before)

    request_clarification(
        engine, run_id,
        question="What is the intended expiration duration?",
        impact="Cannot proceed to decomposition without a concrete duration",
        current_assumption="none",
        owner="human",
        clock=clock,
    )
    pending = engine._workflow_repo.get(run_id)
    assert pending.status == "clarification_pending"

    answer_clarification(
        engine, decision_repo, run_id,
        actor_role_capacity="reviewer_approver",
        answer="Default expiration is 90 days unless specified (PVT-001).",
    )

    # Re-normalize and re-classify with the clarified context (simulated by
    # updating normalized_description directly, since the clarification answer
    # itself is the missing piece of context).
    with lock:
        conn.execute(
            "UPDATE requirements SET normalized_description = ? WHERE requirement_id = ?",
            ("Make links expire after 90 days by default unless a caller-specified expiration is provided.", requirement_id),
        )
        conn.commit()
    reclassification = classify_requirement(engine, conn, lock, run_id, requirement_id)
    assert reclassification.classification == "greenfield"

    request_requirements_gate(engine, run_id, classification="greenfield", clock=clock)
    approve_requirements_gate(engine, decision_repo, run_id, actor_role_capacity="reviewer_approver", rationale="approved after clarification")
    decompose_tasks(engine, run_id)

    final_events = engine._audit_repo.list_for_run(run_id)
    assert any(e.action == "clarification_requested" for e in final_events)
    assert any(e.action == "clarification_answered" for e in final_events)
    assert any(e.action == "tasks_decomposed" for e in final_events)
