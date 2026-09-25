# Implementation Plan: Agentic Software Engineering System: URL Shortener

**Branch**: `001-agentic-url-shortener` | **Date**: 2026-09-24 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/001-agentic-url-shortener/spec.md`

## Summary

Build a locally-runnable URL shortener API (anonymous, embedded-persistence, Base62 7-char codes, no de-duplication) as the demonstration domain for a governed, stateful, non-linear agentic orchestration engine. The orchestration engine is a custom-built, persisted DAG/state-machine (not a third-party workflow product, and not a linear agent chain) that processes ingested requirements through 14 defined nodes with genuine parallel fan-out/synchronization, mandatory human approval gates, bounded retry, fallback, rollback/compensation, safe-stop, resumption, and dynamic replanning — see `contracts/orchestration-state-machine.md` for the full node-by-node design. Technical approach and rationale are recorded in `research.md`; data model in `data-model.md`; API/schema contracts in `contracts/`; end-to-end validation steps in `quickstart.md`.

## Technical Context

**Language/Version**: Python 3.12

**Primary Dependencies**: FastAPI, Uvicorn, Pydantic, pytest, httpx (via FastAPI TestClient), jsonschema

**Storage**: SQLite, file-backed, WAL mode (embedded/in-process, per D-003)

**Testing**: pytest (unit/integration/orchestration-transition), FastAPI TestClient (API/contract), jsonschema-based contract validation against `contracts/openapi.yaml` and `contracts/schemas/*.json`

**Target Platform**: Local single-node (macOS/Linux), no external managed infrastructure (CON-002)

**Project Type**: Web service — single project with clearly separated internal modules (see Project Structure below)

**Performance Goals**: PVT-002 (≥50 req/s redirect path, proposed) / PVT-003 (≤100ms redirect latency, proposed) — both pending human approval, not confirmed production targets

**Constraints**: No caller authentication (D-001/CON-004); no external managed infrastructure (CON-002); rate limiting documented but not implemented (EXC-006); 24-hour human-gate timeout (confirmed); indefinite audit retention for this prototype (confirmed)

**Scale/Scope**: Single-tenant demonstration prototype (EXC-001); not designed for multi-region/HA (EXC-004)

All Technical Context fields are resolved — no `NEEDS CLARIFICATION` markers remain. Technology selections are recorded as proposed Architecture Decisions in `research.md`, pending human approval at the ADR gate (Human Gate 4), per Constitution Principle III.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-checked after Phase 1 design below.*

| Principle | Check | Status |
|---|---|---|
| I. Specification Before Implementation | Plan derives entirely from the approved, clarified spec; no implementation code written in this phase. | PASS |
| II. Explicit Agentic Orchestration | `contracts/orchestration-state-machine.md` defines an explicit 14-node DAG with real parallel fan-out (N9→N10/N11/N12) and synchronization joins, conditional branching, replanning, and resumption — not a linear chain. | PASS |
| III. Human Governance | 5 mandatory human gates modeled (N5, N8, N13, plus N4 clarification and exception approvals); timeout never auto-approves (24h → SAFE_STOP). | PASS |
| IV. Test-Driven Engineering | `research.md` Decision 5 commits to pytest-based TDD; quickstart scenarios assume red-green evidence; enforced at task level in Phase 2 (`/speckit-tasks`). | PASS (deferred enforcement to Phase 2/3) |
| V. Security and Privacy by Design | FR-SVC-002/NFR-001 enforced via URL scheme allowlist in domain logic (Phase 2); no secrets in this prototype's scope beyond none-required (no auth). | PASS |
| VI. Compliance and Change-Control Policy Enforcement | N12/N13 model explicit PolicyCheckResult evaluation with PASS/FAIL/EXCEPTION_REQUESTED/NOT_APPLICABLE and exception expiry enforcement (`data-model.md` invariants). | PASS |
| VII. Architecture and Maintainability | Project Structure below separates domain, API, orchestration, persistence, policy, and telemetry into distinct modules. | PASS |
| VIII. Reliability and Recovery | Every node in the state machine has defined timeout/retry/failure-classification/fallback; SAFE_STOP and REPLANNING are explicit cross-cutting states. | PASS |
| IX. Observability and Auditability | `AuditEvent` schema + N-by-N `Audit Events` list ensure every transition is recorded with actor/action/timestamp/result/reason. | PASS |
| X. Traceability and Repository Integrity | `data-model.md` ties every governance record to `run_id`; contracts are generated from typed code (FastAPI), avoiding a second source of truth. | PASS |
| XI. Evidence-Based Completion | N14 (Final Engineering Summary) is explicitly evidence-derived, not freeform narrative (FR-ORC-019). | PASS |

**No violations requiring justification.** The one deliberate complexity increase (a custom orchestration engine instead of an off-the-shelf workflow product) is justified in `research.md` Decision 4 as *required* by CON-003/Principle II, not optional — recorded in Complexity Tracking below for visibility.

## Project Structure

### Documentation (this feature)

```text
specs/001-agentic-url-shortener/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md         # Phase 1 output
├── quickstart.md         # Phase 1 output
├── contracts/            # Phase 1 output
│   ├── openapi.yaml
│   ├── orchestration-state-machine.md
│   └── schemas/
│       ├── workflow-state.schema.json
│       ├── approval.schema.json
│       ├── audit-event.schema.json
│       └── policy-evaluation.schema.json
└── tasks.md              # Phase 2 output (/speckit-tasks — not created by /speckit-plan)
```

### Source Code (repository root)

```text
src/
├── domain/               # URL-shortener domain logic (framework-agnostic)
│   ├── short_link.py      # ShortLink entity, code generation, expiration rules
│   └── validation.py      # URL scheme/format validation (FR-SVC-002)
├── api/                  # API delivery layer (FastAPI)
│   ├── app.py             # FastAPI app wiring
│   ├── links.py           # /v1/links, /{short_code}, /healthz routes
│   └── workflows.py       # /v1/workflows routes (orchestration ingestion/inspection)
├── orchestration/         # The governed orchestration engine (the core differentiator)
│   ├── graph.py            # Node/edge definitions (contracts/orchestration-state-machine.md)
│   ├── engine.py           # Executor: dispatch, parallel fan-out/join, retry/backoff
│   ├── nodes/              # One module per node (N1..N14) implementing purpose/pre/post
│   ├── gates.py            # Human approval gate logic (timeout, escalation, safe-stop)
│   └── replanning.py       # Dependency-staleness detection and re-planning (FR-ORC-012/013)
├── policy/                # Policy/compliance guardrail evaluation (N12/N13)
│   └── checks.py
├── persistence/           # SQLite repositories (one per entity in data-model.md)
│   ├── db.py               # Connection/migration management
│   ├── short_links.py
│   └── orchestration_store.py  # WorkflowInstance, Decision, AuditEvent, PolicyCheckResult, PolicyException
├── telemetry/             # Structured logging with run_id correlation (NFR-005)
│   └── logging.py
└── config.py              # Environment-variable configuration, fail-fast validation

tests/
├── contract/              # Validates API responses against contracts/openapi.yaml + schemas/
├── integration/            # End-to-end scenario tests (quickstart.md scenarios 1-4,7)
├── orchestration/          # State-transition tests per node (retry, fallback, safe-stop, replanning, resumption)
└── unit/                  # Domain logic unit tests (code generation, validation, expiration)
```

**Structure Decision**: Single project (Option 1 from the template), with the source tree above as the concrete internal module layout. A single deployable service is sufficient because the orchestration engine and the URL-shortener API share one process and one embedded SQLite database (per D-003/CON-002) — a separate "control plane" service would require inter-process/network communication, which is unjustified complexity for a single-node prototype and would itself need its own trust-boundary and deployment story.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|---|---|---|
| Custom orchestration engine (vs. adopting Temporal/Airflow/Prefect) | CON-003 and Constitution Principle II explicitly prohibit a linear agent chain and require real parallel/branching/replanning semantics that are directly inspectable for assessment review | Off-the-shelf workflow engines require external server/broker infrastructure, violating CON-002/AS-002 (locally runnable, no managed infra), and would hide the orchestration semantics being assessed inside a third-party engine rather than demonstrating them in this codebase |

## Human-in-the-Loop Controls

Mandatory approval gates (all with a 24-hour timeout → SAFE_STOP/escalation, never auto-approval, per Constitution Principle III):

| Gate | Trigger | Node | Actor Capacity |
|---|---|---|---|
| Unresolved ambiguity | Classification = ambiguous, or mid-workflow ambiguity raised | N4 | reviewer_approver |
| Requirements approval | Always (expedited for well-specified greenfield; full review for brownfield) | N5 | reviewer_approver |
| Architecture approval | Always, after design | N8 | reviewer_approver |
| Security-sensitive / destructive action | Any node attempting an irreversible operation (NFR-011) | ad hoc, blocks the initiating node | reviewer_approver |
| Constitutional exception | Any PolicyCheckResult requiring EXCEPTION_REQUESTED | N12/N13 | release_owner |
| Material risk acceptance | Release-readiness with disclosed residual risk | N13 | release_owner |
| Release readiness | Always, before N14 | N13 | release_owner |
| Final submission | Outside the runtime engine — a human act (this repository's `git push` / assessment submission) | n/a | human (project owner) |

## Reliability Model

Defined once here; applied per-node in `contracts/orchestration-state-machine.md`:

- **Transient failure**: infra/timeout-class errors (e.g., a bounded compute timeout, a flaky test-runner). Eligible for retry.
- **Permanent failure**: logic-class errors (e.g., a genuine failing test, an unparseable requirement, a contradiction). NOT eligible for retry — routes directly to fallback, human review, or SAFE_STOP.
- **Retry bounds**: 3 attempts default (PVT-004, proposed), exponential backoff starting at 200ms.
- **Idempotency / duplicate execution protection**: `Idempotency-Key` header for link creation (FR-SVC-008); orchestration node re-entry after resumption MUST NOT re-execute already-completed side-effecting steps (checked via `WorkflowInstance.current_stage` + a per-node completion marker).
- **Fallback**: defined per node in the state machine (most nodes: none beyond retry, by design — ambiguity and design defects have no safe default); at least one node type (N9 task-level) demonstrates a real fallback (bulkheaded task failure not blocking unrelated parallel tasks).
- **Rollback vs. compensation**: rollback = reversing an operation with no lasting side effect (e.g., discarding an unapproved draft design); compensation = offsetting an operation that cannot be cleanly reversed (e.g., a brownfield schema change already partially applied) — distinguished explicitly in `data-model.md`'s `Decision.decision_type` and Scenario B's negative acceptance scenario.
- **Safe-stop**: cross-cutting terminal-for-the-path state (see state machine); exits only via explicit human action.
- **Resumption**: workflow state persisted in SQLite; on restart, engine resumes at `WorkflowInstance.current_stage` (FR-ORC-011).
- **Partial failure / dependency unavailability**: SQLite unavailable → FR-SVC-010 defined error outcome, no silent data loss; a single failing parallel branch (N10/N11/N12) blocks only the join, not unrelated in-flight workflows for other `run_id`s.

## Observability and Metrics

**Evidence sources**: structured JSON logs (stdout, tagged with `run_id`) as the operational view; the persisted `AuditEvent`/`Decision`/`PolicyCheckResult` tables as the durable, queryable source of truth (NFR-006 — evidence must not depend on log retention or process memory).

**Demonstration metrics** (computed from the persisted tables; labeled as demonstration-scale per NFR-011/FR-ORC-020, never presented as production statistics):

- Workflow success rate = completed (N14 reached with overall PASS) ÷ total workflows started.
- Failure rate = workflows reaching SAFE_STOP or a FAIL release-readiness outcome ÷ total workflows started.
- Retry frequency = count of `retry_attempted` audit events ÷ total node executions.
- Rollback/compensation frequency = count of `decision_type` in {rollback, compensation}-tagged decisions ÷ total workflows.
- End-to-end latency = `N14.completed_at - N1.created_at` per workflow.

**Mean Time to Recovery (MTTR)**:

```
MTTR = Total recovery duration across recovered failure events ÷ Number of recovered failure events
```

Captured per recovered failure: `failure_detected_at`, `recovery_start_at`, `recovery_complete_at`, `recovery_duration = recovery_complete_at - recovery_start_at`, `recovery_mechanism` (retry / fallback / human intervention), `recovered: true`. Unrecovered failures (terminal SAFE_STOP with no subsequent human-resolved recovery within the run) are **excluded from the MTTR denominator** and reported separately as an `unrecovered_failure_count`, per the doc's explicit instruction not to blend the two. Measurement population, exclusions, and demonstration-data limitations (small sample size, synthetic test-injected failures rather than organic production incidents) MUST be stated alongside any reported MTTR figure.

## Security

- **Input validation**: all API request bodies validated via Pydantic models; URL scheme allowlist (`http`, `https` only) enforced in `src/domain/validation.py` (FR-SVC-002, NFR-001).
- **Malicious redirect / internal-address considerations**: reject target URLs resolving to loopback/link-local/private ranges at creation time (SSRF-adjacent hardening) — recorded as a domain validation rule, testable via `tests/unit/test_validation.py`.
- **Abuse cases**: short-code enumeration (guessing valid codes) is mitigated only by the Base62^7 keyspace size (~3.5 trillion); no additional anti-enumeration control is in scope for v1 (documented limitation, consistent with EXC-006's rate-limiting deferral).
- **Rate limiting**: not implemented in v1 (EXC-006); documented as a known, disclosed limitation.
- **Authentication assumptions**: none for the API surface (D-001); the orchestration's human-approval endpoints are assumed single-operator-trusted for this assessment (no auth layer built), which is itself a disclosed limitation for any future multi-user deployment.
- **Secrets management**: none required for v1 (no external service credentials); `src/config.py` fails fast on malformed configuration rather than falling back to an insecure default.
- **Dependency risk**: dependency manifest MUST be scanned (e.g., `pip-audit`) as part of N12 (Security & Risk Validation) and release-readiness (Constitution Principle V).
- **Audit integrity**: `AuditEvent` rows are append-only (no update/delete path exposed) to preserve audit trail integrity.
- **Least privilege / secure defaults**: single local SQLite file with restrictive filesystem permissions; no network exposure beyond localhost by default (`quickstart.md`).
- **Threat modeling summary**: primary threats in scope are malicious/malformed URL submission and short-code enumeration; out of scope for v1 are multi-tenant isolation breaches (EXC-001) and DDoS-class abuse (mitigated only by documented rate-limiting deferral).

## Compliance and Change Control

- **Policy domains applicable to this prototype**: security (URL/scheme validation, dependency scanning), architecture/change-control (this Plan/ADR/Constitution chain), audit-retention (indefinite for this prototype, per Clarifications), licensing (dependencies MUST be permissively licensed — verified at N12).
- **Versioned policy model**: each `PolicyCheckResult.policy_id` + `policy_version` pair is explicit; policy definitions live in `src/policy/checks.py` with a version constant bumped on any semantic change.
- **Policy evaluation inputs/outputs**: inputs = current code, dependency manifest, spec/plan/ADR state; outputs = `PolicyCheckResult` rows (PASS/FAIL/EXCEPTION_REQUESTED/NOT_APPLICABLE), per `data-model.md`.
- **Mandatory vs. advisory policies**: all eleven Constitution principles are mandatory for release-readiness; PVT-* proposed validation targets are advisory until human-approved, at which point they become mandatory NFR checks.
- **Compliance-check workflow stage**: N12 (evaluation) → N13 (aggregation + human release-readiness decision).
- **Change-request / exception workflow**: any change to an approved requirement/architecture/schema/policy triggers a recorded impact analysis (NFR-010) before it may affect an in-flight or future workflow; a `PolicyException` requires the fields defined in `data-model.md` and explicit human approval (FR-ORC-018).
- **Exception expiry**: enforced per `data-model.md`'s cross-entity invariant — an expired exception reverts its linked check to FAIL on next evaluation.
- **Policy audit-event structure**: `policy_check_evaluated` audit event per check, linked to the `PolicyCheckResult.result_id`.
- **Release-blocking condition**: demonstrated explicitly in Validation Scenario 6 (`quickstart.md`) — an injected FAIL with no exception yields overall FAIL, never a silent PASS (SC-006).
- **Upstream-change propagation**: handled by the REPLANNING cross-cutting state (`contracts/orchestration-state-machine.md`).

## Testing Plan

| Test category | Location | Maps to |
|---|---|---|
| Domain unit tests | `tests/unit/` | FR-SVC-001..011, code generation/validation/expiration rules |
| API contract tests | `tests/contract/` | `contracts/openapi.yaml`, `contracts/schemas/*.json` |
| Persistence tests | `tests/unit/` (repository-level) | FR-SVC-010, SQLite WAL behavior, collision retry |
| Integration tests | `tests/integration/` | quickstart.md scenarios 1, 4, 7 |
| Orchestration state-transition tests | `tests/orchestration/` | every node's allowed/prohibited transitions |
| Approval and rejection tests | `tests/orchestration/` | N5/N8/N13 approve and reject paths |
| Retry tests | `tests/orchestration/` | N2/N4b/N6/N7/N9 bounded-retry-with-backoff |
| Timeout tests | `tests/orchestration/` | N4/N5/N8/N13 24-hour timeout → SAFE_STOP (fast-forwarded clock, quickstart scenario 5) |
| Fallback tests | `tests/orchestration/` | N9 task-level bulkheading |
| Rollback/compensation tests | `tests/orchestration/` | Scenario B negative scenario (irreversible brownfield change) |
| Safe-stop tests | `tests/orchestration/` | quickstart scenario 5 |
| Resumption tests | `tests/orchestration/` | User Story 8, interrupted-restart simulation |
| Replanning tests | `tests/orchestration/` | User Story 9, upstream-artifact-change simulation |
| Concurrency tests | `tests/integration/` | FR-SVC-009, SC-010 (no duplicate active codes under load) |
| Security tests | `tests/unit/` + `tests/orchestration/` | NFR-001, N12 policy checks, disallowed-scheme rejection |
| End-to-end tests | `tests/integration/` | full quickstart.md walk-throughs |
| Release-readiness checks | `tests/orchestration/` | quickstart scenario 6, SC-006 |

Red-green-refactor is applied to all domain and orchestration behavior per Constitution Principle IV; task-level enforcement (write failing test first, verify failure reason, minimum implementation, refactor-while-green) is specified per task in Phase 2 (`/speckit-tasks`).

## Scenario Designs

### Greenfield (Scenario A / User Story 1)
- **Initial input**: "Add redirect_count and last_accessed_at to the short link detail response."
- **Requirement interpretation**: complete, consistent, testable, in-policy (extends existing `ShortLinkDetail` schema, already defined).
- **Decomposition**: single task — expose existing aggregation via the detail endpoint.
- **Orchestration path**: N1→N2→N3(greenfield)→N5→N6→N7→N8→N9→(N10‖N11‖N12)→N13→N14.
- **Approvals**: N5 (expedited, auto-qualified rationale), N8, N13.
- **Failure paths**: none expected; if N3 later finds a conflict (e.g., schema collision), suspends only that path per Scenario A's negative scenario.
- **Validation**: quickstart Scenario 2.
- **Generated evidence**: audit trail showing no `clarification_requested` event.
- **Expected terminal outcome**: `completed`, release-readiness PASS.

### Brownfield (Scenario B / User Story 2)
- **Initial input**: "Fix: redirect resolution returns 302 for expired short codes instead of 410."
- **Requirement interpretation**: defect correction against existing behavior (FR-SVC-005 already specifies 410-equivalent "expired" outcome — this scenario simulates a regression).
- **Decomposition**: fix redirect-resolution branch logic; add/verify regression test.
- **Orchestration path**: N1→N2→N3(brownfield)→N4b→N5→N6→N7→N8→N9→(N10‖N11‖N12)→N13→N14.
- **Approvals**: N5 reviews the N4b impact-analysis artifact explicitly, N8, N13.
- **Failure paths**: if impact analysis reveals a rollback-impossible consequence, routes to compensation classification per Scenario B's negative scenario.
- **Validation**: quickstart Scenario 4.
- **Generated evidence**: impact-analysis artifact enumerating all required categories.
- **Expected terminal outcome**: `completed`, existing regression suite passes.

### Ambiguous Requirement (Scenario C / User Story 3)
- **Initial input**: "Make links expire eventually."
- **Requirement interpretation**: incomplete (no duration) — fails the completeness quality check.
- **Decomposition**: blocked until clarified.
- **Orchestration path**: N1→N2→N3(ambiguous)→N4→(answered)→N2→N3(greenfield/brownfield, re-classified)→… (continues per resolved classification).
- **Approvals**: N4 clarification answer recorded with rationale; downstream gates as per resolved path.
- **Failure paths**: N4 timeout (24h) → SAFE_STOP with `reason=clarification_gate_timeout`.
- **Validation**: quickstart Scenario 3.
- **Generated evidence**: `clarification_requested` + `clarification_answered` audit events; spec-update record.
- **Expected terminal outcome**: either `completed` (after resolution) or `safe_stopped` (on timeout) — both are valid, evidenced terminal outcomes for this scenario's test suite.

## Technology Decisions (Structured)

Full rationale and rejected alternatives are in `research.md`; this table summarizes each material decision in the doc-mandated structure:

| # | Decision Question | Options | Criteria | Selected | Reversibility |
|---|---|---|---|---|---|
| 1 | Language/runtime? | Python 3.12, TypeScript/Node, Go | Stdlib richness, TDD tooling maturity, local-run simplicity | Python 3.12 | Low-moderate — a full rewrite; contracts (OpenAPI/JSON Schema) are language-agnostic and would survive a switch |
| 2 | API framework? | FastAPI, Flask, hand-rolled | Contract-from-code generation, schema/validation integration | FastAPI | Moderate — route/handler rewrite, but contracts stay stable |
| 3 | Persistence? | SQLite (embedded), Postgres (external), pure in-memory | No external infra (CON-002), real transactional/durability semantics | SQLite (WAL) | Moderate — repository layer is isolated (`src/persistence/`), swappable behind its interface |
| 4 | Orchestration engine? | Custom-built, Temporal, Airflow, Prefect | No external infra, full inspectability, exact governance semantics | Custom-built | Low — this is the core differentiator; a swap to a third-party engine would be a major re-architecture |
| 5 | Testing stack? | pytest+jsonschema, Schemathesis, manual | Executable contract validation, dependency weight | pytest + FastAPI TestClient + jsonschema | High — easily swappable, no architectural coupling |
| 6 | Deployment/local execution? | Bare process, Docker Compose | No separate server process needed (SQLite) | Bare local process (Uvicorn) | High — Dockerfile can be added later as a brownfield enhancement |

## Traceability

```
Requirement (spec.md FR-*/NFR-*/US-*)
  → Scenario (Greenfield/Brownfield/Ambiguous, above)
    → Design (contracts/orchestration-state-machine.md nodes, data-model.md entities)
      → ADR (docs/adr/*, next step)
        → Task (tasks.md, /speckit-tasks)
          → Code (src/*)
            → Test (tests/*, mapped in Testing Plan above)
              → Validation (quickstart.md scenarios)
                → Documentation (this plan, README, docs/*)
                  → Evidence (AuditEvent/Decision/PolicyCheckResult rows, per run_id)
```

Each layer carries the identifiers from the layer above it (e.g., a task references its FR-*/US-* IDs; a test references its task ID and, transitively, its requirement ID) — enforced structurally in Phase 2 (`/speckit-tasks`), not left as an informal convention.

