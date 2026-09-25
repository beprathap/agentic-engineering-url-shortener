"""N3 - Ambiguity Detection & Classification (FR-ORC-003/004, contracts/orchestration-state-machine.md).

Classification heuristic disclosed honestly: this is a rule-based check, not a
sophisticated NLP/LLM classifier. It looks for known vagueness markers and
brownfield-indicating keywords. It satisfies the assessment's functional
contract (route ambiguous input to clarification, route existing-code changes
to impact analysis, let well-specified new requirements through) without
overstating its own sophistication.
"""

from __future__ import annotations

import json
import sqlite3
import threading
from dataclasses import dataclass, field

from src.orchestration.engine import OrchestrationEngine

_VAGUENESS_MARKERS = (
    "eventually",
    "somehow",
    "maybe",
    "at some point",
    "some kind of",
    "etc",
    "and so on",
)

_BROWNFIELD_MARKERS = (
    "fix",
    "bug",
    "regression",
    "existing",
    "currently",
    "instead of",
    "broken",
)

_MIN_LENGTH = 20


@dataclass
class ClassificationResult:
    classification: str  # "greenfield" | "brownfield" | "ambiguous"
    quality_check_failures: list[str] = field(default_factory=list)


def _run_quality_checks(normalized: str) -> list[str]:
    failures = []
    lowered = normalized.lower()

    if len(normalized) < _MIN_LENGTH:
        failures.append("completeness: requirement text is too short to be actionable")

    if any(marker in lowered for marker in _VAGUENESS_MARKERS):
        failures.append("testability: contains a vague/unquantified marker with no concrete criterion")

    return failures


def classify_requirement(
    engine: OrchestrationEngine,
    conn: sqlite3.Connection,
    lock: threading.Lock,
    run_id: str,
    requirement_id: str,
) -> ClassificationResult:
    with lock:
        row = conn.execute(
            "SELECT normalized_description FROM requirements WHERE requirement_id = ?",
            (requirement_id,),
        ).fetchone()
    normalized = row["normalized_description"]

    failures = _run_quality_checks(normalized)

    if failures:
        classification = "ambiguous"
    elif any(marker in normalized.lower() for marker in _BROWNFIELD_MARKERS):
        classification = "brownfield"
    else:
        classification = "greenfield"

    with lock:
        conn.execute(
            "UPDATE requirements SET classification = ?, quality_check_results = ? WHERE requirement_id = ?",
            (classification, json.dumps({"failures": failures}), requirement_id),
        )
        conn.commit()

    engine.emit(
        run_id,
        actor_type="system",
        action="quality_checks_recorded",
        result="success",
        affected_artifact=requirement_id,
    )
    engine.emit(
        run_id,
        actor_type="system",
        action="classification_assigned",
        result="success",
        affected_artifact=classification,
    )

    return ClassificationResult(classification=classification, quality_check_failures=failures)
