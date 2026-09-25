# ADR-007: Retry, Fallback, and Safe-Stop Policy

## Status
Accepted (Human Gate 4, 2026-09-24)

## Context
Constitution Principle VIII requires classified transient/permanent failures, bounded retries with backoff, defined fallback, and safe-stop when continuation is unsafe. FR-ORC-007..010 require this at the orchestration-node level.

## Decision Drivers
- Retries must be bounded (never infinite) and must distinguish transient from permanent failure.
- Fallback and safe-stop must be explicit, not implicit.
- Must be demonstrable in tests without requiring long real-world waits.

## Options Considered

**Option A — Fixed bounded retry (3 attempts) with exponential backoff (200ms base), per-node failure classification, explicit fallback table, SAFE_STOP as universal terminal-for-path state** — SELECTED
- Advantages: Simple, deterministic, easy to test (bounded iteration count); every node in `contracts/orchestration-state-machine.md` already declares its own classification/retry/fallback, so this ADR formalizes the shared policy they all reference.
- Disadvantages: A single fixed backoff curve may not be optimal for every node type (e.g., human-wait gates don't use it at all — they use the 24h timeout from ADR-006 instead).
- Risks: None material at this scale.
- Implementation impact: Low — one shared retry decorator/utility in `src/orchestration/engine.py`, parameterized per node where a node needs a different bound.
- Assessment implications: Directly testable (PVT-004 default: 3 attempts, 200ms exponential backoff).

**Option B — Per-node fully custom retry/backoff configuration with no shared default**
- Advantages: Maximum flexibility per node.
- Disadvantages: More configuration surface, harder to reason about consistently, higher risk of an under-specified node with undefined failure behavior (which Principle VIII explicitly prohibits).
- Risks: Inconsistency across 14 nodes; some node likely ends up with undefined behavior by omission.
- Implementation impact: Higher.
- Assessment implications: Rejected — a shared default with explicit per-node overrides (Option A) is safer against the "no stage may have undefined failure behavior" requirement.

## Decision
A shared default retry policy (max 3 attempts, exponential backoff from 200ms) applied to every node unless explicitly overridden (documented per-node in `contracts/orchestration-state-machine.md`); failure classification (transient vs. permanent) is a required, explicit field on every node's implementation — there is no "unclassified" failure path. Fallback is explicit per node (most: none, by design — see ADR-008 for why ambiguity/design defects have no safe fallback); SAFE_STOP is the universal terminal-for-path state entered whenever retries are exhausted with no fallback, or a permanent failure occurs with no fallback.

## Rationale
A shared default with documented per-node overrides satisfies Principle VIII's "no stage may have undefined failure behavior" more safely than a fully bespoke per-node scheme, while remaining simple enough to implement and test within the timebox.

## Consequences
- **Positive**: Predictable, testable failure behavior across the entire graph; no node can silently lack a defined failure response.
- **Negative**: A node needing genuinely different retry economics (e.g., a much longer backoff) must explicitly override the default, adding a small amount of per-node configuration.
- **Operational**: Retry attempts are recorded as `retry_attempted` audit events (feeds the Observability retry-frequency metric).
- **Testing**: Each node's retry/fallback/safe-stop behavior is unit-testable in isolation by injecting a transient or permanent failure and asserting the correct classification and terminal behavior.
- **Governance**: Changing the default retry policy is a plan-level change requiring re-evaluation of every node relying on the default (impact analysis, per NFR-010).

## Risks and Mitigations
- Risk: retries masking a genuine permanent failure by retrying something that will never succeed. Mitigation: strict transient/permanent classification per node, reviewed at design time (N7/N8), not inferred at runtime by "try again and see."

## Reversibility
High. The retry utility is a shared, isolated component (`src/orchestration/engine.py`); its parameters can be tuned without touching node logic.

## Traceability
- Requirements: FR-ORC-007, FR-ORC-008, FR-ORC-010, PVT-004, Constitution Principle VIII.
- Spec sections: Functional Requirements — Orchestration Domain, Proposed Validation Targets.
- Plan sections: Reliability Model, `contracts/orchestration-state-machine.md` (per-node retry/fallback/failure-classification).
- Expected task identifiers: Delivery Sequence slice 6 (Reliability controls).

## Validation
Verified by: `tests/orchestration/test_retry_policy.py` (bounded attempts, backoff timing), `tests/orchestration/test_safe_stop_on_exhausted_retry.py` (User Story 7 acceptance scenarios).
