---
description: "Task list for Agentic Software Engineering System: URL Shortener"
---

# Tasks: Agentic Software Engineering System: URL Shortener

**Input**: Design documents from `/specs/001-agentic-url-shortener/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md, docs/adr/ (all present and accepted)

**Tests**: Included — Constitution Principle IV mandates red-green-refactor TDD; every implementation task is paired with a preceding failing-test task.

**Organization**: Primary organization is by user story (per spec.md), in priority order (P1: US1–US4; P2: US5–US7; P3: US8–US9), preceded by Setup and Foundational phases. Each phase is cross-referenced to its corresponding slice in `plan.md`'s Delivery Sequence for traceability to the approved plan.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: Which user story this task belongs to (US1–US9); omitted for Setup/Foundational/Polish tasks
- Every task cites the requirement identifier(s) it satisfies in `[...]` at the end
- Every task requiring implementation is preceded by its failing-test task; a task is not complete until its paired test executes and passes (Constitution Principle XI)

## Path Conventions

Single project per `plan.md` Project Structure: `src/`, `tests/` at repository root.

---

## Phase 1: Setup — *(plan.md Delivery Sequence slice 1: Engineering baseline)*

**Purpose**: Repository scaffolding and tooling, no behavior yet.

- [ ] T001 Create the module skeleton exactly as defined in `plan.md` Project Structure: `src/domain/`, `src/api/`, `src/orchestration/`, `src/orchestration/nodes/`, `src/policy/`, `src/persistence/`, `src/telemetry/`, `src/config.py`, `tests/contract/`, `tests/integration/`, `tests/orchestration/`, `tests/unit/` [Plan §Project Structure]
- [ ] T002 [P] Initialize `pyproject.toml` declaring Python 3.12 and dependencies FastAPI, Uvicorn, Pydantic, pytest, pytest-asyncio, httpx, jsonschema per `research.md` Decisions 1, 2, 5 and ADR-002/ADR-011 [ADR-002, ADR-011]
- [ ] T003 [P] Configure `pytest.ini`/`pyproject.toml` test discovery across `tests/contract/`, `tests/integration/`, `tests/orchestration/`, `tests/unit/` per `plan.md` Testing Plan [NFR-009]

**Checkpoint**: Repository builds; `pytest` runs (zero tests, zero failures).

---

## Phase 2: Foundational (Blocking Prerequisites) — *(plan.md Delivery Sequence slices 2–4: Walking skeleton, Core URL behavior, Orchestration state model)*

**⚠️ CRITICAL**: No user story (US1–US9) can be implemented or demonstrated until this phase is complete — every user story exercises the URL-shortener domain as its demonstration content and runs through the orchestration graph/engine.

### Walking Skeleton

- [ ] T004 Implement `src/config.py`: environment-variable configuration with fail-fast validation at startup (no insecure defaults on malformed config) per `research.md` Decision 7 [Constitution Principle V, ADR-002]
- [ ] T005 Implement `src/persistence/db.py`: SQLite connection management in WAL mode per ADR-003 [D-003, CON-002, ADR-003]
- [ ] T006 [P] Contract test: `GET /healthz` in `tests/contract/test_health.py` asserting response matches `contracts/openapi.yaml` `HealthStatus` schema (`status` enum: ready/not_ready/degraded) — write failing first [FR-SVC-011]
- [ ] T007 Implement `GET /healthz` in `src/api/app.py` returning `ready`/`not_ready` per `contracts/openapi.yaml` (depends on T004, T005, T006) [FR-SVC-011]

### Core URL Behavior (domain layer)

- [ ] T008 [P] Unit test: short-code format matches `^[0-9a-zA-Z]{7}$` (Base62, exactly 7 chars) in `tests/unit/test_short_link.py` — write failing first [FR-SVC-001, FR-SVC-003, ADR-004]
- [ ] T009 Implement short-code generation in `src/domain/short_link.py`: Base62 alphabet (`0-9a-zA-Z`), fixed length 7, per ADR-004 (depends on T008) [FR-SVC-001, FR-SVC-003]
- [ ] T010 [P] Unit test: URL validation rejects disallowed schemes (`javascript:`, `data:`) and malformed URLs; accepts `http`/`https` only in `tests/unit/test_validation.py` — write failing first [FR-SVC-002, NFR-001]
- [ ] T011 Implement `src/domain/validation.py`: scheme allowlist (`http`, `https` only), malformed-URL rejection, loopback/private-address rejection per `plan.md` §Security (depends on T010) [FR-SVC-002, NFR-001]
- [ ] T012 [P] Unit test: on generation collision (seeded small keyspace to force it), the system regenerates and retries without a caller-visible error, bounded by 3 attempts in `tests/unit/test_short_link_collision.py` — write failing first [FR-SVC-003, ADR-004, edge case "collision race"]
- [ ] T013 Implement bounded collision-retry (max 3 attempts) in `src/domain/short_link.py` (depends on T009, T012) [FR-SVC-003]
- [ ] T014 Implement `src/persistence/short_links.py` repository for `ShortLink`: `short_code` (PK, unique among rows where `status='active'`), `target_url` (required, no uniqueness constraint), `created_at`, `expires_at` (nullable), `status` (enum: active/expired/deleted), `idempotency_key` (nullable, unique when present) — exact constraints per `data-model.md` ShortLink table (depends on T005) [data-model.md ShortLink]
- [ ] T015 [P] Contract test: `POST /v1/links` in `tests/contract/test_links_create.py` asserting 201 + `ShortLink` schema for valid `target_url`, 400 `INVALID_URL` for disallowed scheme, per `contracts/openapi.yaml` — write failing first [FR-SVC-001, FR-SVC-002]
- [ ] T016 Implement `POST /v1/links` in `src/api/links.py`, always minting a new code (no de-duplication against prior `target_url`, per Clarifications 2026-09-24), wiring validation + generation + persistence (depends on T011, T013, T014, T015) [FR-SVC-001, FR-SVC-002, FR-SVC-006]
- [ ] T017 [P] Unit test: identical `Idempotency-Key` on two creation requests returns the identical `short_code`, no duplicate row, in `tests/unit/test_idempotency.py` — write failing first [FR-SVC-008]
- [ ] T018 Implement `Idempotency-Key` handling in `src/api/links.py` + `src/persistence/short_links.py` (unique-key lookup precedes creation) (depends on T016, T017) [FR-SVC-008]
- [ ] T019 [P] Contract test: `GET /{short_code}` in `tests/contract/test_redirect.py` asserting 302+`Location` for active code, 404 `NOT_FOUND` for unknown code, 410 `EXPIRED` for expired code, per `contracts/openapi.yaml` — write failing first [FR-SVC-004, FR-SVC-005]
- [ ] T020 Implement `GET /{short_code}` redirect in `src/api/links.py` distinguishing not-found vs. expired outcomes (depends on T014, T019) [FR-SVC-004, FR-SVC-005]
- [ ] T021 Implement append-only `RedirectEvent` insert (`short_code`, `occurred_at`, `outcome`: redirected/not_found/expired) in `src/persistence/short_links.py` on every redirect resolution, per ADR-014 (depends on T020) [FR-SVC-007, ADR-014, data-model.md RedirectEvent]
- [ ] T022 [P] Unit test: `redirect_count` = COUNT of `outcome='redirected'` rows, `last_accessed_at` = MAX(`occurred_at`) for those rows, in `tests/unit/test_analytics_aggregation.py` — write failing first [FR-SVC-007, ADR-014]
- [ ] T023 Implement `GET /v1/links/{short_code}` detail endpoint with aggregated analytics in `src/api/links.py` per `contracts/openapi.yaml` `ShortLinkDetail` (depends on T021, T022) [FR-SVC-007]
- [ ] T024 [P] Integration test: concurrent creation + redirect requests for the same code produce no duplicate active codes and no lost-update analytics counts, in `tests/integration/test_concurrency.py` — write failing first [FR-SVC-009, SC-010]
- [ ] T025 Adjust `src/persistence/short_links.py` transaction boundaries as needed so T024 passes under SQLite WAL mode (depends on T014, T024) [FR-SVC-009]
- [ ] T026 [P] Integration test: simulated persistence unavailability (e.g., read-only DB file) returns 503 `STORE_UNAVAILABLE` with no internal detail leaked, in `tests/integration/test_persistence_failure.py` — write failing first [FR-SVC-010]
- [ ] T027 Implement persistence-failure handling in `src/api/links.py` + `src/persistence/db.py` per `contracts/openapi.yaml` 503 response (depends on T005, T026) [FR-SVC-010]

### Orchestration Scaffolding (needed by every user story)

- [ ] T028 Implement `src/persistence/orchestration_store.py` repositories for `WorkflowInstance`, `Decision`, `AuditEvent`, `PolicyCheckResult`, `PolicyException` with exact fields/constraints per `data-model.md` (e.g., `AuditEvent.result` enum success/failure/pending; `reason` required when `result='failure'`) (depends on T005) [data-model.md, ADR-003]
- [ ] T029 [P] Unit test: `AuditEvent` validates against `contracts/schemas/audit-event.schema.json`, including the "reason required when result=failure" conditional, in `tests/contract/test_audit_event_schema.py` — write failing first [FR-ORC-014]
- [ ] T030 Implement `src/orchestration/graph.py`: declare the 14-node DAG (N1–N14) and edges exactly as specified in `contracts/orchestration-state-machine.md`, with each node's purpose/preconditions/postconditions/allowed-transitions/prohibited-transitions as structured data (depends on T029) [FR-ORC-001, CON-003, ADR-005]
- [ ] T031 Implement `src/orchestration/engine.py`: async executor for sequential edge traversal and `AuditEvent` emission per transition (depends on T028, T030) [FR-ORC-014, ADR-005]
- [ ] T032 [P] Unit test: N1 (Requirement Ingestion) creates `WorkflowInstance` + `Requirement` with a stable `run_id`/`requirement_id`; empty/malformed input is rejected without creating a `WorkflowInstance`, in `tests/orchestration/test_n1_ingestion.py` — write failing first [FR-ORC-001]
- [ ] T033 Implement N1 in `src/orchestration/nodes/n1_ingestion.py` (depends on T031, T032) [FR-ORC-001]
- [ ] T034 [P] Contract test: `POST /v1/workflows` returns a `run_id` conforming to `contracts/schemas/workflow-state.schema.json`, in `tests/contract/test_workflows_create.py` — write failing first [FR-ORC-001, FR-ORC-002]
- [ ] T035 Implement `POST /v1/workflows` and `GET /v1/workflows/{run_id}` in `src/api/workflows.py` (depends on T033, T034) [FR-ORC-001, FR-ORC-002]

**Checkpoint**: Foundation ready — URL-shortener domain is fully functional and testable on its own (FR-SVC-001..011 complete), and the orchestration engine can ingest a requirement and report its state. User story implementation can now begin.

---

## Phase 3: User Story 1 — Greenfield Requirement Flows Straight Through Governed Orchestration (Priority: P1) 🎯 MVP
*(plan.md Delivery Sequence slices 4/8: Orchestration state model, Three scenarios)*

**Goal**: A well-specified, unambiguous, in-policy requirement proceeds through decomposition → design → implementation → testing → documentation → validation without an artificial clarification gate, while still passing the mandatory architecture and requirements approval gates.

**Independent Test**: Submit a complete, consistent, testable, in-policy requirement via `POST /v1/workflows`; verify via the audit endpoint that no `clarification_requested` event occurs and the run reaches `completed`.

### Tests for User Story 1

- [ ] T036 [P] [US1] Unit test: N2 (Requirement Normalization) produces `normalized_description`; transient failure retries (bounded, per ADR-007), permanent failure → SAFE_STOP, in `tests/orchestration/test_n2_normalization.py` — write failing first [FR-ORC-003 (adjacent), ADR-007]
- [ ] T037 [P] [US1] Unit test: N3 classifies a complete/consistent/testable/in-policy requirement as `greenfield` and does NOT trigger N4, in `tests/orchestration/test_n3_classification.py` — write failing first [FR-ORC-003, FR-ORC-004, User Story 1 acceptance scenario 1]
- [ ] T038 [P] [US1] Unit test: N5 (Requirements Gate) auto-populates an "auto-qualified" approval rationale for the greenfield path but still requires an explicit recorded human approval before advancing; no response before 24h timeout → SAFE_STOP, in `tests/orchestration/test_n5_requirements_gate.py` — write failing first [FR-ORC-005, FR-ORC-006, User Story 1 acceptance scenario 3, ADR-006]
- [ ] T039 [P] [US1] Integration test: full path N1→N2→N3→N5→N6→N7→N8→N9→(N10‖N11‖N12)→N13→N14 for a well-specified requirement produces NO `clarification_requested` audit event and reaches `completed`, per `quickstart.md` Scenario 2, in `tests/integration/test_scenario_greenfield.py` — write failing first [SC-002, User Story 1]

### Implementation for User Story 1

- [ ] T040 [US1] Implement N2 in `src/orchestration/nodes/n2_normalization.py` with bounded retry (3 attempts, 200ms exponential backoff, ADR-007) (depends on T031, T036)
- [ ] T041 [US1] Implement N3 quality checks (completeness/consistency/testability/in-policy) and classification in `src/orchestration/nodes/n3_classification.py` (depends on T040, T037)
- [ ] T042 [US1] Implement N5 with 24h timeout (ADR-006) in `src/orchestration/gates.py`, including the auto-qualified rationale path for greenfield (depends on T041, T038)
- [ ] T043 [US1] Implement N6 (Task Decomposition) in `src/orchestration/nodes/n6_decomposition.py` (depends on T042)
- [ ] T044 [US1] Implement N7 (Architecture & Design, parallel-branch-capable with synchronization join) in `src/orchestration/nodes/n7_design.py` (depends on T043)
- [ ] T045 [US1] Implement N8 (Human Approval Gate: Architecture) in `src/orchestration/gates.py`, reusing the gate-timeout mechanism from T042 (depends on T044)
- [ ] T046 [US1] Implement N9 (Implementation) with genuine parallel task fan-out and a synchronization join in `src/orchestration/nodes/n9_implementation.py` + concurrency support in `src/orchestration/engine.py` (depends on T045) [FR-ORC-015]
- [ ] T047 [US1] Implement N10 (Testing), N11 (Documentation), N12 (Security & Risk Validation) as parallel nodes joining before N13, and N13 (Release-Readiness, aggregation only — human gate implemented in US5) and N14 (Final Engineering Summary) in `src/orchestration/nodes/n10_testing.py`, `n11_documentation.py`, `n12_security.py`, `n13_release_readiness.py`, `n14_summary.py` (depends on T046) [FR-ORC-015, FR-ORC-019]
- [ ] T048 [US1] Run T039 integration test to green; adjust N1–N14 wiring as needed (depends on T047, T039)

**Checkpoint**: User Story 1 fully functional and independently testable — this is the MVP.

---

## Phase 4: User Story 2 — Brownfield Change Requires Pre-Change Impact Analysis (Priority: P1)
*(plan.md Delivery Sequence slices 4/8)*

**Goal**: A brownfield change produces a complete impact-analysis artifact, human-approved before any implementation task starts.

**Independent Test**: Submit a defect-correction request; verify via the API that implementation does not begin until the impact-analysis artifact is approved, and that the artifact contains all required categories.

### Tests for User Story 2

- [ ] T049 [P] [US2] Unit test: N3 routes a `brownfield`-classified requirement to N4b before N5, in `tests/orchestration/test_n3_brownfield_routing.py` — write failing first [FR-ORC-004, User Story 2]
- [ ] T050 [P] [US2] Unit test: N4b's impact-analysis artifact contains impacted components, interfaces, data flows, tests, documentation, regression risks, and rollout/rollback considerations — none omitted, in `tests/orchestration/test_n4b_impact_analysis.py` — write failing first [User Story 2 acceptance scenario 1]
- [ ] T051 [P] [US2] Unit test: N5 (brownfield path) presents the N4b artifact directly and blocks on unapproved/silent timeout, in `tests/orchestration/test_n5_brownfield_review.py` — write failing first [User Story 2 acceptance scenario 2]
- [ ] T052 [P] [US2] Unit test: an irreversible-consequence brownfield change is classified as requiring compensation (not rollback) and is surfaced distinctly to the human, in `tests/orchestration/test_rollback_vs_compensation.py` — write failing first [User Story 2 negative scenario, ADR-008]
- [ ] T053 [P] [US2] Integration test: full brownfield path per `quickstart.md` Scenario 4, in `tests/integration/test_scenario_brownfield.py` — write failing first [SC-003, User Story 2]

### Implementation for User Story 2

- [ ] T054 [US2] Extend N3 in `src/orchestration/nodes/n3_classification.py` with brownfield routing (depends on T041, T049)
- [ ] T055 [US2] Implement N4b in `src/orchestration/nodes/n4b_impact_analysis.py`, including rollback-vs-compensation classification per ADR-008 (depends on T054, T050, T052)
- [ ] T056 [US2] Extend N5 in `src/orchestration/gates.py` to review the N4b artifact for the brownfield path (depends on T042, T055, T051)
- [ ] T057 [US2] Run T053 integration test to green (depends on T056, T053)

**Checkpoint**: User Stories 1 and 2 both independently functional.

---

## Phase 5: User Story 3 — Ambiguous or Conflicting Requirement Blocks Unsafe Implementation (Priority: P1)
*(plan.md Delivery Sequence slices 4/8)*

**Goal**: An incomplete/contradictory requirement halts before decomposition, requests structured clarification, and resumes correctly after a recorded human decision.

**Independent Test**: Submit an incomplete requirement; verify it enters `clarification_pending` and does not reach N6 before a clarification decision is recorded.

### Tests for User Story 3

- [ ] T058 [P] [US3] Unit test: N3 classifies an incomplete/self-contradictory requirement as `ambiguous` (at least one quality check FAIL), in `tests/orchestration/test_n3_ambiguous_classification.py` — write failing first [FR-ORC-003, FR-ORC-004, User Story 3 acceptance scenario 1]
- [ ] T059 [P] [US3] Unit test: N4 produces a structured clarification request (question/impact/current assumption/owner/required decision point); 24h timeout → SAFE_STOP with `reason=clarification_gate_timeout`, never auto-answered, in `tests/orchestration/test_n4_clarification.py` — write failing first [FR-ORC-004, User Story 3 negative scenario]
- [ ] T060 [P] [US3] Unit test: after an accepted clarification answer, the workflow resumes at N2 (not from zero) and only the affected path was suspended, in `tests/orchestration/test_n4_resume.py` — write failing first [User Story 3 acceptance scenarios 2–3]
- [ ] T061 [P] [US3] Integration test: full ambiguous-requirement path per `quickstart.md` Scenario 3, in `tests/integration/test_scenario_ambiguous.py` — write failing first [SC-004, User Story 3]

### Implementation for User Story 3

- [ ] T062 [US3] Extend N3 with ambiguity-detection quality checks in `src/orchestration/nodes/n3_classification.py` (depends on T054, T058)
- [ ] T063 [US3] Implement N4 in `src/orchestration/nodes/n4_clarification.py` with 24h timeout (ADR-006) (depends on T062, T059)
- [ ] T064 [US3] Implement clarification-answer resume logic in `src/orchestration/nodes/n4_clarification.py` + `src/orchestration/engine.py` (depends on T063, T060)
- [ ] T065 [US3] Run T061 integration test to green (depends on T064, T061)

**Checkpoint**: All three required scenarios (Greenfield/Brownfield/Ambiguous — User Stories 1–3) are independently functional. This satisfies `plan.md` Delivery Sequence slice 8's core requirement.

---

## Phase 6: User Story 4 — Human Reviewer Inspects and Approves at Mandatory Gates (Priority: P1)
*(plan.md Delivery Sequence slice 5: Approval governance)*

**Goal**: Explicit approve/reject actions at every mandatory gate, with no silent auto-advance and no undefined rejection state.

**Independent Test**: Drive a workflow to a gate; verify it blocks; approve on one run and verify progression; reject on a separate run and verify return to the producing node with the rejection reason attached.

### Tests for User Story 4

- [ ] T066 [P] [US4] Unit test: rejecting N5 routes back to N3/N4b, and rejecting N8 routes back to N7, each with the rejection rationale attached as a `Decision`, in `tests/orchestration/test_gate_rejection.py` — write failing first [User Story 4 acceptance scenario 3]
- [ ] T067 [P] [US4] Unit test: an approval `Decision` records `actor_role_capacity`, timestamp, and any conditions, in `tests/orchestration/test_decision_recording.py` — write failing first [User Story 4 acceptance scenario 2]

### Implementation for User Story 4

- [ ] T068 [US4] Implement rejection-handling routing in `src/orchestration/gates.py` (depends on T042, T045, T066)
- [ ] T069 [US4] Implement `Decision` persistence with `actor_role_capacity` in `src/persistence/orchestration_store.py` + `src/orchestration/gates.py` (depends on T028, T067)

**Checkpoint**: All P1 user stories (US1–US4) complete.

---

## Phase 7: User Story 5 — Release Owner Obtains a Release-Readiness Decision (Priority: P2)
*(plan.md Delivery Sequence slice 9: Release readiness)*

**Goal**: Aggregate policy checks into an overall PASS/FAIL outcome; FAIL blocks release and is never silently treated as PASS.

**Independent Test**: Inject one known-FAIL policy check with no exception; verify the overall outcome is FAIL and specific/traceable.

### Tests for User Story 5

- [ ] T070 [P] [US5] Unit test: N12 policy evaluation produces PASS/FAIL/EXCEPTION_REQUESTED/NOT_APPLICABLE conforming to `contracts/schemas/policy-evaluation.schema.json`, in `tests/orchestration/test_n12_policy_checks.py` — write failing first [FR-ORC-016]
- [ ] T071 [P] [US5] Unit test: N13 aggregation yields overall FAIL when any mandatory check is FAIL with no approved, non-expired exception, in `tests/orchestration/test_n13_release_readiness.py` — write failing first [FR-ORC-017, User Story 5 acceptance scenario 2]
- [ ] T072 [P] [US5] Unit test: a `PolicyCheckResult` referencing an expired `PolicyException` reverts to FAIL on next evaluation, in `tests/unit/test_policy_exception_expiry.py` — write failing first [data-model.md invariant, FR-ORC-018]
- [ ] T073 [P] [US5] Integration test: release-readiness FAIL per `quickstart.md` Scenario 6, in `tests/orchestration/test_release_readiness_fail_on_policy_violation.py` — write failing first [SC-006, User Story 5]

### Implementation for User Story 5

- [ ] T074 [US5] Implement N12 in `src/policy/checks.py` + `src/orchestration/nodes/n12_security.py` (depends on T047, T070)
- [ ] T075 [US5] Implement N13 aggregation + human release-readiness gate in `src/orchestration/nodes/n13_release_readiness.py` (depends on T074, T071)
- [ ] T076 [US5] Implement `PolicyException` expiry enforcement in `src/persistence/orchestration_store.py` + `src/policy/checks.py` (depends on T075, T072)
- [ ] T077 [US5] Run T073 integration test to green (depends on T076, T073)

---

## Phase 8: User Story 6 — Assessment Reviewer Reconstructs Any Execution from Evidence (Priority: P2)
*(plan.md Delivery Sequence slice 7: Observability)*

**Goal**: Every state transition/decision/approval/retry/failure/replanning event is retrievable and reconstructable by `run_id`; demonstration metrics are clearly labeled.

**Independent Test**: Given only a `run_id`, reconstruct the full sequence of a completed run from the audit endpoint alone.

### Tests for User Story 6

- [ ] T078 [P] [US6] Unit test: `GET /v1/workflows/{run_id}/audit` returns every event with actor_type/action/timestamp/result/reason, in `tests/contract/test_audit_query.py` — write failing first [FR-ORC-014, User Story 6 acceptance scenario 1]
- [ ] T079 [P] [US6] Unit test: computed metrics carry an `is_demonstration_data` marker, in `tests/unit/test_metrics_labeling.py` — write failing first [FR-ORC-020]
- [ ] T080 [P] [US6] Unit test: MTTR calculation excludes `recovered: false` events from its denominator and reports unrecovered count separately, in `tests/unit/test_mttr_calculation.py` — write failing first [Plan §Observability and Metrics]
- [ ] T081 [P] [US6] Integration test: full audit reconstruction per `quickstart.md` Scenario 7, in `tests/integration/test_audit_reconstruction.py` — write failing first [SC-008, User Story 6]

### Implementation for User Story 6

- [ ] T082 [US6] Implement `GET /v1/workflows/{run_id}/audit` in `src/api/workflows.py` (depends on T028, T078)
- [ ] T083 [US6] Implement metrics computation (success rate, failure rate, retry frequency, rollback/compensation frequency, MTTR, end-to-end latency) in `src/telemetry/metrics.py` per `plan.md` §Observability and Metrics (depends on T082, T079, T080)
- [ ] T084 [US6] Run T081 integration test to green (depends on T083, T081)

---

## Phase 9: User Story 7 — Retry, Fallback, and Safe-Stop Under Transient Failure (Priority: P2)
*(plan.md Delivery Sequence slice 6: Reliability controls)*

**Goal**: Bounded retry with backoff on transient failure; safe-stop on exhausted retries with no fallback; permanent failures never retried.

**Independent Test**: Inject a transient failure into a node with a known retry policy; verify bounded retries then safe-stop on exhaustion.

### Tests for User Story 7

- [ ] T085 [P] [US7] Unit test: bounded retry (3 attempts, 200ms exponential backoff) on transient failure, in `tests/orchestration/test_retry_policy.py` — write failing first [FR-ORC-007, PVT-004, ADR-007]
- [ ] T086 [P] [US7] Unit test: SAFE_STOP entered with reason recorded when retries are exhausted and no fallback is defined, in `tests/orchestration/test_safe_stop_on_exhausted_retry.py` — write failing first [FR-ORC-010, User Story 7 acceptance scenario 2]
- [ ] T087 [P] [US7] Unit test: a permanent-failure classification routes directly to fallback/safe-stop without any retry attempt, in `tests/orchestration/test_permanent_failure_routing.py` — write failing first [User Story 7 acceptance scenario 3]

### Implementation for User Story 7

- [ ] T088 [US7] Implement the shared bounded-retry utility in `src/orchestration/engine.py` per ADR-007 (depends on T031, T085)
- [ ] T089 [US7] Implement SAFE_STOP cross-cutting state in `src/orchestration/engine.py` (depends on T088, T086)
- [ ] T090 [US7] Implement transient/permanent failure-classification dispatch per node in `src/orchestration/engine.py` (depends on T089, T087)

---

## Phase 10: User Story 8 — Recoverable Interruption and Resumption (Priority: P3)
*(plan.md Delivery Sequence slice 6)*

**Goal**: An interrupted workflow resumes from its last persisted state without data loss or duplicated side effects.

**Independent Test**: Interrupt a workflow mid-stage, restart, verify it resumes at the correct stage.

### Tests for User Story 8

- [ ] T091 [P] [US8] Unit test: on simulated interruption + restart, the workflow resumes at `WorkflowInstance.current_stage` without re-executing already-completed, side-effecting steps, in `tests/orchestration/test_resumption.py` — write failing first [FR-ORC-011, User Story 8 acceptance scenario 1]
- [ ] T092 [P] [US8] Unit test: interruption and resumption both appear as audit events, in `tests/orchestration/test_resumption_audit.py` — write failing first [User Story 8 acceptance scenario 2]

### Implementation for User Story 8

- [ ] T093 [US8] Implement resumption-on-startup logic in `src/orchestration/engine.py` (depends on T028, T091)
- [ ] T094 [US8] Implement `workflow_interrupted`/`workflow_resumed` audit events in `src/orchestration/engine.py` (depends on T093, T092)

---

## Phase 11: User Story 9 — Dynamic Replanning on Upstream Change (Priority: P3)
*(plan.md Delivery Sequence slice 6)*

**Goal**: A material upstream artifact change suspends dependent downstream work and re-applies the original approval gates before resuming.

**Independent Test**: Approve a plan, begin downstream work, revise the approved plan materially; verify downstream suspension and re-approval requirement.

### Tests for User Story 9

- [ ] T095 [P] [US9] Unit test: a material revision to an approved N7 artifact triggers dependency-staleness detection and suspends dependent N9 work, in `tests/orchestration/test_dynamic_replanning.py` — write failing first [FR-ORC-012, User Story 9 acceptance scenario 1]
- [ ] T096 [P] [US9] Unit test: replanned work re-enters N8 (the same approval gate) before resuming N9 — no bypass, in `tests/orchestration/test_replanning_governance.py` — write failing first [FR-ORC-013, User Story 9 acceptance scenario 2]

### Implementation for User Story 9

- [ ] T097 [US9] Implement `src/orchestration/replanning.py` with version-stamped artifacts and material/cosmetic revision marking per ADR-009 (depends on T044, T095)
- [ ] T098 [US9] Implement governance-preserving re-entry through N8 in `src/orchestration/replanning.py` + `src/orchestration/gates.py` (depends on T097, T096)

---

## Final Phase: Polish & Cross-Cutting Concerns

- [ ] T099 [P] Execute the full `quickstart.md` validation suite end-to-end (all 7 scenarios) and confirm every expected outcome, per Constitution Principle XI evidence-based completion [Plan §Testing Plan]
- [ ] T100 [P] Run a dependency/secret scan (e.g., `pip-audit`) as part of N12's policy evaluation per `plan.md` §Security and Constitution Principle V [NFR-001]
- [ ] T101 Cross-check every FR-SVC-*/FR-ORC-*/NFR-* against the task list above and confirm each maps to at least one executed, passing automated test (NFR-009); record any gap found as a new task before declaring the feature complete [NFR-009, Constitution Principle X]

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies.
- **Foundational (Phase 2)**: Depends on Setup — BLOCKS all user stories.
- **User Stories (Phases 3–11)**: All depend on Foundational completion.
  - US1–US4 (P1) should be completed first, in order (US1 establishes the base N1–N14 path that US2/US3/US4 extend).
  - US5–US7 (P2) can proceed once US1–US4 are complete.
  - US8–US9 (P3) can proceed once US7 (failure classification) is complete, since they build on the same engine primitives.
- **Polish (Final Phase)**: Depends on all desired user stories being complete.

### User Story Dependencies

- **US1 (P1)**: Depends on Foundational only — establishes N1–N14 base path.
- **US2 (P1)**: Depends on Foundational + US1 (extends N3/N5 that US1 implements).
- **US3 (P1)**: Depends on Foundational + US1 (extends N3 that US1 implements); independent of US2.
- **US4 (P1)**: Depends on Foundational + US1 (extends N5/N8 gates that US1 implements); independent of US2/US3.
- **US5 (P2)**: Depends on US1 (N9–N14 base path).
- **US6 (P2)**: Depends on Foundational's `AuditEvent` persistence (T028) and US1's audit-emitting nodes.
- **US7 (P2)**: Depends on Foundational's engine (T031); independent of US2–US6.
- **US8 (P3)**: Depends on Foundational's `WorkflowInstance` persistence (T028); independent of US2–US7.
- **US9 (P3)**: Depends on US1's N7 (T044); independent of US2, US3, US4, US5, US6, US8.

### Within Each User Story

- Tests MUST be written and FAIL before implementation (Constitution Principle IV).
- Node/domain logic before endpoints; endpoints before integration tests are run to green.
- Story complete only when its integration test (or, for US4/US7/US8/US9, its unit tests) executes green.

### Parallel Opportunities

- All Setup tasks marked [P] (T002, T003).
- Within Foundational: T006 [P] runs alongside T004/T005; T008/T010/T012 [P] (independent unit tests) run in parallel; T015/T017/T019/T022/T024/T026/T029/T032/T034 [P] similarly.
- Within each user story phase, all test tasks marked [P] run in parallel (different files, no shared dependency).
- Once Foundational completes, **US1, US7, and US8 can start in parallel** (US1 needs only Foundational; US7 needs only the engine from T031; US8 needs only `WorkflowInstance` persistence from T028) — demonstrating genuine parallelism in the task graph itself, consistent with the orchestration engine's own FR-ORC-015 requirement.
- US2, US3, and US4 can each start in parallel once US1's T041/T042/T044 land (they extend different nodes: US2→N3/N5, US3→N3/N4, US4→N5/N8 rejection paths) but must serialize on any shared file edit (e.g., two tasks both editing `src/orchestration/gates.py` cannot run concurrently — see task-level dependencies above).

---

## Parallel Example: Foundational Phase

```bash
# Launch independent unit tests together:
Task: "Unit test: short-code format in tests/unit/test_short_link.py"
Task: "Unit test: URL scheme validation in tests/unit/test_validation.py"
Task: "Unit test: AuditEvent schema validation in tests/contract/test_audit_event_schema.py"
```

## Parallel Example: User Story 1

```bash
# Launch all tests for User Story 1 together:
Task: "Unit test: N2 normalization in tests/orchestration/test_n2_normalization.py"
Task: "Unit test: N3 greenfield classification in tests/orchestration/test_n3_classification.py"
Task: "Unit test: N5 requirements gate in tests/orchestration/test_n5_requirements_gate.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup.
2. Complete Phase 2: Foundational (CRITICAL — blocks all stories; also delivers the full URL-shortener domain, FR-SVC-001..011).
3. Complete Phase 3: User Story 1 (Greenfield).
4. **STOP and VALIDATE**: run `quickstart.md` Scenario 2 independently.
5. This is the assessment's MVP — demonstrates the core orchestration differentiator end-to-end.

