# ADR-001: Modular Monolith Application Architecture

## Status
Accepted (Human Gate 4, 2026-09-24)

## Context
The system combines a URL-shortener API and a governed orchestration engine that must be locally runnable without external managed infrastructure (spec CON-002, AS-002) while keeping domain logic, API delivery, persistence, orchestration, policy enforcement, and telemetry separable (Constitution Principle VII). A choice is needed between a single deployable process with internal module separation, versus multiple independently deployable services (e.g., a separate "control plane" for orchestration).

## Decision Drivers
- Must run locally with no external managed infrastructure (CON-002).
- Must keep concerns separable and independently testable (Principle VII).
- Must avoid unjustified distributed-system complexity (Planning Constraints).
- 2–3 day assessment timebox.

## Options Considered

**Option A — Modular monolith (single process, internal module boundaries)**
- Approach: One deployable service; `src/domain`, `src/api`, `src/orchestration`, `src/policy`, `src/persistence`, `src/telemetry` as separate Python packages with explicit interfaces between them.
- Advantages: No network boundary to manage; trivially locally runnable; module boundaries still enforce separation of concerns and independent unit testing.
- Disadvantages: Domain and orchestration share a process and a database; a fault in one is not process-isolated from the other.
- Risks: Insufficiently strict internal discipline could let modules bleed into each other over time.
- Implementation impact: Simple deployment (`uvicorn src.api.app:app`); one SQLite file.
- Assessment implications: Keeps reviewer focus on the orchestration logic itself, not on distributed-systems plumbing.

**Option B — Separate control-plane and application-plane services**
- Approach: Orchestration engine as its own service communicating with the URL-shortener API over HTTP/queue.
- Advantages: Stronger process isolation; closer to a real multi-service production topology.
- Disadvantages: Requires inter-process communication, its own trust boundary, and likely an external broker or a second local server — contradicts CON-002/AS-002's "no external managed infrastructure" and "locally runnable" goals.
- Risks: Adds distributed-systems failure modes (network partition, message loss) that must then be handled, expanding scope beyond the 2–3 day timebox without clear assessment benefit.
- Implementation impact: Significantly higher — two deployables, an IPC contract, two test harnesses.
- Assessment implications: Risks displacing time from demonstrating orchestration semantics (the actual differentiator) into deployment plumbing.

## Decision
Adopt Option A: a modular monolith — one deployable process with strict internal module boundaries (`src/domain`, `src/api`, `src/orchestration`, `src/policy`, `src/persistence`, `src/telemetry`, `src/config`).

## Rationale
CON-002/AS-002 explicitly require local runnability without external managed infrastructure, and the Planning Constraints explicitly instruct avoiding unjustified distributed-system complexity within a 2–3 day timebox. A modular monolith satisfies Principle VII's separability requirement without paying the cost of a second deployable and an inter-process contract that the spec does not require.

## Consequences
- **Positive**: Simple to run and test end-to-end (`quickstart.md`); no network-boundary failure modes to model; fast iteration within the timebox.
- **Negative**: Domain and orchestration cannot fail independently at the process level; a crash affects both.
- **Operational**: Single log stream, single SQLite file to back up/inspect.
- **Testing**: Module boundaries are enforced by Python package structure and import discipline, verified by keeping cross-module dependencies one-directional (API → domain/orchestration, never the reverse).
- **Governance**: Any future decision to split into services is itself a material architecture change requiring a new ADR and Human Gate 4-equivalent approval.

## Risks and Mitigations
- Risk: module boundaries erode over time. Mitigation: `tests/unit/` structure mirrors `src/` module boundaries; a review checklist item flags any domain module importing from `src/api`.

## Reversibility
Moderate. Splitting into services later is a brownfield architectural change (its own governed workflow instance per FR-ORC-012), not a rewrite — module boundaries are already drawn as if they were service boundaries.

## Traceability
- Requirements: CON-002, AS-002, NFR-004 (Constitution Principle VII).
- Spec sections: Constraints, Non-Functional Requirements.
- Plan sections: Project Structure, Complexity Tracking.
- Expected task identifiers: Delivery Sequence slice 1 (Engineering baseline).

## Validation
Verified by: (1) the repository's actual directory structure matching this ADR's module list; (2) an import-direction lint/test asserting no reverse-dependency from domain/orchestration back into `src/api`.