## Delivery Sequence (Incremental Vertical Slices)

1. **Engineering baseline** — repo scaffolding, `src/` module skeleton, config, CI-equivalent local test runner wired up.
2. **Walking skeleton** — minimal FastAPI app + SQLite connection + `/healthz`, proving the deployable shape end-to-end before any real logic.
3. **Core URL behavior** — FR-SVC-001..011 fully implemented and tested (short-link creation, redirect, validation, idempotency, analytics).
4. **Orchestration state model** — N1-N14 graph + engine + persistence, without human gates wired to real waiting yet (approvals mocked/synchronous for this slice).
5. **Approval governance** — real human-gate wait/timeout/escalation behavior (24h, SAFE_STOP), Decision/AuditEvent recording.
6. **Reliability controls** — retry/backoff, fallback, rollback/compensation, resumption, replanning wired into the engine.
7. **Observability** — structured logging, audit-trail query endpoint, MTTR/success-rate computation.
8. **Three scenarios** — Greenfield/Brownfield/Ambiguous demonstrated end-to-end with generated evidence (quickstart scenarios 2-4).
9. **Release readiness** — policy checks (N12), release-readiness aggregation (N13), final engineering summary (N14), full quickstart suite green.

## Planning Constraints

- **Timebox**: 2–3 days total for the assessment. Slices 1-3 (baseline through core URL behavior) are the must-have floor for day 1; slices 4-6 (orchestration + governance + reliability) are the must-have floor for day 2, since they are the assessment's central differentiator; slices 7-9 (observability polish, all three scenarios demonstrated, release-readiness) complete by day 3.
- **Scope-control checkpoint**: if by end of day 2 the orchestration engine (slices 4-6) is not functioning with at least the Greenfield scenario passing end-to-end, all further URL-shortener domain enhancement work (e.g., richer analytics) is deferred to backlog — the orchestration system is the assessed differentiator, not the CRUD API.
- **Backlog (explicitly deferred, non-essential)**: rate limiting implementation (EXC-006), advanced analytics (EXC-002), web UI (EXC-003), multi-tenant support (EXC-001), HA/multi-region (EXC-004), Dockerfile/containerization.
- **Stop condition**: if a mandatory Constitution principle cannot be demonstrated within the timebox (e.g., genuine parallel fan-out proves infeasible), this MUST be disclosed as a residual limitation in the Final Engineering Summary (N14) — it MUST NOT be silently dropped or misrepresented as complete.
- **Minimum defensible release-readiness outcome**: all three required scenarios (A/B/C) demonstrated with generated evidence, all mandatory Constitution-derived policy checks evaluated (PASS or disclosed FAIL/exception), full audit trail reconstructable for at least one complete run of each scenario.
- Complexity discipline: no additional distributed-system components beyond the single local process + embedded SQLite described in Project Structure; production-grade *discipline* (TDD, audit trails, policy gates) is the target, not production-*scale* infrastructure.
