# ADR-006: Human Approval Model — Single Operator, Recorded Role-Capacity, 24-Hour Gate Timeout

## Status
Accepted (Human Gate 4, 2026-09-24) (core parameters already confirmed by human: D-002 role model, 24-hour timeout via `/speckit-clarify`)

## Context
Constitution Principle III requires humans to retain ownership of requirements, architecture, security-sensitive decisions, exceptions, destructive changes, and release readiness, with defined approval/rejection/escalation/timeout behavior and no silence-as-approval. D-002 confirmed a single human operator performs all governance roles; clarification confirmed a 24-hour gate timeout.

## Decision Drivers
- Must never interpret silence as approval (FR-ORC-006).
- Must record which capacity/role an approval was made under, without enforcing separation-of-duties between distinct people (D-002).
- Must have a concrete, testable timeout (AMB-004, resolved).

## Options Considered

**Option A — Single operator, multiple recorded capacities, 24h timeout → SAFE_STOP** — SELECTED
- Advantages: Matches the confirmed human decisions exactly; simple to implement (no auth/identity system needed beyond a role-capacity string per decision); timeout is short enough to demonstrate in tests (via clock fast-forwarding) yet realistic for a single-operator working day.
- Disadvantages: No real separation-of-duties enforcement (explicitly out of scope, EXC-005).
- Risks: None material — this is a confirmed scoping decision, not an open design question.
- Implementation impact: Low — `Decision.actor_role_capacity` field (`data-model.md`) plus a per-gate timeout timer.
- Assessment implications: Directly demonstrable within the assessment's single-operator context.

**Option B — Distinct simulated actor identities with enforced separation-of-duties**
- Advantages: Closer to a real multi-person organization.
- Disadvantages: Explicitly rejected in scoping (D-002); adds an identity/authorization system with no assessment benefit given the confirmed single-operator context.
- Risks: Scope creep within the 2-3 day timebox.
- Implementation impact: Materially higher.
- Assessment implications: Rejected per D-002.

## Decision
Implement gates as: (1) a `Decision` record capturing `actor_role_capacity` (`reviewer_approver`, `release_owner`, `assessment_reviewer`) for every approval/rejection; (2) a 24-hour wait timer per gate instance; (3) on timeout, transition to SAFE_STOP with the specific gate name as `reason`, never auto-advance.

## Rationale
Directly implements the human-confirmed D-002 and the clarified 24-hour timeout, satisfying Principle III's "silence is not approval" and "escalation/timeout must be defined" requirements with the minimum complexity the confirmed scope requires.

## Consequences
- **Positive**: Simple, directly traceable to confirmed human decisions; testable without needing to simulate multiple real users.
- **Negative**: Cannot demonstrate separation-of-duties enforcement (disclosed limitation, EXC-005).
- **Operational**: Gate timers must be checkable without requiring the process to stay alive continuously for 24h wall-clock time — implemented as a persisted `gate_opened_at` timestamp checked lazily on next inspection/tick, not an in-memory `sleep`.
- **Testing**: Timeout tests use a test-only clock override rather than waiting 24 real hours (quickstart Scenario 5).
- **Governance**: Any future move to Option B (enforced separation-of-duties) is a brownfield change with its own impact analysis, not a config flag.

## Risks and Mitigations
- Risk: a naive `sleep(24h)` implementation would be untestable and would block the process. Mitigation: gate timeout is checked lazily against a persisted timestamp, not via a blocking sleep.

## Reversibility
Moderate. The `Decision.actor_role_capacity` field already anticipates a multi-actor future; adding real identity/authorization later extends rather than replaces this model.

## Traceability
- Requirements: D-002, FR-ORC-005, FR-ORC-006, User Story 4, Confirmed Parameters (24h timeout).
- Spec sections: Scoping Decisions, Functional Requirements, Confirmed Parameters.
- Plan sections: Human-in-the-Loop Controls, `contracts/schemas/approval.schema.json`.
- Expected task identifiers: Delivery Sequence slice 5 (Approval governance).

## Validation
Verified by: `tests/orchestration/test_gate_timeout.py` (fast-forwarded clock) asserting SAFE_STOP on timeout with no response; `tests/orchestration/test_approval_recording.py` asserting `actor_role_capacity` is captured on every Decision.
