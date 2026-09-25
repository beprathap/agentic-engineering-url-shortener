# Phase 0 Research: Agentic Software Engineering System: URL Shortener

**Status**: Technology selections below are ARCHITECTURE DECISIONS pending human approval at the ADR gate (doc-mandated Human Gate 4), per Constitution Principle III (technology selection is human-owned). They are proposed here with rationale and rejected alternatives, not silently finalized.

## Decision 1: Language and Runtime

- **Decision**: Python 3.12.
- **Rationale**: Rich standard library (`sqlite3`, `asyncio`, `json`, `uuid`) minimizes external dependencies, keeping the prototype locally runnable per CON-002/AS-002. Strong typing support (`dataclasses`, `typing`, `pydantic`) supports explicit schemas for FR-ORC-014's audit-event and state requirements. Mature, well-understood TDD tooling (`pytest`) satisfies Constitution Principle IV.
- **Alternatives considered**:
  - **TypeScript/Node.js**: Comparable ecosystem, but weaker built-in embedded-persistence story (would require an added dependency for SQLite access) and less mature native async DAG-orchestration patterns in the standard library.
  - **Go**: Excellent concurrency primitives (goroutines/channels map naturally to fan-out/synchronization, FR-ORC-015), but weaker rapid-iteration story for a specification-heavy assessment where documentation/schema generation speed matters, and a smaller ecosystem for OpenAPI-from-code generation.

## Decision 2: API Delivery Framework

