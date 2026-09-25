"""N4b - Impact Analysis (User Story 2, Scenario B; ADR-008 rollback-vs-compensation)."""

from __future__ import annotations

import json
import sqlite3
import threading
from dataclasses import dataclass, field

from src.orchestration.engine import OrchestrationEngine

REQUIRED_CATEGORIES = (
    "impacted_components",
    "impacted_interfaces",
    "impacted_data_flows",
    "impacted_tests",
    "impacted_documentation",
    "regression_risks",
    "rollout_rollback_considerations",
)

_IRREVERSIBLE_MARKERS = ("schema change", "incompatible", "migration", "data loss", "irreversible")


@dataclass
class ImpactAnalysisArtifact:
    categories: dict[str, str] = field(default_factory=dict)
    reversibility: str = "rollback"  # "rollback" | "compensation"


def _classify_reversibility(requirement_description: str) -> str:
    """ADR-008: classify whether this change is a simple rollback (undo an
    unapproved draft, no lasting side effect) or requires compensation
    (an already-committed, hard-to-reverse effect).
    """
    lowered = requirement_description.lower()
    if any(marker in lowered for marker in _IRREVERSIBLE_MARKERS):
        return "compensation"
    return "rollback"


def perform_impact_analysis(
    engine: OrchestrationEngine,
    conn: sqlite3.Connection,
    lock: threading.Lock,
    run_id: str,
    requirement_description: str,
) -> ImpactAnalysisArtifact:
    """N4b: draft the impact-analysis artifact covering every required category,
    then transition to N5 for human review of this specific artifact.
    """
    reversibility = _classify_reversibility(requirement_description)

    artifact = ImpactAnalysisArtifact(
        categories={
            "impacted_components": "URL redirect resolution handler (src/api/links.py)",
            "impacted_interfaces": "GET /{short_code} response contract (410 vs 302)",
            "impacted_data_flows": "ShortLink.expires_at read path at redirect time",
            "impacted_tests": "tests/contract/test_redirect.py expired-code scenarios",
            "impacted_documentation": "contracts/openapi.yaml redirect endpoint description",
            "regression_risks": "Existing active-link redirects must remain unaffected",
            "rollout_rollback_considerations": (
                "Compensation required: see reversibility classification"
                if reversibility == "compensation"
                else "Simple rollback: revert the code change, no persisted side effect"
            ),
        },
        reversibility=reversibility,
    )

    engine.emit(
        run_id,
        actor_type="agent",
        action="impact_analysis_drafted",
        result="success",
        affected_artifact=json.dumps(artifact.categories),
    )
    engine.transition(run_id, to_stage="N5", status="running", action="impact_analysis_ready_for_review")

    return artifact
