# ADR-009: Dynamic Replanning on Upstream Artifact Change

## Status
Accepted (Human Gate 4, 2026-09-24)

## Context
Constitution Principle II and FR-ORC-012/013 require detecting when an upstream artifact a downstream stage depends on has materially changed, suspending and re-planning affected downstream work, and preserving governance (re-triggering approvals) during replanning. User Story 9 is the demonstration vehicle.

## Decision Drivers
- Must detect staleness without manual polling by the human.
- Must not silently continue on stale assumptions.
- Must re-apply the same approval gates to replanned work (not a governance shortcut).

## Options Considered

**Option A — Version-stamped artifacts with dependency links; a change to a version-stamped artifact marks all downstream nodes that read it as stale, triggering suspension and re-entry** — SELECTED
- Approach: Every artifact an orchestration node produces (e.g., N7's design) carries a version number. Downstream nodes (N9) record which version of each upstream artifact they were built against. If N7 is later revised (new version), any downstream work still referencing the old version is marked stale and suspended; the engine re-enters N7→N8→N9 for the affected scope.
- Advantages: Deterministic, inspectable staleness detection; naturally re-applies the same gates (N8) since the affected scope literally re-enters the graph at that node.
- Disadvantages: Requires every artifact type to be versioned, adding minor bookkeeping.
- Risks: Over-triggering replanning on trivial/non-material artifact edits. Mitigation: only a version bump that the producing node explicitly marks as "material" (vs. a cosmetic edit) triggers downstream staleness.
- Implementation impact: Moderate — version fields on design/decomposition artifacts, a staleness-check step before N9 proceeds.
- Assessment implications: Directly matches User Story 9's acceptance scenarios (staleness detected, downstream suspended, same governance re-applied).

**Option B — No automatic detection; rely on the human to manually restart affected work**
- Advantages: Simplest possible implementation.
- Disadvantages: Directly fails FR-ORC-012's "system MUST detect" requirement — this is system-detected, not human-detected, per the spec.
- Risks: Silent continuation on stale assumptions, exactly what Constitution Principle II prohibits.
- Assessment implications: Rejected — fails a stated functional requirement.

## Decision
Adopt Option A: version-stamped artifacts with explicit "material vs. cosmetic" revision marking; downstream nodes record the upstream artifact version they depend on; a material revision triggers automatic staleness detection, suspension of affected downstream work, and re-entry through the same approval gates.

## Rationale
This is the only option that satisfies FR-ORC-012's system-detection requirement and FR-ORC-013's governance-preservation requirement simultaneously, and it reuses the existing graph re-entry mechanism (already required for N4's clarification resume and N5/N8 rejection handling) rather than inventing a separate replanning mechanism.

## Consequences
- **Positive**: Replanning reuses existing graph-transition machinery; no separate "replanning engine" needed.
- **Negative**: Requires disciplined material/cosmetic revision marking by whichever node produces a revisable artifact (mostly N7).
- **Operational**: `AuditEvent` gains `dependency_staleness_detected` / `replanning_triggered` / `replanning_completed` actions (already specified in `contracts/orchestration-state-machine.md`).
- **Testing**: User Story 9's acceptance scenarios are directly testable by revising an approved N7 artifact mid-flight and asserting downstream suspension + gate re-entry.
- **Governance**: Replanned work is indistinguishable, from a governance standpoint, from originally-planned work — it must pass N8 again, with no bypass.

## Risks and Mitigations
- Risk: material/cosmetic classification is itself a judgment call that could be gamed to avoid re-approval. Mitigation: the classification is made by the system based on a diff of specific tracked fields (e.g., API contract shape, schema fields), not a free-text judgment, for the fields that matter most in the API and schema change review process.

## Reversibility
Moderate. Isolated to `src/orchestration/replanning.py` and the artifact-versioning scheme; does not require changing the core executor (ADR-005).

## Traceability
- Requirements: FR-ORC-012, FR-ORC-013, User Story 9.
- Spec sections: User Story 9, Functional Requirements — Orchestration Domain.
- Plan sections: `contracts/orchestration-state-machine.md` (REPLANNING cross-cutting state).
- Expected task identifiers: Delivery Sequence slice 6 (Reliability controls).

## Validation
Verified by: `tests/orchestration/test_dynamic_replanning.py` implementing User Story 9's acceptance scenarios exactly (revise approved design mid-flight → downstream suspended → re-approval required before resuming).
