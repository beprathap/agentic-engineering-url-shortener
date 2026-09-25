# Brownfield Impact-Analysis Gate

*Produced without modifying code, from a live execution of the implemented system.*

## Change Impact Summary

**Current behavior**: `GET /{short_code}` returns `302` (redirect) for an active code and is expected to return `410` for an expired one (FR-SVC-005), per `src/api/links.py`.

**Requested behavior**: "Fix: redirect resolution currently returns 302 for expired short codes instead of 410." — a simulated regression against this already-correct behavior, used to exercise the brownfield path.

**Requirement identifiers**: FR-SVC-004, FR-SVC-005, User Story 2 (Scenario B).

## Dependency Map (drafted by N4b, `src/orchestration/nodes/n4b_impact_analysis.py`)

| Category | Finding |
|---|---|
| Impacted components | URL redirect resolution handler (`src/api/links.py`) |
| Impacted interfaces | `GET /{short_code}` response contract (410 vs 302) |
| Impacted data flows | `ShortLink.expires_at` read path at redirect time |
| Impacted tests | `tests/contract/test_redirect.py` expired-code scenarios |
| Impacted documentation | `contracts/openapi.yaml` redirect endpoint description |
| Regression risks | Existing active-link redirects must remain unaffected |
| Rollout/rollback considerations | Simple rollback: revert the code change, no persisted side effect |

**Security risks**: none material — no new input surface introduced.
**Reliability risks**: none — no new failure mode; existing 503-on-persistence-failure path (FR-SVC-010) unaffected.
**Data compatibility risks**: none — no schema change.
**Rollback vs. compensation** (ADR-008): classified **rollback** — no irreversibility marker (no schema change/migration/data loss language) detected in the requirement text; reverting the code change alone is sufficient.
**Architectural decisions affected**: none — no ADR revision required for this change.
**Downstream tasks requiring replanning**: none — this is a same-session fix, not a revision of an already-approved, in-flight design.

## Test-First Change Plan

`tests/contract/test_redirect.py::test_redirect_to_expired_short_code_returns_410_expired` already exists and passes against current code (T021/T022) — for a genuine regression, this test would be the one to re-run and would fail first, then the fix would be applied to make it pass again.

## Human Approval Requirement

Per FR-ORC-005/006, N5 blocks on an explicit recorded approval before N6. Confirmed live (see audit trail below): `requirements_approval_requested` (result=`pending`) is followed only after an explicit `requirements_approved` decision — no auto-advance.

## Live Execution Evidence (real run, not illustrative)

Captured by running the actual orchestration code (`src/orchestration/`) against a real SQLite database on 2026-09-25. Full run ID: `d7e778ea-ddcc-475a-98e1-608426c2d24e`.

```
AUDIT TRAIL:
  workflow_created                      (system, success)
  requirement_ingested                  (system, success)  -> N2
  requirement_normalized                (system, success)  -> N3
  quality_checks_recorded               (system, success)
  classification_assigned               (system, success)  -> brownfield
  impact_analysis_drafted               (agent,  success)  [full artifact JSON recorded]
  impact_analysis_ready_for_review      (system, success)  -> N5
  requirements_approval_requested       (system, pending)
  requirements_approved                 (human,  success)  -> N6   [Decision: reviewer_approver]
  tasks_decomposed                      (system, success)  -> N7
  design_drafted                        (agent,  success)
  design_branches_synchronized          (system, success)  -> N8
  architecture_approval_requested       (system, pending)
  architecture_approved                 (human,  success)  -> N9   [Decision: reviewer_approver]
  task_implementation_started           (agent,  success)
  task_implementation_completed         (agent,  success)
  test_suite_executed                   (system, success)
  documentation_updated                 (agent,  success)
  test_suite_result_recorded            (system, success)
  policy_check_evaluated x3             (system, success)  [no-auth-scope-confirmed, url-validation-present, audit-append-only]
  design_branches_synchronized          (system, success)  -> N10,N11,N12 joined
  parallel_validation_joined            (system, success)  -> N13
  release_readiness_evaluated           (system, success)  -> PASS
  release_readiness_recorded            (system, success)  -> N14   [Decision: release_owner]
  final_summary_generated               (system, success)
  workflow_completed                    (system, success)  -> N14, status=completed
```

**Critically**: no implementation-authorizing event (`tasks_decomposed`) occurs before `impact_analysis_drafted` and the explicit `requirements_approved` decision — confirmed by event ordering above, not by narrative claim. This is also asserted programmatically in `tests/integration/test_scenario_brownfield.py`.

**Reproduce**: `pytest tests/integration/test_scenario_brownfield.py -v`
