---
description: "Task list for Agentic Software Engineering System: URL Shortener"
---

# Tasks: Agentic Software Engineering System: URL Shortener

**Input**: Design documents from `/specs/001-agentic-url-shortener/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md, docs/adr/ (all present and accepted)

**Revision note (2026-09-24, rev. 2)**: This revision incorporates the `/speckit-analyze` pre-implementation findings (F1–F7), the human's batch approval of PVT-001..004 and AMB-006, and the Section 14 Independent Reviewer Gate's required corrections. Key structural change (F1): the shared bounded-retry utility and SAFE_STOP cross-cutting state — originally scheduled in the US7 phase — are moved into the Foundational phase, since ADR-007's "shared default policy applied to every node" design means multiple earlier user stories (US1, US3) implicitly depend on this infrastructure existing first. Reviewer-gate correction: an injectable time/clock abstraction (T038) is added to Foundational, since 24-hour gate timeouts and retry backoff must be testable without real-time waiting; the resumption test (T105) is strengthened to require an actual process kill/restart rather than an in-process simulation, with an explicit fallback-and-disclose path if that proves infeasible. All task IDs below are renumbered sequentially; prior revisions' task IDs no longer apply.

**Tests**: Included — Constitution Principle IV mandates red-green-refactor TDD; every implementation task is paired with a preceding failing-test task.

**Organization**: Primary organization is by user story (per spec.md), in priority order (P1: US1–US4; P2: US5–US7; P3: US8–US9), preceded by Setup and Foundational phases. Each phase is cross-referenced to its corresponding slice in `plan.md`'s Delivery Sequence.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: Which user story this task belongs to (US1–US9); omitted for Setup/Foundational/Polish tasks
- Every task cites the requirement identifier(s) it satisfies in `[...]` at the end
- Every implementation task is preceded by its failing-test task; a task is not complete until its paired test executes and passes (Constitution Principle XI)

## Path Conventions

Single project per `plan.md` Project Structure: `src/`, `tests/` at repository root.

---

## Phase 1: Setup — *(plan.md Delivery Sequence slice 1: Engineering baseline)*

- [x] T001 Create the module skeleton per `plan.md` Project Structure: `src/domain/`, `src/api/`, `src/orchestration/`, `src/orchestration/nodes/`, `src/policy/`, `src/persistence/`, `src/telemetry/`, `src/config.py`, `tests/contract/`, `tests/integration/`, `tests/orchestration/`, `tests/unit/` [Plan §Project Structure]
- [x] T002 [P] Initialize `pyproject.toml`: Python 3.12, FastAPI, Uvicorn, Pydantic, pytest, pytest-asyncio, httpx, jsonschema per `research.md` Decisions 1, 2, 5 and ADR-002/ADR-011 [ADR-002, ADR-011]
- [x] T003 [P] Configure pytest test discovery across `tests/contract/`, `tests/integration/`, `tests/orchestration/`, `tests/unit/` per `plan.md` Testing Plan [NFR-009]

**Checkpoint**: Repository builds; `pytest` runs (zero tests, zero failures).

---

## Phase 2: Foundational (Blocking Prerequisites) — *(plan.md Delivery Sequence slices 2–4: Walking skeleton, Core URL behavior, Orchestration state model)*

**⚠️ CRITICAL**: No user story can be implemented until this phase is complete. This phase now also contains the shared retry/safe-stop/failure-classification infrastructure (moved here per `/speckit-analyze` finding F1), since ADR-007 specifies these as a shared mechanism every node uses, not a US7-specific feature.

### Walking Skeleton

- [x] T004 Implement `src/config.py`: environment-variable configuration, fail-fast on malformed config, per `research.md` Decision 7 [Constitution Principle V, ADR-002]
- [x] T005 Implement `src/persistence/db.py`: SQLite connection management in WAL mode per ADR-003 [D-003, CON-002, ADR-003]
- [x] T006 [P] Contract test: `GET /healthz` in `tests/contract/test_health.py` against `contracts/openapi.yaml` `HealthStatus` schema — write failing first [FR-SVC-011]
- [x] T007 Implement `GET /healthz` in `src/api/app.py` (depends on T004, T005, T006) [FR-SVC-011]

### Core URL Behavior

- [x] T008 [P] Unit test: short-code format `^[0-9a-zA-Z]{7}$` in `tests/unit/test_short_link.py` — write failing first [FR-SVC-001, FR-SVC-003, ADR-004]
- [x] T009 Implement Base62 7-char short-code generation in `src/domain/short_link.py` per ADR-004 (depends on T008)
- [x] T010 [P] Unit test: URL validation rejects `javascript:`/`data:`/malformed URLs, accepts `http`/`https` only, in `tests/unit/test_validation.py` — write failing first [FR-SVC-002, NFR-001]
- [x] T011 Implement `src/domain/validation.py`: scheme allowlist + loopback/private-address rejection per `plan.md` §Security (depends on T010)
- [x] T012 [P] Unit test: seeded collision forces retry-then-success, no caller-visible error, in `tests/unit/test_short_link_collision.py` — write failing first [FR-SVC-003, ADR-004]
- [x] T013 Implement bounded collision-retry (max 3 attempts) in `src/domain/short_link.py` (depends on T009, T012)
- [x] T014 Implement `src/persistence/short_links.py` repository for `ShortLink`: `short_code` (PK, unique among `status='active'` rows), `target_url` (required, no uniqueness constraint), `created_at`, `expires_at` (nullable), `status` (enum active/expired/deleted), `idempotency_key` (nullable, unique when present) — exact constraints per `data-model.md` (depends on T005)
- [x] T015 [P] Contract test: `POST /v1/links` in `tests/contract/test_links_create.py` (201+schema on valid, 400 `INVALID_URL` on disallowed scheme) — write failing first [FR-SVC-001, FR-SVC-002]
- [x] T016 Implement `POST /v1/links` in `src/api/links.py`, always minting a new code (no de-duplication, per Clarifications 2026-09-24) (depends on T011, T013, T014, T015) [FR-SVC-001, FR-SVC-002]
- [x] T017 [P] Unit test: when `expires_at` is omitted, the confirmed default of 90 days from creation is applied, in `tests/unit/test_default_expiration.py` — write failing first [FR-SVC-006, PVT-001 (confirmed 2026-09-24)]
- [x] T018 Implement default-expiration application in `src/domain/short_link.py` + `src/api/links.py` (depends on T016, T017) [FR-SVC-006]
- [x] T019 [P] Unit test: identical `Idempotency-Key` on two creation requests returns the identical `short_code`, in `tests/unit/test_idempotency.py` — write failing first [FR-SVC-008]
- [x] T020 Implement `Idempotency-Key` handling in `src/api/links.py` + `src/persistence/short_links.py` (depends on T018, T019)
- [x] T021 [P] Contract test: `GET /{short_code}` in `tests/contract/test_redirect.py` (302 active / 404 unknown / 410 expired) — write failing first [FR-SVC-004, FR-SVC-005]
- [x] T022 Implement `GET /{short_code}` redirect in `src/api/links.py` (depends on T014, T021)
- [x] T023 Implement append-only `RedirectEvent` insert per redirect resolution per ADR-014 (depends on T022) [FR-SVC-007, ADR-014, data-model.md RedirectEvent]
- [x] T024 [P] Unit test: `redirect_count`/`last_accessed_at` aggregation correctness in `tests/unit/test_analytics_aggregation.py` — write failing first [FR-SVC-007, ADR-014]
- [x] T025 Implement `GET /v1/links/{short_code}` detail endpoint with aggregated analytics (depends on T023, T024) [FR-SVC-007]
- [x] T026 [P] Integration test: concurrent creation/redirect requests produce no duplicate active codes, no lost-update analytics counts, in `tests/integration/test_concurrency.py` — write failing first [FR-SVC-009, SC-010]
- [x] T027 Adjust `src/persistence/short_links.py` transaction boundaries so T026 passes under SQLite WAL mode (depends on T014, T026) [FR-SVC-009]
- [x] T028 [P] Integration test: simulated persistence unavailability returns 503 `STORE_UNAVAILABLE`, no internal detail leaked, in `tests/integration/test_persistence_failure.py` — write failing first [FR-SVC-010]
- [x] T029 Implement persistence-failure handling in `src/api/links.py` + `src/persistence/db.py` (depends on T005, T028) [FR-SVC-010]
- [x] T030 [P] Integration test *(closes analyze finding F5)*: `POST /v1/links`, `GET /{short_code}`, `GET /v1/links/{short_code}` all respond with no `Authorization` header present, in `tests/integration/test_no_auth.py` — write failing first [D-001, FR-SVC-012, ADR-013]
- [x] T031 Confirm and lock in that no authentication middleware is registered on any route in `src/api/app.py`; add a comment referencing D-001/ADR-013 so this isn't accidentally "fixed" later (depends on T007, T016, T022, T025, T030) [D-001, ADR-013]

### Orchestration Scaffolding

- [x] T032 Implement `src/persistence/orchestration_store.py` repositories for `WorkflowInstance`, `Decision`, `AuditEvent`, `PolicyCheckResult`, `PolicyException` per `data-model.md` exact fields/constraints (depends on T005) [data-model.md, ADR-003]
- [x] T033 [P] Unit test: `AuditEvent` validates against `contracts/schemas/audit-event.schema.json`, including "reason required when result=failure", in `tests/contract/test_audit_event_schema.py` — write failing first [FR-ORC-014]
- [x] T034 Implement `src/orchestration/graph.py`: declare the 14-node DAG (N1–N14) and edges exactly per `contracts/orchestration-state-machine.md` (depends on T033) [FR-ORC-001, CON-003, ADR-005]
- [x] T035 Implement `src/orchestration/engine.py`: async executor base (sequential edge traversal, `AuditEvent` emission per transition) (depends on T032, T034) [FR-ORC-014, ADR-005]
- [x] T036 [P] Unit test *(closes analyze finding F2)*: the `AuditEvent` repository and API expose no update/delete operation (append-only invariant), in `tests/unit/test_audit_append_only.py` — write failing first [NFR-006, ADR-010]
- [x] T037 Implement `AuditEvent` repository in `src/persistence/orchestration_store.py` with no update/delete method exposed (depends on T032, T036) [NFR-006]
- [x] T038 Implement an injectable time/clock abstraction (`src/orchestration/clock.py`) used by every gate-timeout and retry-backoff computation, with a test double that can fast-forward simulated time — required so 24-hour gate timeouts (ADR-006) and retry backoff (ADR-007) are testable without real-time waiting; identified as a required correction in the Section 14 Independent Reviewer Gate (2026-09-24) rather than left implicit (depends on T035) [ADR-006, ADR-007]
- [x] T039 [P] Unit test *(F1: relocated from the former US7 phase)*: bounded retry (3 attempts, 200ms exponential backoff) on transient failure, using the T038 clock abstraction to assert backoff timing without real delays, in `tests/orchestration/test_retry_policy.py` — write failing first [FR-ORC-007, PVT-004 (confirmed 2026-09-24), ADR-007]
- [x] T040 Implement the shared bounded-retry utility in `src/orchestration/engine.py` per ADR-007, using T038's clock (depends on T035, T038, T039) [FR-ORC-007]
- [x] T041 [P] Unit test *(F1: relocated)*: SAFE_STOP entered with reason recorded when retries are exhausted and no fallback is defined, in `tests/orchestration/test_safe_stop_on_exhausted_retry.py` — write failing first [FR-ORC-010]
- [x] T042 Implement the SAFE_STOP cross-cutting state in `src/orchestration/engine.py` (depends on T040, T041) [FR-ORC-010]
- [x] T043 [P] Unit test *(F1: relocated)*: permanent-failure classification routes directly to fallback/safe-stop without any retry attempt, in `tests/orchestration/test_permanent_failure_routing.py` — write failing first
- [x] T044 Implement transient/permanent failure-classification dispatch per node in `src/orchestration/engine.py` (depends on T042, T043) [NFR-002]
- [x] T045 [P] Unit test *(closes analyze finding F3)*: a node capable of an irreversible action cannot transition without a preceding `Decision` of type `approval`/`exception_approval`, in `tests/orchestration/test_controlled_autonomy.py` — write failing first [NFR-011]
- [x] T046 Implement the irreversible-action guard in `src/orchestration/gates.py` + `src/orchestration/engine.py` (depends on T044, T045) [NFR-011]
- [x] T047 [P] Unit test: N1 creates `WorkflowInstance`+`Requirement` with a stable `run_id`/`requirement_id`; empty input rejected without creating a `WorkflowInstance`, in `tests/orchestration/test_n1_ingestion.py` — write failing first [FR-ORC-001]
- [x] T048 Implement N1 in `src/orchestration/nodes/n1_ingestion.py` (depends on T035, T047)
- [x] T049 [P] Contract test: `POST /v1/workflows` returns `run_id` per `contracts/schemas/workflow-state.schema.json`, in `tests/contract/test_workflows_create.py` — write failing first [FR-ORC-001]
- [x] T050 [P] Contract test *(closes analyze finding F7)*: `GET /v1/workflows/{run_id}` returns current stage/status per the same schema, in `tests/contract/test_workflows_get.py` — write failing first [FR-ORC-002]
- [x] T051 Implement `POST /v1/workflows` and `GET /v1/workflows/{run_id}` in `src/api/workflows.py` (depends on T048, T049, T050) [FR-ORC-001, FR-ORC-002]

**Checkpoint**: Foundation ready — full URL-shortener domain (FR-SVC-001..012) complete and tested; orchestration engine can ingest a requirement, apply shared retry/safe-stop/failure-classification, and report state. User story implementation can now begin.

---

## Phase 3: User Story 1 — Greenfield Requirement Flows Straight Through Governed Orchestration (Priority: P1) 🎯 MVP
*(plan.md Delivery Sequence slices 4/8)*

**Goal**: A well-specified requirement proceeds through decomposition→design→implementation→testing→documentation→validation without an artificial clarification gate, while still passing the requirements and architecture approval gates.

**Independent Test**: Submit a complete, unambiguous requirement via `POST /v1/workflows`; verify via the audit endpoint that no `clarification_requested` event occurs and the run reaches `completed`.

### Tests for User Story 1

- [x] T052 [P] [US1] Unit test: N2 produces `normalized_description`, reusing the shared retry utility (T040) on transient failure, in `tests/orchestration/test_n2_normalization.py` — write failing first
- [x] T053 [P] [US1] Unit test: N3 classifies a complete/consistent/testable/in-policy requirement as `greenfield` and does NOT trigger N4, in `tests/orchestration/test_n3_classification.py` — write failing first [FR-ORC-003, FR-ORC-004, User Story 1 acceptance scenario 1]
- [x] T054 [P] [US1] Unit test: N5 auto-populates an "auto-qualified" rationale for greenfield but still requires an explicit recorded approval; 24h timeout (reusing T042's SAFE_STOP) if no response, in `tests/orchestration/test_n5_requirements_gate.py` — write failing first [FR-ORC-005, FR-ORC-006, ADR-006]
- [x] T055 [P] [US1] Integration test: full path N1→N2→N3→N5→N6→N7→N8→N9→(N10‖N11‖N12)→N13→N14 produces NO `clarification_requested` event and reaches `completed`, per `quickstart.md` Scenario 2, in `tests/integration/test_scenario_greenfield.py` — write failing first [SC-002]

### Implementation for User Story 1

- [x] T056 [US1] Implement N2 in `src/orchestration/nodes/n2_normalization.py`, calling the shared retry utility from T040 (depends on T040, T052)
- [x] T057 [US1] Implement N3 quality checks + classification in `src/orchestration/nodes/n3_classification.py` (depends on T056, T053)
- [x] T058 [US1] Implement N5 in `src/orchestration/gates.py`, calling T042's SAFE_STOP on timeout using T038's clock abstraction for the 24h window, including the auto-qualified rationale path (depends on T038, T042, T057, T054)
- [x] T059 [US1] Implement N6 in `src/orchestration/nodes/n6_decomposition.py` (depends on T058)
- [x] T060 [US1] Implement N7 (parallel-branch-capable, synchronization join) in `src/orchestration/nodes/n7_design.py` (depends on T059)
- [x] T061 [US1] Implement N8 in `src/orchestration/gates.py`, reusing T058's gate/timeout mechanism (depends on T060)
- [x] T062 [US1] Implement N9 with genuine parallel task fan-out + synchronization join in `src/orchestration/nodes/n9_implementation.py` + concurrency support in `src/orchestration/engine.py` (depends on T061) [FR-ORC-015]
- [x] T063 [US1] Implement N10, N11, N12 (parallel, joined) and N13/N14 (base pass-through; full N13 gate built in US5) in `src/orchestration/nodes/n10_testing.py`, `n11_documentation.py`, `n12_security.py`, `n13_release_readiness.py`, `n14_summary.py` (depends on T062) [FR-ORC-019]
- [x] T064 [US1] Run T055 integration test to green; adjust N1–N14 wiring as needed (depends on T063, T055)

**Checkpoint**: User Story 1 fully functional and independently testable — this is the MVP.

---

## Phase 4: User Story 2 — Brownfield Change Requires Pre-Change Impact Analysis (Priority: P1)
*(plan.md Delivery Sequence slices 4/8)*

**Goal**: A brownfield change produces a complete, human-approved impact-analysis artifact before any implementation task starts.

**Independent Test**: Submit a defect-correction request; verify implementation doesn't begin until the impact-analysis artifact is approved and contains all required categories.

### Tests for User Story 2

- [x] T065 [P] [US2] Unit test: N3 routes `brownfield` classification to N4b before N5, in `tests/orchestration/test_n3_brownfield_routing.py` — write failing first
- [x] T066 [P] [US2] Unit test: N4b's artifact contains impacted components/interfaces/data flows/tests/documentation/regression risks/rollout-rollback considerations — none omitted, in `tests/orchestration/test_n4b_impact_analysis.py` — write failing first
- [x] T067 [P] [US2] Unit test: N5 (brownfield path) presents the N4b artifact and blocks on unapproved/timeout, in `tests/orchestration/test_n5_brownfield_review.py` — write failing first
- [x] T068 [P] [US2] Unit test: an irreversible-consequence change is classified as requiring compensation, surfaced distinctly, per ADR-008, in `tests/orchestration/test_rollback_vs_compensation.py` — write failing first [ADR-008]
- [x] T069 [P] [US2] Integration test: full brownfield path per `quickstart.md` Scenario 4, in `tests/integration/test_scenario_brownfield.py` — write failing first [SC-003]

### Implementation for User Story 2

- [x] T070 [US2] Extend N3 in `src/orchestration/nodes/n3_classification.py` with brownfield routing (depends on T057, T065)
- [x] T071 [US2] Implement N4b in `src/orchestration/nodes/n4b_impact_analysis.py`, including rollback-vs-compensation classification per ADR-008 (depends on T070, T066, T068)
- [x] T072 [US2] Extend N5 in `src/orchestration/gates.py` to review the N4b artifact (depends on T058, T071, T067)
- [x] T073 [US2] Run T069 integration test to green (depends on T072, T069)

**Checkpoint**: User Stories 1 and 2 both independently functional.

---

## Phase 5: User Story 3 — Ambiguous or Conflicting Requirement Blocks Unsafe Implementation (Priority: P1)
*(plan.md Delivery Sequence slices 4/8)*

**Goal**: An incomplete/contradictory requirement halts before decomposition, requests structured clarification, and resumes correctly.

**Independent Test**: Submit an incomplete requirement; verify it enters `clarification_pending` and does not reach N6 before a clarification decision is recorded.

### Tests for User Story 3

- [x] T074 [P] [US3] Unit test: N3 classifies an incomplete/contradictory requirement as `ambiguous`, in `tests/orchestration/test_n3_ambiguous_classification.py` — write failing first
- [x] T075 [P] [US3] Unit test: N4 produces a structured clarification request; 24h timeout (reusing T042) → SAFE_STOP with `reason=clarification_gate_timeout`, never auto-answered, in `tests/orchestration/test_n4_clarification.py` — write failing first
- [x] T076 [P] [US3] Unit test: after an accepted answer, the workflow resumes at N2 (not from zero); only the affected path was suspended, in `tests/orchestration/test_n4_resume.py` — write failing first
- [x] T077 [P] [US3] Integration test: full ambiguous-requirement path per `quickstart.md` Scenario 3, in `tests/integration/test_scenario_ambiguous.py` — write failing first [SC-004]

### Implementation for User Story 3

- [x] T078 [US3] Extend N3 with ambiguity-detection quality checks in `src/orchestration/nodes/n3_classification.py` (depends on T070, T074)
- [x] T079 [US3] Implement N4 in `src/orchestration/nodes/n4_clarification.py`, reusing T042's SAFE_STOP and T038's clock for the 24h timeout (depends on T038, T078, T075)
- [x] T080 [US3] Implement clarification-answer resume logic in `src/orchestration/nodes/n4_clarification.py` + `src/orchestration/engine.py` (depends on T079, T076)
- [x] T081 [US3] Run T077 integration test to green (depends on T080, T077)

**Checkpoint**: All three required scenarios (Greenfield/Brownfield/Ambiguous — User Stories 1–3) independently functional. Satisfies `plan.md` Delivery Sequence slice 8's core requirement.

---

## Phase 6: User Story 4 — Human Reviewer Inspects and Approves at Mandatory Gates (Priority: P1)
*(plan.md Delivery Sequence slice 5: Approval governance)*

**Goal**: Explicit approve/reject at every mandatory gate; no silent auto-advance; no undefined rejection state.

**Independent Test**: Drive a workflow to a gate; verify it blocks; approve on one run and verify progression; reject on another and verify return to the producing node.

### Tests for User Story 4

- [x] T082 [P] [US4] Unit test: rejecting N5 routes back to N3/N4b, rejecting N8 routes back to N7, each with rejection rationale attached, in `tests/orchestration/test_gate_rejection.py` — write failing first
- [x] T083 [P] [US4] Unit test: an approval `Decision` records `actor_role_capacity`, timestamp, conditions, in `tests/orchestration/test_decision_recording.py` — write failing first

### Implementation for User Story 4

- [x] T084 [US4] Implement rejection-handling routing in `src/orchestration/gates.py` (depends on T058, T061, T082)
- [x] T085 [US4] Implement `Decision` persistence with `actor_role_capacity` in `src/persistence/orchestration_store.py` + `src/orchestration/gates.py` (depends on T032, T083)

**Checkpoint**: All P1 user stories (US1–US4) complete.

---

## Phase 7: User Story 5 — Release Owner Obtains a Release-Readiness Decision (Priority: P2)
*(plan.md Delivery Sequence slice 9: Release readiness)*

**Goal**: Aggregate policy checks into an overall PASS/FAIL outcome; FAIL blocks release and is never silently treated as PASS.

### Tests for User Story 5

- [x] T086 [P] [US5] Unit test: N12 evaluation conforms to `contracts/schemas/policy-evaluation.schema.json`, in `tests/orchestration/test_n12_policy_checks.py` — write failing first [FR-ORC-016]
- [x] T087 [P] [US5] Unit test: N13 aggregation yields overall FAIL when any mandatory check is FAIL with no approved, non-expired exception, in `tests/orchestration/test_n13_release_readiness.py` — write failing first [FR-ORC-017]
- [x] T088 [P] [US5] Unit test: a `PolicyCheckResult` referencing an expired `PolicyException` reverts to FAIL, in `tests/unit/test_policy_exception_expiry.py` — write failing first [FR-ORC-018]
- [x] T089 [P] [US5] Integration test: release-readiness FAIL per `quickstart.md` Scenario 6, in `tests/orchestration/test_release_readiness_fail_on_policy_violation.py` — write failing first [SC-006]

### Implementation for User Story 5

- [x] T090 [US5] Implement N12 in `src/policy/checks.py` + `src/orchestration/nodes/n12_security.py` (depends on T063, T086)
- [x] T091 [US5] Implement N13 aggregation + human release-readiness gate in `src/orchestration/nodes/n13_release_readiness.py`, using T038's clock for its 24h timeout (depends on T038, T090, T087)
- [x] T092 [US5] Implement `PolicyException` expiry enforcement in `src/persistence/orchestration_store.py` + `src/policy/checks.py` (depends on T091, T088)
- [x] T093 [US5] Run T089 integration test to green (depends on T092, T089)

---

## Phase 8: User Story 6 — Assessment Reviewer Reconstructs Any Execution from Evidence (Priority: P2)
*(plan.md Delivery Sequence slice 7: Observability)*

### Tests for User Story 6

- [x] T094 [P] [US6] Unit test: `GET /v1/workflows/{run_id}/audit` returns every event with actor_type/action/timestamp/result/reason, in `tests/contract/test_audit_query.py` — write failing first [FR-ORC-014]
- [x] T095 [P] [US6] Unit test: computed metrics carry an `is_demonstration_data` marker, in `tests/unit/test_metrics_labeling.py` — write failing first [FR-ORC-020]
- [x] T096 [P] [US6] Unit test: MTTR calculation excludes `recovered: false` events from its denominator, reports unrecovered count separately, in `tests/unit/test_mttr_calculation.py` — write failing first
- [x] T097 [P] [US6] Integration test: full audit reconstruction per `quickstart.md` Scenario 7, in `tests/integration/test_audit_reconstruction.py` — write failing first [SC-008]

### Implementation for User Story 6

- [x] T098 [US6] Implement `GET /v1/workflows/{run_id}/audit` in `src/api/workflows.py` (depends on T032, T094)
- [x] T099 [US6] Implement metrics computation in `src/telemetry/metrics.py` per `plan.md` §Observability and Metrics (depends on T098, T095, T096)
- [x] T100 [US6] Run T097 integration test to green (depends on T099, T097)

---

## Phase 9: User Story 7 — Retry, Fallback, and Safe-Stop Under Transient Failure (Priority: P2)
*(plan.md Delivery Sequence slice 6. Note: the core retry/safe-stop/classification mechanism was relocated to Foundational per finding F1 — this phase now validates that mechanism's correctness across multiple node types plus N9's task-level bulkheading, which is node-specific and was not fully covered by the generic Foundational tests.)*

### Tests for User Story 7

- [x] T101 [P] [US7] Integration test: retry/backoff is observed end-to-end across at least two distinct node types (e.g., N2 and N6) reusing the shared T040 utility, in `tests/orchestration/test_retry_policy_cross_node.py` — write failing first [FR-ORC-007]
- [x] T102 [P] [US7] Integration test *(closes analyze finding F6 for N9)*: an N9 task-level failure triggers bulkheading — unrelated parallel tasks are unaffected — and SAFE_STOP is scoped to only the failing task, in `tests/orchestration/test_n9_bulkhead_safe_stop.py` — write failing first [User Story 7 acceptance scenario 2]

### Implementation for User Story 7

- [x] T103 [US7] Adjust N9 in `src/orchestration/nodes/n9_implementation.py` for task-level bulkheaded fallback per `contracts/orchestration-state-machine.md` (depends on T062, T102)
- [x] T104 [US7] Run T101 to green, confirming cross-node reuse of the T040/T042/T044 Foundational mechanism (depends on T040, T042, T044, T101)

---

## Phase 10: User Story 8 — Recoverable Interruption and Resumption (Priority: P3)
*(plan.md Delivery Sequence slice 6)*

### Tests for User Story 8

- [x] T105 [P] [US8] Integration test *(strengthened per Section 14 Independent Reviewer Gate, 2026-09-24)*: resumption is proven via an actual OS-level process kill and restart of the orchestration process (not an in-process function call simulating one), asserting it resumes from persisted `WorkflowInstance.current_stage` without re-executing completed side-effecting steps, in `tests/integration/test_resumption_process_restart.py` — write failing first. If a genuine process-kill test proves infeasible within the timebox, this task must be re-scoped to an explicitly-labeled in-process simulation, with that limitation disclosed in `plan.md` §Known Limitations rather than left implicit. [FR-ORC-011]
- [x] T106 [P] [US8] Unit test: interruption and resumption both appear as audit events, in `tests/orchestration/test_resumption_audit.py` — write failing first

### Implementation for User Story 8

- [x] T107 [US8] Implement resumption-on-startup logic in `src/orchestration/engine.py` (depends on T032, T105)
- [x] T108 [US8] Implement `workflow_interrupted`/`workflow_resumed` audit events (depends on T107, T106)

---

## Phase 11: User Story 9 — Dynamic Replanning on Upstream Change (Priority: P3)
*(plan.md Delivery Sequence slice 6)*

### Tests for User Story 9

- [x] T109 [P] [US9] Unit test: a material revision to an approved N7 artifact triggers dependency-staleness detection and suspends dependent N9 work, in `tests/orchestration/test_dynamic_replanning.py` — write failing first [FR-ORC-012]
- [x] T110 [P] [US9] Unit test: replanned work re-enters N8 before resuming N9 — no bypass, in `tests/orchestration/test_replanning_governance.py` — write failing first [FR-ORC-013]

### Implementation for User Story 9

- [x] T111 [US9] Implement `src/orchestration/replanning.py` with version-stamped artifacts per ADR-009 (depends on T060, T109)
- [x] T112 [US9] Implement governance-preserving re-entry through N8 (depends on T111, T110)

---

## Final Phase: Polish & Cross-Cutting Concerns

- [x] T113 [P] Load test *(newly approved PVT-002)*: redirect path sustains ≥50 req/s on a single local node without observable error-rate increase, in `tests/integration/test_load_throughput.py` [NFR-003]
- [x] T114 [P] Latency test *(newly approved PVT-003)*: redirect resolution completes ≤100ms end-to-end at T113's load scale, in `tests/integration/test_latency.py` [NFR-007]
- [x] T115 [P] Execute the full `quickstart.md` validation suite end-to-end (all 7 scenarios) [Constitution Principle XI]
- [x] T116 [P] Run a dependency/secret scan (e.g., `pip-audit`) per `plan.md` §Security [NFR-001]
- [x] T117 Cross-check every FR-SVC-*/FR-ORC-*/NFR-* against this task list; confirm each maps to ≥1 executed, passing test; confirm findings F1–F7 (`/speckit-analyze`) and the Section 14 Independent Reviewer Gate's required corrections (clock abstraction T038, process-restart resumption T105, brownfield/rubber-stamp disclosures in plan.md) are all closed [NFR-009, Constitution Principle X]

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies.
- **Foundational (Phase 2)**: Depends on Setup — BLOCKS all user stories. Now includes the clock abstraction (T038) plus the shared retry/safe-stop/failure-classification mechanism (T039–T046), per finding F1 and the Section 14 reviewer-gate correction.
- **User Stories (Phases 3–11)**: All depend on Foundational completion.
  - US1–US4 (P1) completed first, in order (US1 establishes the base N1–N14 path US2/US3/US4 extend).
  - US5–US7 (P2) proceed once US1–US4 are complete.
  - US8–US9 (P3) proceed once US7 is complete.
- **Polish**: Depends on all desired user stories.

### User Story Dependencies

- **US1**: Foundational only.
- **US2**: Foundational + US1 (extends N3/N5).
- **US3**: Foundational + US1 (extends N3); independent of US2.
- **US4**: Foundational + US1 (extends N5/N8); independent of US2/US3.
- **US5**: US1 (N9–N14 base path).
- **US6**: Foundational's `AuditEvent` persistence (T032) + US1's audit-emitting nodes.
- **US7**: Foundational's shared mechanism (T040/T042/T044) + US1's N9 (T062); independent of US2–US6.
- **US8**: Foundational's `WorkflowInstance` persistence (T032); independent of US2–US7.
- **US9**: US1's N7 (T060); independent of US2, US3, US4, US5, US6, US8.

### Parallel Opportunities

- Setup: T002, T003 [P].
- Foundational: T006 [P] with T004/T005; T008/T010/T012 [P]; T015/T017/T019/T021/T024/T026/T028/T030/T033/T036/T039/T041/T043/T045/T047/T049/T050 [P] within their local dependency windows.
- Once Foundational completes, **US1, US7, and US8 can start in parallel** (US1 needs only Foundational; US7 needs the Foundational shared mechanism plus US1's N9, so it trails US1 slightly; US8 needs only `WorkflowInstance` persistence from T032) — demonstrating genuine task-graph parallelism, consistent with the engine's own FR-ORC-015.
- US2, US3, and US4 can each start in parallel once US1's T057/T058/T060 land (they extend different nodes) but must serialize on any shared file edit (e.g., two tasks both editing `src/orchestration/gates.py`).

---

## Parallel Example: Foundational Phase

```bash
Task: "Unit test: short-code format in tests/unit/test_short_link.py"
Task: "Unit test: URL scheme validation in tests/unit/test_validation.py"
Task: "Unit test: AuditEvent schema validation in tests/contract/test_audit_event_schema.py"
Task: "Unit test: bounded retry policy in tests/orchestration/test_retry_policy.py"
```

## Parallel Example: User Story 1

```bash
Task: "Unit test: N2 normalization in tests/orchestration/test_n2_normalization.py"
Task: "Unit test: N3 greenfield classification in tests/orchestration/test_n3_classification.py"
Task: "Unit test: N5 requirements gate in tests/orchestration/test_n5_requirements_gate.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup.
2. Complete Phase 2: Foundational (delivers the full URL-shortener domain plus the shared orchestration reliability mechanism).
3. Complete Phase 3: User Story 1.
4. **STOP and VALIDATE**: run `quickstart.md` Scenario 2 independently.

