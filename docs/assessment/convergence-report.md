# Convergence Report

**Generated**: 2026-09-25 · **Feature**: 001-agentic-url-shortener · **Commits covered**: `820f358`..`92ab3d5` (39 commits)

This is the full Prompt 9 (doc §22) convergence pass: verification across requirements, architecture, orchestration, all three scenarios, testing, documentation, and compliance/change-control, followed by the 13 required outputs and one release-readiness decision. The mechanical gap-analysis (`/speckit-converge`) already ran and appended/closed Phase 12 (T118–T120, see `tasks.md` and commits `e132df5`..`92ab3d5`); this report is the broader synthesis the guidance doc calls for.

## Requirements

Every FR-SVC-\*, FR-ORC-\*, and NFR-\* identifier was cross-checked against `src/` and `tests/` (see the traceability matrix below). No incomplete, contradicted, or unverifiable requirement was found as of this commit. No implementation behavior was found that isn't represented in `spec.md` (no "unrequested" gap-type findings from the converge pass).

## Architecture

Implementation matches the approved component boundaries in `plan.md` §Project Structure (`src/domain`, `src/api`, `src/orchestration`, `src/policy`, `src/persistence`, `src/telemetry`, `src/config.py`). No undocumented architectural drift found. All 14 ADRs have `Accepted` status (Human Gate 4) and their Decisions are reflected in the code — the one exception (T118's stdout→stderr deviation from ADR-010's literal wording) is documented in `tasks.md` T118 and this report, not silent. Application-plane (`src/domain`, `src/api/links.py`) and orchestration-plane (`src/orchestration/*`) responsibilities remain separated — the two share only the persistence layer's connection object, by design (ADR-003).

## Orchestration — Executable Evidence

| Capability | Evidence |
|---|---|
| Explicit dependencies | `src/orchestration/graph.py` (14-node DAG) |
| Persisted state | `WorkflowInstance` table, SQLite/WAL |
| Sequential execution | N1→N2→N3→... transitions, every integration test |
| Parallel execution | N9's `ThreadPoolExecutor` fan-out to N10/N11/N12 |
| Synchronization | `run_parallel_validation_and_join`, tested by `test_n9_bulkhead_safe_stop.py` |
| Branching | N3→{N4, N4b, N5} conditional routing |
| Entry/exit gates | N1 (entry), N14 (exit/terminal) |
| Approval | `gates.py::approve_*` functions, `Decision` records |
| Rejection | `gates.py::reject_*` functions, routes to producing node |
| Bounded retry | `retry_with_backoff` (3 attempts, 200ms exponential backoff), now wired into N2, N4b, N6, N7, N9-path, N11 |
| Timeout | 24h gate timeout (`check_gate_timeout`), `FakeClock`-tested |
| Fallback | N9 task-level bulkheading |
| Rollback/compensation | `n4b_impact_analysis.py` classification, ADR-008 |
| Safe-stop | `engine.safe_stop()`, tested on retry exhaustion and gate timeout |
| Resume | `src/orchestration/resume.py`, proven via genuine subprocess kill |
| Dynamic replanning | `src/orchestration/replanning.py`, version-stamped artifacts |
| Decision lineage | `Decision` table, `run_id`-keyed |
| Terminal status | `WorkflowInstance.status` ∈ {completed, safe_stopped} |

Every row above has at least one passing automated test citing it (see traceability matrix).

## Three Scenarios

Covered exhaustively in `docs/scenarios/`:
- `docs/scenarios/brownfield-impact-analysis.md` — full live-execution audit trail.
- `docs/scenarios/ambiguous-requirement-demonstration.md` — full 17-item evidence list, live-execution audit trail.
- `docs/scenarios/scenario-evidence-review.md` — cross-scenario matrix confirming all three are structurally distinct (not relabeled copies) and no scenario passes on documentation alone.

Greenfield's live-execution evidence (26 audit events, zero `clarification_requested`) is captured in the commit history and `test_scenario_greenfield.py`; not separately filed as a standalone doc since Greenfield's evidence is materially identical in form to Brownfield's (same node path minus N4b) and re-filing it would be redundant, not because it's less rigorously verified.

## Testing

**Executed at report time**: `pytest -q` → **94 passed, 0 failed, 0 skipped**, 3.82s.