### Incremental Delivery (matches plan.md Delivery Sequence)

1. Setup + Foundational → domain + base orchestration path ready (slices 1–4).
2. US1 → Greenfield scenario demonstrable (slice 4/8 partial).
3. US2, US3 → Brownfield + Ambiguous scenarios demonstrable (slice 8 complete — all three required scenarios).
4. US4 → full approval governance (slice 5).
5. US7, US8, US9 → reliability controls (slice 6).
6. US6 → observability (slice 7).
7. US5 → release readiness (slice 9).
8. Final Phase → full quickstart validation, security scan, traceability cross-check.

### Stop Condition (per plan.md Planning Constraints)

If by the end of the timebox's first two-thirds the Foundational phase and US1–US4 (P1) are not complete, all further work on US5–US9 is deferred and disclosed as a residual limitation in the Final Engineering Summary (N14) rather than silently dropped — the P1 stories (all three required scenarios plus approval governance) are the minimum defensible release-readiness floor.

---

## Notes

- [P] tasks = different files, no dependencies on incomplete tasks.
- [Story] label maps task to specific user story for traceability, per Constitution Principle X.
- Every task cites its satisfied requirement identifier(s); `T101` performs a final NFR-009 cross-check before completion is declared.
- Verify each failing test actually fails for the expected reason before implementing (Constitution Principle IV) — this is a gate on every task pair above, not just a suggestion.
- Commit after each red-green pair, per the doc's Suggested Commit Progression.
- Avoid: vague tasks, same-file conflicts marked [P], cross-story dependencies that break independent testability beyond what is explicitly documented above.