### Incremental Delivery (matches plan.md Delivery Sequence)

1. Setup + Foundational → domain + base orchestration path + shared reliability mechanism ready (slices 1–4).
2. US1 → Greenfield scenario demonstrable.
3. US2, US3 → Brownfield + Ambiguous scenarios demonstrable (slice 8 complete — all three required scenarios).
4. US4 → full approval governance (slice 5).
5. US7 (cross-node validation + N9 bulkheading), US8, US9 → reliability controls fully validated (slice 6).
6. US6 → observability (slice 7).
7. US5 → release readiness (slice 9).
8. Final Phase → load/latency validation (newly approved PVT-002/003), full quickstart validation, security scan, traceability cross-check.

### Stop Condition (per plan.md Planning Constraints)

If by the end of the timebox's first two-thirds the Foundational phase and US1–US4 (P1) are not complete, all further work on US5–US9 is deferred and disclosed as a residual limitation in the Final Engineering Summary (N14) rather than silently dropped.

---

## Notes

- [P] tasks = different files, no dependencies on incomplete tasks.
- [Story] label maps task to specific user story for traceability, per Constitution Principle X.
- T117 performs the final NFR-009 cross-check, including confirming findings F1–F7 from `/speckit-analyze` are closed.
- Verify each failing test actually fails for the expected reason before implementing (Constitution Principle IV).
- Commit after each red-green pair, per the doc's Suggested Commit Progression.
