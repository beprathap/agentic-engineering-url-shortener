# ADR-008: Rollback vs. Compensation Semantics

## Status
Accepted (Human Gate 4, 2026-09-24)

## Context
Constitution Principle VIII and spec FR-ORC-009 require the system to distinguish rollback (reversing an operation with no lasting side effect) from compensation (offsetting an operation that cannot be cleanly reversed). Scenario B's negative acceptance scenario requires this distinction to be surfaced explicitly to the human when rollback is impossible.

## Decision Drivers
- Must be a real, inspectable distinction in the data model, not just prose.
- Must be surfaced to the human before an irreversible action proceeds (NFR-011).

## Options Considered

**Option A — Explicit `decision_type` values (`rollback` is implicit undo of an unapproved draft; `compensation` is an explicit `Decision` type requiring human approval of a compensating action)** — SELECTED
- Approach: Rollback = discarding not-yet-committed/not-yet-approved artifacts (e.g., an unapproved design draft at N7) — a pure undo with no external effect, performed automatically without a separate approval. Compensation = a recorded `Decision(decision_type=exception_approval` or a dedicated `compensation` action`)` for an already-committed, hard-to-reverse effect (e.g., a brownfield schema change already applied) — requires explicit human approval of the compensating action itself (e.g., a follow-up migration), not just approval to proceed.
- Advantages: Matches Scenario B's negative scenario directly; keeps the common case (rolling back an unapproved draft) cheap and automatic while making the rare, risky case (compensation) require explicit human sign-off.
- Disadvantages: Requires the design (N7) to correctly identify, before implementation, whether a given brownfield change is rollback-safe or compensation-required — an imperfect, judgment-based classification.
- Risks: Misclassifying a compensation-requiring change as simple rollback would understate its risk to the human.
- Implementation impact: N4b (Impact Analysis) is the node responsible for this classification, since it already produces "rollback/rollout considerations" per FR-ORC-009/Scenario B.
- Assessment implications: Directly demonstrable via Scenario B's negative acceptance scenario (irreversible schema change → compensation classification → human approval required).

**Option B — Treat all reversals uniformly as "rollback," with no distinct compensation concept**
- Advantages: Simpler.
- Disadvantages: Directly fails FR-ORC-009's explicit requirement to distinguish the two; would hide the risk of an irreversible change behind the same label used for a cheap, safe undo.
- Risks: Understates risk to the human, violating Principle III's informed-consent spirit.
- Assessment implications: Rejected — fails a stated functional requirement outright.

## Decision
Adopt Option A. N4b (Impact Analysis) classifies a brownfield change's reversibility; if compensation-required, N5's human-approval-gate presentation MUST explicitly surface this classification (not bury it in prose), and the resulting `Decision` record uses a `compensation`-flagged type requiring the human to approve the compensating action, not merely the change itself.

## Rationale
This is the only option that satisfies FR-ORC-009's explicit distinction requirement and Scenario B's negative acceptance scenario, which specifically tests that irreversible-consequence detection surfaces this distinction to the human rather than treating it as ordinary rollback.

## Consequences
- **Positive**: Risk-appropriate human attention — cheap undos don't require a special approval flow; expensive/irreversible changes get one.
- **Negative**: Adds a classification judgment to N4b that could be wrong; mitigated by requiring the human to review the classification itself at N5, not just the underlying change.
- **Operational**: `data-model.md`'s `Decision.decision_type` enum must include a way to represent compensation distinctly (an explicit value or a tagged `exception_approval`).
- **Testing**: Scenario B's negative acceptance scenario is the primary test vehicle.
- **Governance**: Any brownfield change classified as compensation-required is logged distinctly in audit evidence for reviewer visibility (User Story 6).

## Risks and Mitigations
- Risk: N4b under-classifies a change as simple rollback when it is actually compensation-required. Mitigation: N5's human review explicitly includes the reversibility classification as a required field the human must see, not an optional detail.

## Reversibility
High. This is a classification and data-modeling decision, isolated to N4b's output structure and N5's presentation; does not constrain the underlying engine architecture (ADR-005).

## Traceability
- Requirements: FR-ORC-009, Scenario B negative acceptance scenario.
- Spec sections: User Story 2 (negative scenario), Functional Requirements — Orchestration Domain.
- Plan sections: Reliability Model, Scenario Designs (Brownfield).
- Expected task identifiers: Delivery Sequence slice 6 (Reliability controls).

## Validation
Verified by: `tests/orchestration/test_rollback_vs_compensation.py` asserting an irreversible-change scenario produces a `compensation`-classified Decision requiring explicit human approval, distinct from a simple draft-discard rollback.
