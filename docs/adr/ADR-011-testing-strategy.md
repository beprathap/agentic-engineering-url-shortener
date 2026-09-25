# ADR-011: Testing Strategy — pytest, FastAPI TestClient, jsonschema Contract Validation, Mandatory TDD

## Status
Accepted (Human Gate 4, 2026-09-24)

## Context
Constitution Principle IV mandates red-green-refactor TDD across domain and orchestration behavior with unit, integration, API contract, orchestration-transition, reliability, security, and end-to-end coverage; task completion requires executed, passing validation, not merely generated code.

## Decision Drivers
- Must produce genuinely executable contract validation, not just a static document.
- Must minimize added dependencies (CON-002 spirit — keep the footprint small even though CON-002 is about infrastructure, not libraries, low dependency count reduces review burden).
- Must support the full breadth of test categories the constitution requires.

## Options Considered

**Option A — pytest + FastAPI `TestClient` (httpx-backed) + `jsonschema` for contract assertions** — SELECTED
- Advantages: `pytest` is the de facto Python testing standard with excellent fixture/parametrization support for the many scenario variations (greenfield/brownfield/ambiguous × retry/fallback/safe-stop); `TestClient` allows full API-level testing without a running server process; `jsonschema` validates responses directly against the same schemas published in `contracts/schemas/`, making the contract tests genuinely executable against the published contract rather than a hand-duplicated assertion set.
- Disadvantages: Contract tests must be hand-written per endpoint/scenario rather than auto-generated property tests.
- Risks: Hand-written contract tests could under-cover edge cases a property-based tool would find automatically.
- Implementation impact: Low — all three are lightweight, well-documented libraries.
- Assessment implications: Directly demonstrates TDD discipline (Principle IV) with a low-friction toolchain reviewers will recognize.

**Option B — Schemathesis (property-based OpenAPI contract testing)**
- Advantages: Automatically generates test cases from the OpenAPI spec, potentially finding edge cases hand-written tests miss.
- Disadvantages: Heavier dependency, steeper configuration, and less direct mapping from "this test" to "this functional requirement" — weakens the traceability chain (Plan §Traceability) that ties each test to a specific FR/US identifier.
- Risks: Property-based failures can be harder to map back to a specific spec requirement for traceability purposes.
- Implementation impact: Moderate additional setup.
- Assessment implications: Rejected for this assessment's traceability-first priorities, though noted as a reasonable production enhancement.

## Decision
Adopt Option A: `pytest` (with `pytest-asyncio` for the async orchestration engine), FastAPI `TestClient`, and `jsonschema` for contract validation against `contracts/openapi.yaml` (converted/asserted at the response level) and `contracts/schemas/*.json`.

## Rationale
Satisfies the constitution's full test-category breadth with a minimal, well-understood dependency set, and keeps a direct, traceable line from each test to a specific functional requirement or user story — a priority made explicit in the Plan's Traceability section.

## Consequences
- **Positive**: Every test in `tests/` maps to an identifiable FR/NFR/US/SC per the Testing Plan table; TDD discipline is directly observable in commit history (failing test committed before passing implementation, per Constitution Principle IV and the doc's Suggested Commit Progression).
- **Negative**: No automatic property-based edge-case discovery; edge-case coverage depends on the thoroughness of the Edge Cases section already enumerated in `spec.md`.
- **Operational**: Test suite runs entirely locally and fast (`pytest tests/`), no external services.
- **Testing**: This ADR is itself validated by the Testing Plan table in `plan.md`.
- **Governance**: Task completion (Constitution Principle XI) requires an executed, passing test per task — enforced at the `/speckit-tasks` and `/speckit-implement` stages, not just documented here.

## Risks and Mitigations
- Risk: hand-written contract tests drift from the OpenAPI contract over time. Mitigation: contract tests load the schema file directly at test time (not a copy-pasted inline schema), so a contract change without a corresponding implementation change fails the test immediately.

## Reversibility
High. Test tooling is fully decoupled from application architecture; swapping to Schemathesis or another tool later does not require touching `src/`.

## Traceability
- Requirements: Constitution Principle IV, NFR-009.
- Spec sections: Non-Functional Requirements (Testability).
- Plan sections: Testing Plan, Technology Decisions #5.
- Expected task identifiers: All Delivery Sequence slices (testing is cross-cutting, not a single slice).

## Validation
Verified by: presence of a red-green commit pair (failing test, then passing implementation) for each task in the eventual commit history, per the doc's Suggested Commit Progression; `tests/contract/` loading `contracts/openapi.yaml`/`contracts/schemas/*.json` directly rather than duplicating schema definitions inline.