- Unit: `tests/unit/*.py` (18 files)
- Contract: `tests/contract/*.py` (7 files) — validated against `contracts/openapi.yaml` and `contracts/schemas/*.json`
- Integration: `tests/integration/*.py` (9 files) — includes the 3 scenario tests, load/latency, concurrency, persistence-failure, real subprocess-kill resumption
- Orchestration-transition: `tests/orchestration/*.py` (18 files)
- Security: `test_validation.py` (SSRF/scheme allowlist), `test_no_auth.py`, `test_dependency_scan_policy.py` (real `pip-audit` invocation)
- End-to-end: the three scenario integration tests drive N1→N14 (or N1→N6 for the ambiguous demo, by design) through real function calls against a real SQLite database

**Flaky or order-dependent tests**: none found. The suite was run standalone and as part of the full 94-test run with identical results; tests use `tmp_path`-scoped SQLite files or `:memory:`, avoiding shared state (the one deliberately shared-state test, `test_no_auth.py`/`test_default_expiration.py` etc. using `src.api.app`'s module-level singleton, is intentional and stable — the app module is imported once per test session and its `url_shortener.db` file is cleaned up between manual/live-server runs, not between these unit-level TestClient tests, which don't collide on short-code values due to Base62 randomness).

**Unsupported test claims**: none found — every test asserts on real return values or real persisted state, never on a mocked assertion of "this would have happened."

## Documentation

`quickstart.md` was corrected during Polish (commit `7430749`) to accurately reflect that the HTTP API only wires N1/inspection/audit — this is the one place documentation had drifted from implementation, and it's now fixed rather than left stale. All other documentation (`plan.md`, ADRs, `data-model.md`, `contracts/`) was written after or alongside the corresponding code and cross-checked in this pass — no further drift found.

## Compliance and Change Control

