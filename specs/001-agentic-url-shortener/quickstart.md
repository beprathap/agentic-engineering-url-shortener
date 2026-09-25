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

## Validation Scenario 2 — Greenfield Requirement (User Story 1)

```bash
# Submit a well-specified requirement to the orchestration ingestion endpoint (implementation-defined path, e.g. /v1/workflows)
curl -s -X POST http://localhost:8000/v1/workflows \
  -H "Content-Type: application/json" \
  -d '{"raw_input": "Add redirect_count and last_accessed_at to the short link detail response (already defined in ShortLinkDetail schema)."}' | jq
# Expected: run_id returned; workflow proceeds to N3 classification=greenfield,
# then directly to N5 (Human Approval Gate: Requirements) — NOT N4 (clarification).

# Inspect the audit trail for the run
curl -s http://localhost:8000/v1/workflows/<run_id>/audit | jq
# Expected: audit events show quality_checks_recorded, classification_assigned (greenfield),
# NO clarification_requested event, then requirements_approval_requested.
```

**Pass criteria**: SC-002 — no clarification gate invoked for this well-specified requirement.

## Validation Scenario 3 — Ambiguous Requirement (User Story 3 / Scenario C)

```bash
curl -s -X POST http://localhost:8000/v1/workflows \
  -H "Content-Type: application/json" \
  -d '{"raw_input": "Make links expire eventually."}' | jq
# Expected: classification=ambiguous; workflow enters N4 (clarification_pending)

curl -s http://localhost:8000/v1/workflows/<run_id> | jq
# Expected: status=clarification_pending; current_stage=N4

# Answer the clarification (implementation-defined endpoint)
curl -s -X POST http://localhost:8000/v1/workflows/<run_id>/clarify \
  -H "Content-Type: application/json" \
  -d '{"answer": "Default expiration is 90 days unless specified.", "actor_role_capacity": "reviewer_approver"}' | jq
# Expected: status transitions back to running, current_stage resumes at N2
```

**Pass criteria**: SC-004 — workflow never reaches N6 (task decomposition) before the clarification decision is recorded.

## Validation Scenario 4 — Brownfield Change (User Story 2 / Scenario B)

```bash
curl -s -X POST http://localhost:8000/v1/workflows \
  -H "Content-Type: application/json" \
  -d '{"raw_input": "Fix: redirect resolution currently returns 302 for expired short codes instead of 410."}' | jq
# Expected: classification=brownfield; workflow enters N4b (impact_analysis) before N5

curl -s http://localhost:8000/v1/workflows/<run_id>/impact-analysis | jq
# Expected: artifact includes impacted components, interfaces, data flows, tests,
# documentation, regression risks, rollout/rollback considerations — none omitted.
```

**Pass criteria**: SC-003 — impact-analysis artifact exists and is human-approved before N6.

## Validation Scenario 5 — Safe-Stop on Approval Timeout (User Story 4 / Edge Case)

Run with a shortened test-only timeout override (implementation MUST expose a test hook for this — e.g., a config override — rather than actually waiting 24 hours):

```bash
# (test harness fast-forwards the gate's internal clock past 24h)
pytest tests/orchestration/test_safe_stop_on_timeout.py -v
```

**Pass criteria**: SC-005 — the workflow transitions to `safe_stopped` with `reason=requirements_gate_timeout` (or the applicable gate name) recorded in the audit trail; it never auto-advances.

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
