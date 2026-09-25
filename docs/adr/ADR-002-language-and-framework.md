# ADR-002: Python 3.12 with FastAPI as Language and API Framework

## Status
Accepted (Human Gate 4, 2026-09-24)

## Context
The spec requires an explicit, versioned API contract with executable contract validation, and the project constitution defers technology choice to this planning stage. A language and API-delivery framework must be selected that supports rapid, contract-accurate development within the 2–3 day timebox.

## Decision Drivers
- Contract-from-code generation to avoid a second, driftable source of truth (Constitution Principle X).
- Standard-library richness to minimize external dependencies (CON-002).
- TDD tooling maturity (Constitution Principle IV).
- Team/reviewer familiarity and readability for assessment review.

## Options Considered

**Option A — Python 3.12 + FastAPI**
- Approach: FastAPI generates OpenAPI 3.x directly from typed Pydantic request/response models.
- Advantages: Contract and implementation cannot drift (same source); rich stdlib (`sqlite3`, `asyncio`, `uuid`); mature `pytest` ecosystem.
- Disadvantages: Async programming model adds some complexity versus a synchronous framework.
- Risks: Team unfamiliarity with async FastAPI patterns could slow initial velocity.
- Implementation impact: Moderate learning curve, high leverage (contract generation "for free").
- Assessment implications: Reviewers can inspect `contracts/openapi.yaml` and trust it matches the running code, since it is generated from it.

**Option B — Python 3.12 + Flask**
- Approach: Hand-maintain a separate OpenAPI document alongside Flask routes.
- Advantages: Simpler synchronous mental model.
- Disadvantages: Two sources of truth (routes and contract) that can silently diverge — directly risks violating Principle X ("documentation must evolve with implementation").
- Risks: Contract drift discovered only at review time, not enforced by tooling.
- Implementation impact: Requires manual contract-sync discipline with no tooling backstop.
- Assessment implications: Weaker evidence that the contract reflects reality.

**Option C — TypeScript/Node.js + a framework (e.g., NestJS)**
- Approach: Similar contract-from-code approach available via decorators.
- Advantages: Comparable ecosystem maturity.
- Disadvantages: Weaker built-in embedded-persistence story (no equivalent to Python's stdlib `sqlite3`) and a heavier framework surface (NestJS) relative to the assessment's scope.
- Risks: More dependencies to justify individually.
- Implementation impact: Comparable to Option A but with less stdlib leverage.
- Assessment implications: Neutral; a reasonable alternative, not selected due to marginally higher dependency footprint.

## Decision
Adopt Option A: Python 3.12 with FastAPI (Uvicorn ASGI server), Pydantic for schemas.

## Rationale
FastAPI's contract-from-code generation directly satisfies the spec's explicit, versioned, executable-contract requirement without introducing a second source of truth, and Python's standard library keeps the dependency footprint minimal, supporting CON-002's no-external-infrastructure constraint and the 2–3 day timebox.

## Consequences
- **Positive**: OpenAPI contract always reflects the actual API surface; strong typing catches schema errors early.
- **Negative**: Async/await discipline required throughout `src/api/`; a bug in async handling (e.g., blocking the event loop with synchronous SQLite calls) is a real risk requiring care (mitigated by using SQLite in a thread pool or accepting synchronous-but-fast local I/O for this scale).
- **Operational**: Single Uvicorn process; no additional runtime beyond the Python interpreter.
- **Testing**: FastAPI's `TestClient` enables in-process contract tests without a running server.
- **Governance**: Locks in Python/FastAPI as the implementation language; a future change is a brownfield rewrite, not a config change.

## Risks and Mitigations
- Risk: blocking SQLite calls stall the async event loop under load. Mitigation: acceptable at the assessment's demonstration scale (PVT-002, ≤50 req/s); documented as a known scaling limitation, not hidden.

## Reversibility
Low-moderate. A language/framework change is a full rewrite of `src/api/` and touches most of the codebase, though `contracts/` (language-agnostic) would survive unchanged.

## Traceability
- Requirements: CON-001, API/schema deliverables, NFR-004.
- Spec sections: Constraints, Non-Functional Requirements.
- Plan sections: Technical Context, Technology Decisions #1-2.
- Expected task identifiers: Delivery Sequence slice 2 (Walking skeleton).

## Validation
Verified by: `contracts/openapi.yaml` being generated (not hand-written) from `src/api/` Pydantic models, and `tests/contract/` asserting API responses conform to the generated schema.
