# Quickstart: Agentic Software Engineering System: URL Shortener

This validates that the implemented prototype satisfies the approved spec end-to-end. It assumes the architecture decisions in `research.md` (Python 3.12, FastAPI, SQLite, custom orchestration engine) have been approved and implemented per `tasks.md`.

## Prerequisites

- Python 3.12+ installed locally.
- Repository dependencies installed (implementation phase will define the exact dependency manifest, e.g. `pyproject.toml` / `requirements.txt`, per `research.md` Decisions 1–5).
- No external services required (SQLite is file-backed; no network dependency) per CON-002/D-003.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .            # or: pip install -r requirements.txt
```

## Running the Service

```bash
uvicorn src.api.app:app --reload --port 8000
```

Verify readiness:

```bash
curl -s http://localhost:8000/healthz | jq
# Expected: {"status": "ready"}
```

## Validation Scenario 1 — Short Link Lifecycle (FR-SVC-001..011)

```bash
# Create a short link
curl -s -X POST http://localhost:8000/v1/links \
  -H "Content-Type: application/json" \
  -d '{"target_url": "https://example.com/some/long/path"}' | jq
# Expected: 201, short_code matches ^[0-9a-zA-Z]{7}$ (Base62, 7 chars per Clarifications)

# Same target URL again — expect a DIFFERENT short code (no de-duplication)
curl -s -X POST http://localhost:8000/v1/links \
  -H "Content-Type: application/json" \
  -d '{"target_url": "https://example.com/some/long/path"}' | jq

# Redirect resolution
curl -s -i http://localhost:8000/<short_code>
# Expected: 302 with Location header set to target_url

# Redirect for unknown code
curl -s -i http://localhost:8000/zzzzzzz
# Expected: 404, error_code=NOT_FOUND

# Invalid scheme rejected
curl -s -i -X POST http://localhost:8000/v1/links \
  -H "Content-Type: application/json" \
  -d '{"target_url": "javascript:alert(1)"}'
# Expected: 400, error_code=INVALID_URL

# Idempotency
curl -s -X POST http://localhost:8000/v1/links \
  -H "Content-Type: application/json" -H "Idempotency-Key: demo-key-1" \
  -d '{"target_url": "https://example.com/idem"}' | jq
curl -s -X POST http://localhost:8000/v1/links \
  -H "Content-Type: application/json" -H "Idempotency-Key: demo-key-1" \
  -d '{"target_url": "https://example.com/idem"}' | jq
# Expected: both calls return the identical short_code
```

**Pass criteria**: All responses match `contracts/openapi.yaml`; validated automatically via the contract test suite (`tests/contract/`) using `jsonschema` against the schemas in `contracts/schemas/`.

## Implementation Scope Note (as of 2026-09-25, T001-T117)

The HTTP API currently exposes only workflow **creation** (`POST /v1/workflows`,
which runs N1 only), **inspection** (`GET /v1/workflows/{run_id}`), and
**audit** (`GET /v1/workflows/{run_id}/audit`). It does **not** expose an
endpoint to drive N2 through N14, answer a clarification, or review an
impact-analysis artifact over HTTP — those node behaviors (N2-N14, gates,
clarification, impact analysis, replanning, resumption) are implemented as
Python functions in `src/orchestration/` and are exercised end-to-end by the
integration test suite (`tests/integration/test_scenario_*.py`), not by a
fully HTTP-wired pipeline. This is a disclosed scope boundary, not an
oversight: building a governed HTTP surface for every gate action was judged
lower priority than proving the orchestration semantics themselves work
correctly, given the 2-3 day timebox (plan.md §Planning Constraints). Wiring
a full HTTP-driven pipeline is a reasonable brownfield enhancement.

Scenarios 2-5 below are therefore validated via **pytest**, not curl, against
the real orchestration engine and a real SQLite database — this is genuine
execution evidence, just not over HTTP.

## Validation Scenario 2 — Greenfield Requirement (User Story 1)

```bash
pytest tests/integration/test_scenario_greenfield.py -v
```

Drives N1 through N14 directly via the orchestration functions, asserting no
`clarification_requested` event fires for a well-specified requirement and
the run reaches `completed`.

**Pass criteria**: SC-002 — no clarification gate invoked for this well-specified requirement.

## Validation Scenario 3 — Ambiguous Requirement (User Story 3 / Scenario C)

```bash
pytest tests/integration/test_scenario_ambiguous.py -v
```

Confirms an incomplete requirement is classified ambiguous, blocks before N6,
enters `clarification_pending`, and resumes at N2 (not from zero) once a
human clarification answer is recorded.

**Pass criteria**: SC-004 — workflow never reaches N6 (task decomposition) before the clarification decision is recorded.

## Validation Scenario 4 — Brownfield Change (User Story 2 / Scenario B)

```bash
pytest tests/integration/test_scenario_brownfield.py -v
```

Confirms a defect-correction requirement is classified brownfield, produces a
complete N4b impact-analysis artifact (all 7 required categories), and that
no implementation task is authorized (`tasks_decomposed` never fires) before
that artifact is human-approved.

**Pass criteria**: SC-003 — impact-analysis artifact exists and is human-approved before N6.

## Validation Scenario 5 — Safe-Stop on Approval Timeout (User Story 4 / Edge Case)

Uses the injectable clock abstraction (`src/orchestration/clock.py`, `FakeClock`) to fast-forward simulated time past the 24h gate timeout, rather than actually waiting 24 hours:

```bash
pytest tests/orchestration/test_n5_requirements_gate.py::test_gate_timeout_after_24_hours_enters_safe_stop -v
pytest tests/orchestration/test_n4_clarification.py::test_clarification_gate_timeout_enters_safe_stop_never_auto_answers -v
```

**Pass criteria**: SC-005 — the workflow transitions to `safe_stopped` with the applicable gate's timeout reason recorded in the audit trail; it never auto-advances.

## Validation Scenario 6 — Release-Readiness FAIL (User Story 5)

```bash
pytest tests/orchestration/test_release_readiness_fail_on_policy_violation.py -v
```

**Pass criteria**: SC-006 — injecting a FAIL policy check with no exception yields an overall FAIL release-readiness outcome, not a silent PASS.

## Validation Scenario 7 — Audit Reconstruction (User Story 6)

```bash
curl -s http://localhost:8000/v1/workflows/<completed_run_id>/audit | jq
```

**Pass criteria**: SC-008 — every state transition, decision, approval, retry, failure, and replanning event for the run is present with actor type, action, timestamp, affected artifact/state, result, and reason; a reviewer with no other context can reconstruct the sequence.

## Full Automated Suite

```bash
pytest tests/ -v
```

Expected: unit, integration, contract (`tests/contract/`, validated against `contracts/openapi.yaml` and `contracts/schemas/*.json`), and orchestration-transition tests (`tests/orchestration/`) all pass, per NFR-009 (every functional requirement maps to at least one automated test).