- **Decision**: FastAPI (with Uvicorn as the ASGI server for local execution).
- **Rationale**: Generates an OpenAPI 3.x contract directly from typed request/response models, directly satisfying the spec's explicit, versioned API contract requirement without hand-maintaining a separate OpenAPI document that can drift from the implementation. Pydantic models double as the request/response/error schemas required by the spec.
- **Alternatives considered**:
  - **Flask**: Simpler, but does not generate an OpenAPI contract natively; would require a separate contract-maintenance step, risking spec/implementation drift (violates Constitution Principle X's "documentation must evolve with implementation").
  - **Hand-written OpenAPI + any framework**: Rejected because it creates two sources of truth that could silently diverge; FastAPI's contract-from-code approach makes the contract executable and always current.

## Decision 3: Persistence

- **Decision**: SQLite, file-backed, in WAL (write-ahead log) mode, accessed via Python's built-in `sqlite3` module (or a thin wrapper).
- **Rationale**: Satisfies D-003 (embedded/in-process store acceptable) and CON-002 (no external managed infrastructure). WAL mode provides real transactional guarantees and reasonable concurrent-read/single-writer behavior, which is sufficient to test FR-SVC-009 (concurrent request handling) and FR-SVC-010 (persistence-failure behavior, simulated via a locked/unavailable file or injected I/O error) without needing a real network-attached database.
- **Alternatives considered**:
  - **Pure in-memory dict with periodic snapshot**: Simpler, but weaker durability story and harder to demonstrate a genuine "persistence failure" scenario (FR-SVC-010) since there is no real I/O boundary to fail.
  - **PostgreSQL**: Rejected per D-003 — would require external managed infrastructure, contradicting AS-002/CON-002 and the "locally runnable" goal.

## Decision 4: Orchestration Engine Architecture

- **Decision**: A custom, lightweight, persisted DAG/state-machine executor built directly in this codebase (`src/orchestration/`), rather than adopting a third-party workflow engine (e.g., Temporal, Airflow, Prefect).
- **Rationale**: Constitution Principle II and spec constraint CON-003 require the orchestration to be more than a linear chain — an explicit dependency graph with real parallel/fan-out/synchronization, human approval gates, bounded retry, fallback, rollback/compensation, and safe-stop, all with audit-grade evidence. A custom, purpose-built engine keeps every one of these semantics directly inspectable and testable in the assessment's own codebase (supporting Assessment Reviewer traceability, User Story 6) rather than hidden inside a third-party engine's internals, which would also violate CON-002 (most production workflow engines require external infrastructure — a message broker, a server process, or a managed service).
- **Alternatives considered**:
  - **Temporal / Airflow / Prefect**: Powerful, battle-tested orchestration semantics, but all require external server/broker infrastructure, contradicting CON-002/AS-002, and would obscure — rather than demonstrate — the assessment's core differentiator (a governed, auditable, non-linear orchestration system built with engineering judgment).
  - **A simple linear pipeline of function calls**: Rejected outright — this is explicitly prohibited by CON-003 and would fail Constitution Principle II.
- **Complexity justification** (recorded per plan template's Complexity Tracking guidance): building a custom orchestration engine is more work than adopting a chain-of-function-calls approach, but the additional complexity is required by CON-003/Principle II, not optional — the "simpler alternative" (linear chaining) is the one thing the spec and constitution explicitly forbid.

## Decision 5: Testing Stack

- **Decision**: `pytest` for unit/integration/orchestration-transition tests; FastAPI's built-in `TestClient` (backed by `httpx`) for API-level and contract tests; `jsonschema` for validating requests/responses against the published JSON Schemas in `contracts/`.
- **Rationale**: Keeps the dependency footprint small (all are widely-used, well-maintained libraries with no external service requirements), while still providing genuinely executable contract validation (spec requirement: "executable contract validation") rather than just static schema documents.
- **Alternatives considered**:
  - **Schemathesis** (property-based OpenAPI contract testing): More powerful, but adds a heavier dependency and steeper learning curve than the assessment's scope requires; `jsonschema` + hand-written contract test cases is sufficient to demonstrate the required discipline.

## Decision 6: Target Platform and Deployment

- **Decision**: Single-node local execution (macOS/Linux), Python 3.12 + Uvicorn, no containerization required for the assessment (a `Dockerfile` MAY be added later as a brownfield enhancement but is not required for v1).
- **Rationale**: Matches AS-002 and CON-002 directly.
- **Alternatives considered**: Docker Compose local stack — rejected as unnecessary overhead given SQLite has no separate server process to orchestrate.

## Decision 7: Configuration and Telemetry

- **Decision**: Configuration via environment variables with typed defaults (a small `src/config.py` module), validated at startup (fail-fast if malformed). Telemetry via structured JSON logging to stdout (correlation/run-id included on every log line per NFR-005) plus the persisted `audit_events` table as the durable, queryable source of truth (audit evidence must not depend on log retention).
- **Rationale**: Avoids requiring an external telemetry backend (CON-002) while still satisfying NFR-005/NFR-006 (observability, auditability) via the persisted audit trail as primary evidence, with logs as a secondary/operational view.
- **Alternatives considered**: OpenTelemetry SDK with an external collector — rejected as unnecessary infrastructure for a local, single-node assessment prototype; the persisted audit trail already satisfies the reconstruction requirement (User Story 6) without it.

## Resolved Technical Context (feeds `plan.md`)

| Field | Value |
|---|---|
| Language/Version | Python 3.12 |
| Primary Dependencies | FastAPI, Uvicorn, Pydantic, pytest, httpx, jsonschema |
| Storage | SQLite (file-backed, WAL mode) |
| Testing | pytest, FastAPI TestClient, jsonschema-based contract validation |
| Target Platform | Local single-node (macOS/Linux) |
| Project Type | Web service (single project, modular internal structure) |
| Performance Goals | See spec PVT-002/PVT-003 (proposed, pending approval): ≥50 req/s, ≤100ms redirect latency at that scale |
| Constraints | No external managed infrastructure (CON-002); no caller auth (CON-004); embedded persistence only (D-003) |
| Scale/Scope | Single-tenant demonstration prototype; not designed for multi-tenant or high-availability scale (EXC-001, EXC-004) |

No `NEEDS CLARIFICATION` markers remain in the Technical Context — all resolved above, subject to human ADR approval at Gate 4.
