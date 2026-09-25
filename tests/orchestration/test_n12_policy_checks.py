"""Unit test: N12 policy evaluation conforms to policy-evaluation.schema.json (FR-ORC-016)."""

import json
import threading
from pathlib import Path

import jsonschema

SCHEMA_PATH = Path(__file__).parents[2] / "specs" / "001-agentic-url-shortener" / "contracts" / "schemas" / "policy-evaluation.schema.json"


def test_policy_check_results_conform_to_schema(tmp_path):
    from src.orchestration.engine import OrchestrationEngine
    from src.orchestration.nodes.n12_security import evaluate_security_policies
    from src.persistence.db import ensure_db
    from src.persistence.orchestration_store import AuditEventRepository, PolicyCheckResultRepository, WorkflowInstanceRepository

    conn = ensure_db(str(tmp_path / "n12_test.db"))
    lock = threading.Lock()
    engine = OrchestrationEngine(WorkflowInstanceRepository(conn, lock), AuditEventRepository(conn, lock))
    policy_repo = PolicyCheckResultRepository(conn, lock)
    instance = engine.create_workflow(requirement_id="req-1", initial_stage="N12")

    results = evaluate_security_policies(engine, policy_repo, instance.run_id)

    schema = json.loads(SCHEMA_PATH.read_text())
    assert results
    for result in results:
        instance_dict = {
            "result_id": result.result_id,
            "run_id": result.run_id,
            "policy_id": result.policy_id,
            "policy_version": result.policy_version,
            "outcome": result.outcome,
            "evaluated_at": result.evaluated_at.isoformat(),
            "exception_id": result.exception_id,
        }
        jsonschema.validate(instance=instance_dict, schema=schema)
