# ADR-003: SQLite Embedded Persistence for Domain and Orchestration State

## Status
Accepted (Human Gate 4, 2026-09-24)

## Context
Both the URL-shortener domain (ShortLink, RedirectEvent) and the orchestration engine (WorkflowInstance, Decision, AuditEvent, PolicyCheckResult, PolicyException) require durable, transactional persistence. D-003 confirmed an in-process/embedded store is acceptable; CON-002 prohibits external managed infrastructure. This ADR also covers item 6 of the ADR-gate checklist (workflow state persistence specifically), since both domains share the same mechanism and durability guarantees.

## Decision Drivers
- Must not require external managed infrastructure (CON-002).
- Must support real transactional guarantees to test persistence-failure behavior (FR-SVC-010) meaningfully.
- Must support workflow resumption after process restart without data loss (FR-ORC-011, NFR-008).
- Must support reasonable concurrent read / bounded concurrent write behavior for FR-SVC-009.

## Options Considered

**Option A — SQLite, file-backed, WAL mode**
- Approach: A single `.db` file per environment; Write-Ahead Logging enabled for concurrent-read/single-writer semantics.
- Advantages: Zero external infrastructure; real ACID transactions; genuine I/O boundary to test failure injection against; built into Python's stdlib.
- Disadvantages: Single-writer bottleneck under heavy concurrent write load (acceptable at demonstration scale, PVT-002).
- Risks: WAL file growth if not checkpointed; mitigated by SQLite's automatic checkpointing.
- Implementation impact: Low — `sqlite3` stdlib module, thin repository wrapper.
- Assessment implications: A real, inspectable file reviewers can open directly to verify persisted evidence.

**Option B — Pure in-memory dict with periodic snapshot**
- Approach: All state in a Python dict, flushed to disk periodically.
- Advantages: Simplest possible implementation.
- Disadvantages: No real transactional boundary; a "persistence failure" test would have to be artificially simulated rather than exercising a genuine I/O path; risk of losing recent writes between snapshots on crash — directly undermines FR-ORC-011's resumption-without-data-loss requirement.
- Risks: Weakens the very reliability guarantees (Principle VIII) the assessment is meant to demonstrate.
- Implementation impact: Low, but weakens evidentiary value.
- Assessment implications: Reviewers would see a materially weaker durability story.

**Option C — PostgreSQL (external server)**
- Approach: Run a local Postgres instance.
- Advantages: Production-grade concurrency and durability.
- Disadvantages: Requires external managed infrastructure (even if "local," it's a separate server process to install/manage) — directly contradicts D-003/CON-002.
- Risks: Adds setup friction for reviewers reproducing the assessment.
- Implementation impact: Higher — connection pooling, migrations tooling.
- Assessment implications: Rejected per confirmed scoping decision D-003.

## Decision
Adopt Option A: SQLite (file-backed, WAL mode) for both domain and orchestration persistence, via a repository layer in `src/persistence/` (`short_links.py`, `orchestration_store.py`).

## Rationale
Directly satisfies D-003 and CON-002 while still providing genuine transactional semantics sufficient to test FR-SVC-010 (persistence failure) and FR-ORC-011 (resumption) meaningfully, unlike a pure in-memory approach.

## Consequences
- **Positive**: Zero external setup for reviewers; real, inspectable evidence file; genuine failure-injection surface (e.g., simulate a locked/read-only file).
- **Negative**: Single-writer concurrency ceiling; not representative of a horizontally-scaled production deployment (disclosed limitation, EXC-004).
- **Operational**: One file to back up; WAL mode requires the `-wal`/`-shm` sidecar files to be included in any manual copy operation.
- **Testing**: Repository layer is isolated behind an interface, enabling in-memory SQLite (`:memory:`) for fast unit tests and file-backed SQLite for integration/persistence-failure tests.
- **Governance**: A future move to Postgres is a brownfield change isolated to `src/persistence/`, not a full rewrite, because the domain/orchestration layers depend only on the repository interface.

## Risks and Mitigations
- Risk: WAL-mode write contention under concurrent load. Mitigation: acceptable at PVT-002 demonstration scale; documented as a scaling limitation.
- Risk: file corruption on abrupt process kill mid-write. Mitigation: SQLite's WAL journal is itself the recovery mechanism; tested via the resumption test suite (User Story 8).

## Reversibility
Moderate. The repository-interface isolation (Principle VII) means swapping the persistence backend does not require rewriting domain or orchestration logic — only `src/persistence/`.

## Traceability
- Requirements: D-003, CON-002, FR-SVC-010, FR-ORC-011, NFR-008.
- Spec sections: Scoping Decisions, Constraints, Functional Requirements (both domains), Non-Functional Requirements.
- Plan sections: Technical Context, Reliability Model, Technology Decisions #3.
- Expected task identifiers: Delivery Sequence slices 2-3 (Walking skeleton, Core URL behavior).

## Validation
Verified by: `tests/unit/` repository tests using `:memory:` SQLite; `tests/integration/` tests using a real file-backed database with injected I/O failures (e.g., a read-only file) asserting FR-SVC-010's defined error outcome; resumption tests (User Story 8) asserting state survives a simulated process restart.
