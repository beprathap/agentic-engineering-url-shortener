# Reviewer Navigation Guide

**Read this first**: this system has no authentication anywhere. That is a deliberate, human-confirmed scope decision, not an oversight.

## 1. Project Objective
`specs/001-agentic-url-shortener/spec.md`, Input section. A governed agentic orchestration engine, demonstrated via a URL shortener.

## 2. How to Run the Application
```bash
python3 -m venv .venv && source .venv/bin/activate && pip install -e ".[dev]"
uvicorn src.api.app:app --reload --port 8000
```
Expected: `Application startup complete.` — `curl http://localhost:8000/healthz` → `{"status":"ready"}`. [FR-SVC-011]

## 3. How to Run Tests
```bash
pytest -q
```
Expected: `94 passed`. [NFR-009]

## 4. How to Exercise the URL Shortener
```bash
curl -X POST http://localhost:8000/v1/links -H "Content-Type: application/json" -d '{"target_url": "https://example.com"}'
```
Expected: `201`, a 7-character Base62 `short_code`. Then `curl -i http://localhost:8000/<short_code>` → `302` with `Location` header. [FR-SVC-001, FR-SVC-004]

## 5. How to Initiate an Orchestration Workflow
```bash
curl -X POST http://localhost:8000/v1/workflows -H "Content-Type: application/json" -d '{"raw_input": "Add a feature."}'
```
Expected: `201`, a `run_id`. **Note**: this triggers N1 only — see item 23 below for the full pipeline. [FR-ORC-001]

## 6. How to Inspect Workflow State
```bash
curl http://localhost:8000/v1/workflows/<run_id>
curl http://localhost:8000/v1/workflows/<run_id>/audit
```
Expected: current stage/status; full audit event list. [FR-ORC-002, FR-ORC-014]

## 7. How to Perform a Human Approval
```bash
pytest tests/orchestration/test_n5_requirements_gate.py -v
```
Expected: 2 passed — one demonstrates an explicit approval advancing the workflow, one demonstrates a 24h-unanswered gate entering `safe_stopped` (never auto-approving). [FR-ORC-005, FR-ORC-006]

## 8. How to Demonstrate Retry
```bash
pytest tests/orchestration/test_retry_policy.py tests/orchestration/test_retry_policy_cross_node.py -v
```
Expected: 4 passed — bounded retry (3 attempts, 200ms exponential backoff) via an injectable clock, no real waiting. [FR-ORC-007]

## 9. How to Demonstrate Compensation or Rollback
```bash
pytest tests/orchestration/test_rollback_vs_compensation.py -v
```
Expected: 2 passed — an irreversible-change requirement is classified `compensation`; a simple fix is classified `rollback`. [FR-ORC-009]

## 10. How to Demonstrate Safe-Stop
```bash
pytest tests/orchestration/test_safe_stop_on_exhausted_retry.py -v
```
Expected: 2 passed — retries exhausted with no fallback enters `safe_stopped` with a recorded reason. [FR-ORC-010]

## 11. How to Demonstrate Dynamic Replanning
```bash
pytest tests/orchestration/test_dynamic_replanning.py tests/orchestration/test_replanning_governance.py -v
```
Expected: 3 passed — a material design revision suspends downstream work and requires a fresh N8 approval before resuming. [FR-ORC-012, FR-ORC-013]

## 12. Greenfield Scenario
```bash
pytest tests/integration/test_scenario_greenfield.py -v
```
Expected: 1 passed. Live evidence: commit `7237cb8`. [SC-002, User Story 1]

## 13. Brownfield Scenario
```bash
pytest tests/integration/test_scenario_brownfield.py -v
```
Expected: 1 passed. Full evidence: `docs/scenarios/brownfield-impact-analysis.md`. [SC-003, User Story 2]

## 14. Ambiguous-Requirement Scenario
```bash
pytest tests/integration/test_scenario_ambiguous.py -v
```
Expected: 1 passed. Full evidence: `docs/scenarios/ambiguous-requirement-demonstration.md`. [SC-004, User Story 3]

## 15. Architecture
`specs/001-agentic-url-shortener/plan.md` (full plan) and `contracts/orchestration-state-machine.md` (14-node graph, node-by-node). Scoping decisions (including the no-auth decision) are in `spec.md` §Scoping Decisions Confirmed by Human.

## 16. ADRs
`docs/adr/ADR-001..014-*.md` — all `Accepted`, Human Gate 4, 2026-09-24.

## 17. Requirement Traceability
`docs/assessment/convergence-report.md` §"Requirement Traceability Matrix" — every FR/NFR mapped to implementing code and test file.

## 18. Audit Evidence
`docs/scenarios/*.md` (live-captured audit trails) or, for any live run, `GET /v1/workflows/{run_id}/audit`. [FR-ORC-014, NFR-006]

## 19. Reliability Measurements
```bash
pytest tests/unit/test_mttr_calculation.py tests/unit/test_metrics_labeling.py -v
```
Expected: 3 passed. Formula and methodology: `docs/assessment/final-engineering-summary.md` under the reliability section. All figures explicitly labeled `is_demonstration_data=True`. [FR-ORC-020]

## 20. Security Controls
```bash
pytest tests/unit/test_validation.py tests/integration/test_no_auth.py tests/unit/test_dependency_scan_policy.py -v
```
Expected: 15 passed — URL scheme allowlist + SSRF hardening, confirmed no-auth-by-design, and a real `pip-audit` invocation. [NFR-001]

## 21. Known Limitations
`docs/assessment/final-engineering-summary.md` and the project plan's known limitations section.

## 22. Final Engineering Summary
`docs/assessment/final-engineering-summary.md` — the mandatory 21-section schema.

## 23. API Contracts, Schemas, Versions, Compatibility, Examples, and Contract-Test Evidence
`specs/001-agentic-url-shortener/contracts/openapi.yaml` (v1.0.0) and `contracts/schemas/*.json`. One versioned amendment: `audit-event.schema.json` was tightened in commit `bbfb26d` (flagged and approved before editing). Contract tests: `pytest tests/contract/ -v` → 7 files passing. **Scope note**: the HTTP contract covers workflow creation/inspection/audit only; the full N2–N14 pipeline is exercised via direct Python calls in `tests/integration/test_scenario_*.py`, not additional HTTP endpoints — see `quickstart.md` §Implementation Scope Note.

## 24. Compliance/Change-Control Results and Approved Exceptions
```bash
pytest tests/orchestration/test_n12_policy_checks.py tests/orchestration/test_n13_release_readiness.py tests/unit/test_policy_exception_expiry.py -v
```
Expected: 5 passed — 4 mandatory policy checks evaluated per run, FAIL blocks release, expired exceptions revert to FAIL. No exceptions are currently active in this repository (none were needed). [FR-ORC-016, FR-ORC-017, FR-ORC-018]

## 25. MTTR Calculation Inputs, Recovered-Event Population, Exclusions, Unrecovered Failures, and Demonstration-Data Limitations
`src/telemetry/metrics.py::compute_mttr`. Population = events with `recovered=True` and a non-null `recovery_complete_at`; unrecovered events are excluded from the denominator and reported separately. Demonstration-data limitation: with a small number of runs in this repository's test suite, any computed MTTR figure is a demonstration statistic, not a production reliability claim — labeled as such by `is_demonstration_data=True` on every computed metric.
