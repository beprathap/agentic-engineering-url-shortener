# ADR-005: Custom-Built Orchestration Engine as an Explicit Code-Defined DAG

## Status
Accepted (Human Gate 4, 2026-09-24)

## Context
Constitution Principle II and spec constraint CON-003 require the orchestration to be more than a linear chain of agent calls: an explicit dependency graph or equivalent stateful model with sequential paths, parallel paths, synchronization, branching, dynamic replanning, interruption, and resumption (FR-ORC-001..015). This ADR also covers item 7 of the ADR-gate checklist (dependency graph representation), since the representation choice is inseparable from the engine architecture choice.

## Decision Drivers
- Must not be implementable as a linear chain (CON-003 — a hard constraint, not a preference).
- Must run locally without external infrastructure (CON-002).
- Must be fully inspectable/testable by an assessment reviewer (User Story 6).
- Must support genuine parallel fan-out with synchronization (FR-ORC-015).

## Options Considered

**Option A — Custom-built engine; nodes and edges defined as Python code (`src/orchestration/graph.py`), executed by a bespoke async executor**
- Approach: Each node (N1-N14, `contracts/orchestration-state-machine.md`) is a Python callable with declared preconditions/postconditions; a `DependencyGraph` object holds edges; an `Executor` walks the graph, running independent nodes concurrently via `asyncio.gather` and joining at declared synchronization points; state persisted to SQLite after every transition.
- Advantages: Every semantic required by Principle II (parallelism, branching, replanning, safe-stop) is directly implemented and inspectable in this codebase; no external infrastructure; full audit-event emission is under our control at every transition.
- Disadvantages: More implementation effort than adopting an existing library; must independently ensure correctness of retry/backoff/idempotency logic that a mature engine would provide out of the box.
- Risks: Reinventing workflow-engine correctness properties (e.g., exactly-once semantics under crash-and-resume) with less battle-testing than an established product.
- Implementation impact: Highest of the options, but bounded — the graph has a fixed, known 14 nodes plus cross-cutting states, not an open-ended workflow DSL.
- Assessment implications: Directly demonstrates the assessed capability (orchestration engineering judgment) rather than delegating it to a dependency.

**Option B — Adopt an existing workflow engine (Temporal, Airflow, Prefect)**
- Advantages: Battle-tested retry/idempotency/durability semantics; less code to write.
- Disadvantages: All three require external server/broker infrastructure (a Temporal server, an Airflow scheduler+metadata DB, a Prefect server/agent) — directly contradicts CON-002/AS-002's local-runnability-without-external-infrastructure requirement. Would also obscure the orchestration semantics being assessed inside the engine's internals rather than demonstrating engineering judgment in this codebase.
- Risks: Reviewer cannot inspect "how retries/fallback/safe-stop actually work" without reading the third-party engine's source, undermining the assessment's traceability goal.
- Implementation impact: Lower raw coding effort, but higher setup/operational complexity (a server process, possibly a message broker).
- Assessment implications: Rejected — directly conflicts with CON-002 and dilutes the demonstrated differentiator.

**Option C — A simple linear pipeline of sequential function calls, each stage calling the next**
- Advantages: Trivial to implement.
- Disadvantages: Explicitly prohibited by CON-003 and Constitution Principle II ("A linear sequence of agents is not sufficient evidence of orchestration"); cannot represent genuine parallel fan-out, branching, or replanning.
- Risks: Would fail the assessment's core evaluation criterion outright.
- Implementation impact: Lowest, but not a viable option.
- Assessment implications: Rejected outright — this is the one thing the spec and constitution explicitly forbid.

## Decision
Adopt Option A: a custom-built orchestration engine with nodes and edges declared as Python code in `src/orchestration/graph.py`, executed by an async executor (`src/orchestration/engine.py`) that supports concurrent execution of independent nodes with explicit synchronization joins, and persists `WorkflowInstance`/`AuditEvent` state after every transition (ADR-003).

## Rationale
This is the only option that simultaneously satisfies CON-003 (no linear chain), CON-002 (no external infrastructure), and the assessment's explicit goal of demonstrating orchestration engineering judgment directly and inspectably in the submitted codebase, rather than inside a third-party product.

## Consequences
- **Positive**: Every orchestration semantic (parallelism, branching, retry, fallback, rollback/compensation, safe-stop, resumption, replanning) is implemented, testable, and reviewable in this repository.
- **Negative**: More implementation effort than adopting a library; correctness of concurrency/crash-recovery logic is our responsibility to test thoroughly (Testing Plan, `tests/orchestration/`).
- **Operational**: No separate server process; the engine runs in-process with the API.
- **Testing**: Each node and each cross-cutting state (SAFE_STOP, REPLANNING, RESUMPTION) has dedicated transition tests (Testing Plan).
- **Governance**: This is the assessment's core differentiator; any change to the graph structure is itself a material architecture change requiring a new/amended ADR.

## Risks and Mitigations
- Risk: subtle concurrency bugs in the async executor (e.g., a race between two parallel nodes writing `WorkflowInstance.current_stage`). Mitigation: all state writes go through a single-writer SQLite connection per workflow instance, serializing writes for a given `run_id` even when nodes execute concurrently in-process.
- Risk: under-testing the resumption path (crash-and-restart) since it is harder to simulate than a normal happy path. Mitigation: explicit resumption test suite (User Story 8, Testing Plan) using a simulated interruption (kill the in-memory executor mid-node, restart from persisted state).

## Reversibility
Low. This is the architectural core of the deliverable; replacing it with a third-party engine would be a near-total rewrite of `src/orchestration/`. This low reversibility is accepted because it is also the assessment's central, non-negotiable requirement (CON-003) — there is no lower-commitment alternative that satisfies the constraint.

## Traceability
- Requirements: CON-002, CON-003, FR-ORC-001..020, Constitution Principle II.
- Spec sections: Constraints, Functional Requirements — Orchestration Domain, User Stories 1-9.
- Plan sections: Summary, Constitution Check, Project Structure, `contracts/orchestration-state-machine.md` (full node design).
- Expected task identifiers: Delivery Sequence slices 4-6 (orchestration state model, approval governance, reliability controls).

## Validation
Verified by: `tests/orchestration/` state-transition test suite covering every node's allowed/prohibited transitions; an explicit test asserting at least one genuine parallel fan-out (N9→N10/N11/N12) with a synchronization join (FR-ORC-015); quickstart Scenarios 2-4 demonstrating the three required requirement scenarios end-to-end.
