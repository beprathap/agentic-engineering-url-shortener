# ADR-010: Observability and Audit Model

## Status
Accepted (Human Gate 4, 2026-09-24)

## Context
Constitution Principle IX requires a correlation/run identifier per execution, recorded state transitions/decisions/approvals/retries/failures/replanning events, and audit evidence with actor type, action, timestamp, affected artifact/state, result, and reason, sufficient to reconstruct any execution (User Story 6). Demonstration metrics must be clearly distinguished from production measurements (FR-ORC-020).

## Decision Drivers
- Audit evidence must be durable and queryable after the fact, not only in-memory or log-only (NFR-006).
- Must support MTTR and other reliability metrics without conflating recovered and unrecovered failures.
- Must not require external telemetry infrastructure (CON-002).

## Options Considered

**Option A — Persisted, append-only `AuditEvent` table as source of truth; structured JSON stdout logs as a secondary operational view; metrics computed on-demand by querying persisted tables** — SELECTED
- Advantages: No external telemetry backend required; audit evidence survives process restarts and is directly queryable (`v1/workflows/{run_id}/audit`); metrics are always derivable from the same evidence a reviewer can independently inspect (no separate, potentially inconsistent metrics pipeline).
- Disadvantages: No real-time dashboarding without building a small query/reporting layer.
- Risks: Table growth over a long-running demonstration; acceptable given indefinite retention was explicitly confirmed for this prototype.
- Implementation impact: Low — `AuditEvent` repository plus a handful of aggregate queries for the metrics in the Plan's Observability section.
- Assessment implications: A reviewer can independently query the same evidence store rather than trusting a rendered dashboard.

**Option B — OpenTelemetry SDK + external collector (e.g., Jaeger/Prometheus)**
- Advantages: Production-grade, industry-standard tooling.
- Disadvantages: Requires running an external collector/backend — contradicts CON-002; adds setup friction disproportionate to the assessment's local-demonstration scope.
- Risks: Reviewer must additionally stand up telemetry infrastructure just to see evidence that the persisted audit trail already provides.
- Assessment implications: Rejected as unnecessary infrastructure for this scope.

## Decision
Adopt Option A. `AuditEvent`, `Decision`, and `PolicyCheckResult` (all in `data-model.md`) are the durable source of truth; structured JSON logs (tagged with `run_id`) are a secondary, human-readable operational view; metrics (success rate, failure rate, retry frequency, rollback/compensation frequency, MTTR, end-to-end latency) are computed via SQL aggregate queries against the persisted tables, exposed for inspection, and explicitly labeled as demonstration-scale (FR-ORC-020).

## Rationale
Satisfies NFR-005/NFR-006/User Story 6 without requiring external infrastructure (CON-002), and keeps a single evidentiary source of truth that both the running system and an external reviewer query identically — reducing the risk of a metrics/evidence mismatch.

## Consequences
- **Positive**: Reviewer-independent verifiability; no external telemetry setup; MTTR and other metrics are transparent, re-derivable calculations, not opaque dashboard numbers.
- **Negative**: No real-time visualization out of the box (acceptable — this is a local assessment prototype, not an operated production service).
- **Operational**: Table growth is unbounded for this prototype (indefinite retention, confirmed); a production deployment would need a real retention/archival policy (disclosed limitation, NFR-006).
- **Testing**: Metrics computations are unit-testable against known, seeded `AuditEvent` fixtures (e.g., assert MTTR calculation excludes unrecovered failures from the denominator, per the Plan's Observability section).
- **Governance**: `AuditEvent` rows are append-only (no update/delete API) to preserve audit integrity (Plan §Security).

## Risks and Mitigations
- Risk: conflating recovered and unrecovered failures in MTTR, overstating reliability. Mitigation: explicit `recovered: true/false` flag per failure event; MTTR denominator strictly excludes `recovered: false` rows, with unrecovered count reported separately (Plan §Observability).
- Risk: demonstration metrics mistaken for production claims. Mitigation: FR-ORC-020 requires explicit labeling; enforced by including a `is_demonstration_data: true` marker on any computed metric surfaced to a human.

## Reversibility
High. The metrics-computation layer is a thin query layer over the persisted tables; it can be replaced or extended (e.g., exported to an external system later) without changing how evidence is captured.

## Traceability
- Requirements: NFR-005, NFR-006, FR-ORC-014, FR-ORC-020, User Story 6.
- Spec sections: Non-Functional Requirements, User Story 6, Success Criteria SC-001/SC-008.
- Plan sections: Observability and Metrics (MTTR formula), `data-model.md` (AuditEvent).
- Expected task identifiers: Delivery Sequence slice 7 (Observability).

## Validation
Verified by: `tests/orchestration/test_audit_reconstruction.py` (User Story 6's acceptance scenarios) and `tests/unit/test_mttr_calculation.py` asserting the MTTR formula correctly excludes unrecovered failures.