- Every orchestration run records `policy_version` (`POLICY_VERSION = "1.0.0"` in `src/policy/checks.py`) on every `PolicyCheckResult`.
- Mandatory compliance policies (4, after T119) execute automatically in N12 on every run — confirmed by `test_n12_policy_checks.py` and the scenario evidence's `policy_check_evaluated` events.
- Policy failures block progression: `test_release_readiness_fail_on_policy_violation.py` confirms an injected FAIL yields overall FAIL, not silent PASS.
- Exceptions require explicit human approval with rationale/scope/expiry/compensating-control: `data-model.md`'s `PolicyException` fields, enforced by `test_policy_exception_expiry.py`.
- Material changes followed impact analysis: the one in-session contract change (`audit-event.schema.json`'s reason-non-null tightening) was flagged and approved before editing, per commit `bbfb26d`.
- Changed contracts/schemas/tests/documentation were revalidated: the schema change's own test (`test_audit_event_schema.py`) was updated and re-passed in the same commit.

## Evidence Integrity

- No unsupported claims found in this pass (checked above, per section).
- Simulated input is labeled: the brownfield/ambiguous scenario requirement texts are explicitly described as simulated demonstration inputs in their respective docs, not presented as real user submissions.
- Demonstration measurements are labeled: `WorkflowMetrics.is_demonstration_data = True` (always), `NFR-003`/`NFR-007`'s load/latency tests are explicitly scoped as "demonstration-scale... not a claimed production capacity figure" in both `spec.md` and the test files themselves.
- Approvals correspond to actual recorded actions: every `Decision` in every scenario's audit trail was produced by an actual function call in this session, captured live (see `docs/scenarios/*.md`), not authored as prose.
- Repository history presents a truthful engineering journey: 3 real bugs (route-shadowing, SQLite thread-safety, schema validation gap) are documented in their fixing commits as bugs found by failing tests, not retroactively described as intentional; one process deviation (T012/T013 collision-retry written ahead of its test) is disclosed rather than concealed; the T118 stdout→stderr regression is disclosed in its own commit message.

---

## Required Outputs

### 1. Requirement Traceability Matrix

| Requirement Group | Implementing Code | Test Evidence |
|---|---|---|
| FR-SVC-001..003 (creation, uniqueness) | `src/domain/short_link.py`, `src/api/links.py` | `test_short_link*.py`, `test_links_create.py` |
| FR-SVC-004..005 (redirect, expiry) | `src/api/links.py` | `test_redirect.py` |
| FR-SVC-006 (default expiration) | `src/domain/short_link.py::compute_default_expiration` | `test_default_expiration.py` |
| FR-SVC-007 (analytics) | `src/persistence/short_links.py::get_analytics` | `test_analytics_aggregation.py` |
| FR-SVC-008 (idempotency) | `src/api/links.py` | `test_idempotency.py` |
| FR-SVC-009 (concurrency) | `ShortLinkRepository` shared lock | `test_concurrency.py` |
| FR-SVC-010 (persistence failure) | `src/api/links.py` `sqlite3.Error` handling | `test_persistence_failure.py` |
| FR-SVC-011 (health) | `src/api/app.py::get_health` | `test_health.py` |
| FR-SVC-012 / D-001 (no auth) | absence by design, `app.py` docstring | `test_no_auth.py` |
| FR-ORC-001..002 (workflow create/inspect) | `n1_ingestion.py`, `src/api/workflows.py` | `test_n1_ingestion.py`, `test_workflows_*.py` |
| FR-ORC-003..004 (quality checks, routing) | `n3_classification.py` | `test_n3_*.py` |
| FR-ORC-005..006 (approval, no-silence) | `gates.py` | `test_n5_requirements_gate.py`, `test_gate_rejection.py` |
| FR-ORC-007..008 (retry, fallback) | `engine.py::retry_with_backoff`, N9 bulkheading | `test_retry_policy*.py`, `test_n9_bulkhead_safe_stop.py` |
| FR-ORC-009 (rollback/compensation) | `n4b_impact_analysis.py` | `test_rollback_vs_compensation.py` |
| FR-ORC-010 (safe-stop) | `engine.py::safe_stop` | `test_safe_stop_on_exhausted_retry.py`, gate-timeout tests |
| FR-ORC-011 (resumption) | `src/orchestration/resume.py` | `test_resumption_process_restart.py` (real subprocess kill) |
| FR-ORC-012..013 (replanning, governance) | `src/orchestration/replanning.py` | `test_dynamic_replanning.py`, `test_replanning_governance.py` |
| FR-ORC-014 (audit) | `AuditEventRepository`, `engine.py::emit` | `test_audit_event_schema.py`, `test_audit_query.py` |
| FR-ORC-015 (parallel/sync) | `n9_implementation.py::run_parallel_validation_and_join` | `test_scenario_greenfield.py` |
| FR-ORC-016..018 (policy, exceptions) | `src/policy/checks.py`, `n12_security.py`, `n13_release_readiness.py` | `test_n12_policy_checks.py`, `test_n13_release_readiness.py`, `test_policy_exception_expiry.py` |
| FR-ORC-019 (final summary) | `n14_summary.py` | asserted in all 3 scenario integration tests |
| FR-ORC-020 (demonstration labeling) | `src/telemetry/metrics.py` | `test_metrics_labeling.py` |
| NFR-001 (security) | `src/domain/validation.py` | `test_validation.py` |
| NFR-002 (failure classification) | `engine.py::classify_and_execute` | `test_permanent_failure_routing.py` |
| NFR-003/007 (throughput/latency, PVT-002/003) | N/A (measured, not implemented) | `test_load_throughput.py`, `test_latency.py` |
| NFR-004 (maintainability) | module structure itself | N/A (structural, not unit-testable) |
| NFR-005 (observability) | `src/telemetry/logging.py` (T118) | `test_logging.py`, `test_engine_logging_integration.py` |
| NFR-006 (append-only audit) | `AuditEventRepository` (no update/delete method) | `test_audit_append_only.py` |
| NFR-008 (recoverability) | `resume.py` | `test_resumption_process_restart.py` |
| NFR-009 (testability) | this matrix itself | — |
| NFR-010 (change safety) | N4b, `replanning.py` | `test_n4b_impact_analysis.py`, `test_dynamic_replanning.py` |
| NFR-011 (controlled autonomy) | `engine.py::require_prior_approval` | `test_controlled_autonomy.py` |

### 2. Final Checklist Status

- `checklists/requirements.md`: 16/16 checked (spec-quality, closed at specify/clarify time).
- `checklists/design-consistency.md`: 32 items, reviewer-owned, not yet marked — my assessment: all 32 are now satisfiable given final implementation state (no CHK item's underlying concern remains open); final marking is the human reviewer's call, not mine to make on your behalf.
- `checklists/assessment-readiness.md`: 45 items, reviewer-owned, same status — every named failure-trap category has corresponding evidence in this report or `docs/scenarios/`.

### 3. Test and Validation Summary

94/94 passing, 0 failed, 0 skipped, 3.82s wall time, executed at report time (not a historical claim). See "Testing" section above for category breakdown.

### 4. Security Summary

URL-scheme allowlist + SSRF-adjacent loopback/private-address rejection (`NFR-001`); no authentication anywhere in v1, disclosed as an intentional scope decision (D-001, ADR-013); real `pip-audit` scan wired into every N12 evaluation as of T119 (previously manual/ad hoc — closed gap); append-only audit trail (NFR-006) prevents post-hoc evidence tampering. No rate limiting (EXC-006, disclosed limitation, not a defect).

### 5. Reliability Summary

Bounded retry (3 attempts, 200ms exponential backoff) now applied uniformly across N2, N4b, N6, N7, N9-path, N11 (closed T120 gap — previously N6/N7/N11 had none). SAFE_STOP on retry exhaustion or gate timeout, never silent. Resumption proven via genuine OS process kill, not simulation. N9 bulkheading confirmed: one failing parallel branch doesn't block the others.

### 6. Risk Register

| Risk | Severity | Disclosure |
|---|---|---|
| HTTP API doesn't wire full N2–N14 pipeline | Medium | `quickstart.md`, this report |
| Brownfield demo uses same-session code, not real legacy | Low | `plan.md` §Known Limitations |
| Greenfield auto-qualified approval could become rubber-stamp in careless use | Low | `plan.md` §Known Limitations |
| Single-writer SQLite ceiling under heavy concurrent load | Low | ADR-003 |
| No rate limiting | Low | EXC-006 |

### 7. Known Limitations

See `plan.md` §Known Limitations (4 items) plus the HTTP-pipeline-scope item disclosed in `quickstart.md` and reiterated in the risk register above.

### 8. Residual Risks

None rated above Medium. The HTTP-pipeline-scope item is the only Medium-severity residual risk and is fully disclosed, not hidden.

### 9. Assumption Status

AS-001..005 (spec.md) all confirmed/closed via the clarification session (2026-09-24) and PVT-001..004 approval round. No open assumptions remain except the intentionally-deferred AMB-006 sub-detail (analytics retention duration exact value), itself resolved to "indefinite, same as audit retention" per the same clarification round.

### 10. Scenario Evidence Index

- `docs/scenarios/brownfield-impact-analysis.md`
- `docs/scenarios/ambiguous-requirement-demonstration.md`
- `docs/scenarios/scenario-evidence-review.md`
- Greenfield: `tests/integration/test_scenario_greenfield.py` + commit `7237cb8`

### 11. Reviewer Navigation Guide

Not yet produced as a standalone document — this is doc §26, the next step after this convergence report and the Final Independent Assessment.

### 12. Final Engineering Summary

Not yet produced — this is doc §25's mandatory 21-section document, scheduled after the Final Independent Assessment (doc §23), per the doc's own sequencing (§23 runs "only after convergence"; §25 runs "only after convergence, final independent assessment, and resolution... of mandatory findings").

### 13. Release-Readiness Decision

## **READY WITH ACCEPTED LIMITATIONS**

Rationale: every mandatory requirement, all three required scenarios, and all governance/reliability/compliance mechanisms have real, executed evidence — not narrative claims. Three genuine implementation gaps were found by this convergence pass and closed in the same session (T118–T120), each with its own test-first evidence. No CRITICAL or unresolved HIGH finding remains. The disclosed limitations (HTTP pipeline scope, demo-authenticity, rubber-stamp risk, SQLite ceiling, no rate limiting) are all judged acceptable for a 2–3 day assessment prototype and are documented, not concealed — which is precisely why this is `READY WITH ACCEPTED LIMITATIONS` rather than an unqualified `READY`: an unqualified READY would imply no limitations exist, which would itself be a false claim.
