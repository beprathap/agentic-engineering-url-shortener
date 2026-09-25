# ADR-013: Anonymous URL-Shortener API with Single-Operator Orchestration Governance

## Status
Accepted (Human Gate 4, 2026-09-24) (confirmed by human via D-001/D-002 prior to specification drafting)

## Context
D-001 confirmed the URL-shortener API surface requires no caller authentication in v1; D-002 confirmed a single human operator performs all orchestration governance roles. This ADR formalizes the resulting authentication/authorization architecture (item 15 of the ADR-gate checklist).

## Decision Drivers
- Must match the confirmed human scoping decisions exactly (not re-litigate them).
- Must not silently add authentication complexity beyond confirmed scope.
- Must still record accountability for governance actions (role-capacity, not identity/authentication).

## Options Considered

**Option A — No authentication on `/v1/links`, `/{short_code}`, `/healthz`; no authentication layer on `/v1/workflows/*` either, but every governance action records a role-capacity string** — SELECTED
- Advantages: Matches D-001/D-002 exactly; avoids building an unused auth system; keeps the assessment's engineering effort focused on orchestration semantics rather than credential management.
- Disadvantages: Anyone with local network access to the running process can both use the URL shortener AND act as any governance role — acceptable only because this is a single-operator, local-only assessment prototype (explicitly disclosed limitation).
- Risks: Would be unsafe in any multi-user or internet-exposed deployment; must be clearly disclosed as out-of-scope for that context (EXC-005, D-001).
- Implementation impact: Minimal — no auth middleware needed at all for v1.
- Assessment implications: Keeps scope aligned with the confirmed decisions; reviewers should not read the absence of auth as an oversight — it is a recorded, deliberate scoping decision.

**Option B — API-key authentication for the URL-shortener surface; real user-identity authentication for governance actions**
- Advantages: More production-representative.
- Disadvantages: Explicitly rejected by D-001 (API auth) and unnecessary given D-002 (single operator) — would add unused complexity contradicting the confirmed scope.
- Assessment implications: Rejected — re-litigates decisions already made by the human at Human Gate 2/3.

## Decision
No authentication anywhere in v1. Accountability for governance actions is provided by the recorded `actor_role_capacity` field (ADR-006), not by an authentication/identity system.

## Rationale
This is a direct implementation of D-001 and D-002; introducing authentication would contradict decisions the human already made explicitly, and would consume timebox budget on infrastructure the assessment's scope does not call for.

## Consequences
- **Positive**: Zero implementation cost; keeps focus on the assessed differentiator (orchestration).
- **Negative**: Not safe for multi-user or internet-facing deployment — must be prominently disclosed in `README.md`/final engineering summary as a scope boundary, not silently omitted.
- **Operational**: No credential storage, no session management, no auth-related attack surface to secure (also reduces security scope correspondingly).
- **Testing**: No auth-bypass tests needed; tests instead assert that endpoints work without any credential (confirming the intended open-access behavior).
- **Governance**: Adding authentication later (e.g., for a real deployment) is a brownfield change (FR-ORC-012-triggering) with its own impact analysis — not a default anyone should silently add without going through governance.

## Risks and Mitigations
- Risk: a future maintainer deploys this prototype publicly without adding authentication first. Mitigation: explicit, prominent disclosure in README/final summary that this is unauthenticated by design for the assessment context only.

## Reversibility
Moderate. Adding authentication later touches `src/api/` (middleware) and would need a corresponding `Decision`/audit model extension for identity — an additive, not destructive, change.

## Traceability
- Requirements: D-001, D-002, CON-004, FR-SVC-012, EXC-005.
- Spec sections: Scoping Decisions, Constraints, Exclusions.
- Plan sections: Security, Human-in-the-Loop Controls.
- Expected task identifiers: Delivery Sequence slice 2-3 (Walking skeleton, Core URL behavior).

## Validation
Verified by: `tests/integration/` asserting all endpoints are reachable without any credential; README/final summary explicitly disclosing the no-auth scope boundary.
