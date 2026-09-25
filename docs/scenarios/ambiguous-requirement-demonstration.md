# Ambiguous Requirement Demonstration

*(doc §20 — the 17-item required evidence, from a live execution of the implemented system, run ID redacted per-run since `/tmp` scratch DBs are not retained; reproducible via the command at the bottom)*

1. **Original ambiguous input**: `"Make links expire eventually."`
2. **Detected ambiguity**: N3's quality checks flagged `testability: contains a vague/unquantified marker with no concrete criterion` (the word "eventually" matches a known vagueness marker with no duration attached).
3. **Classification and severity**: `ambiguous` — blocking (not merely advisory); the workflow cannot proceed to decomposition until resolved.
4. **Affected requirements/components**: FR-SVC-006 (default expiration policy) — the requirement doesn't specify what "eventually" means, and no default can be silently assumed per Constitution Principle III.
5. **Workflow state before detection**: `N3`, `status=running`.
6. **Transition to blocked state**: `status=clarification_pending`, `current_stage=N4` — confirmed live (`pending status: clarification_pending`).
7. **Reason implementation cannot safely continue**: recorded verbatim in the `clarification_requested` audit event's `reason` field: *"question='What is the intended expiration duration?'; impact='Cannot proceed to decomposition without a concrete duration'; current_assumption='none'; owner='human'"*.
8. **Human clarification request**: the structured request above — question, impact, current assumption, and owner, per FR-ORC-004's contract; not a freeform "please clarify."
9. **Recorded human decision**: a `Decision` row, `decision_type=clarification_answer`, `actor_role_capacity=reviewer_approver`, rationale = *"Default expiration is 90 days unless specified (PVT-001)."*
10. **Updated requirement/assumption**: the requirement's `normalized_description` was updated to *"Make links expire after 90 days by default unless a caller-specified expiration is provided"* — reflecting the clarified intent, tying back to the already-confirmed PVT-001 (90-day default).
11. **Downstream impact analysis**: re-running N3's classification against the clarified text yields `greenfield` (no vagueness marker remains) — confirmed live (`reclassification: greenfield`).
12. **Replanning event**: not applicable to this specific run (the ambiguity was caught before any downstream design/task artifact existed to become stale); User Story 9's dedicated replanning demonstration (`test_dynamic_replanning.py`) covers the case where staleness is detected *after* downstream work exists.
13. **Invalidated and regenerated artifacts**: the original `ambiguous` classification record is superseded by the new `greenfield` classification on the same `requirement_id` — not silently overwritten; both classification events remain in the audit trail (see below, two `classification_assigned` events).
14. **Resumed workflow state**: `current_stage=N2`, `status=running` immediately after the answer — confirmed live (`resumed stage: N2 status: running`) — i.e., resumed at N2 for re-normalization, not restarted from N1.
15. **Final validation**: the resumed, reclassified requirement proceeds through the standard N5 requirements gate (auto-qualified rationale, since it is now well-specified) and reaches `tasks_decomposed`.
16. **Audit trail**: full sequence below.
17. **Terminal outcome**: this demonstration run stops at `tasks_decomposed` (N6) intentionally, to isolate the ambiguity-to-resumption behavior being demonstrated; the full N1→N14 path for an equivalent well-specified requirement is separately demonstrated end-to-end in the Greenfield scenario.

## Live Execution Evidence (real run, not illustrative)

```
AUDIT TRAIL:
  workflow_created                (system, success)
  requirement_ingested            (system, success)
  requirement_normalized          (system, success)
  quality_checks_recorded         (system, success)
  classification_assigned         (system, success)   -> ambiguous
  clarification_requested         (system, pending)    reason: question/impact/current_assumption/owner (verbatim above)
  clarification_answered          (human,  success)    [Decision: clarification_answer, reviewer_approver]
  quality_checks_recorded         (system, success)    -- re-run after clarification
  classification_assigned         (system, success)   -> greenfield
  requirements_approval_requested (system, pending)     reason: auto-qualified (now well-specified)
  requirements_approved           (human,  success)    [Decision: approval, reviewer_approver]
  tasks_decomposed                (system, success)
```

**Rules honored, verified by this run, not merely asserted**:
- No default was silently assumed for "eventually" — the workflow entered `clarification_pending` and stayed there until an explicit human `Decision` was recorded.
- No auto-approval on timeout is exercised in *this* run (the answer was provided before any timeout check); the 24-hour timeout → SAFE_STOP path is a separate, dedicated test (`test_n4_clarification.py::test_clarification_gate_timeout_enters_safe_stop_never_auto_answers`), also passing.
- The workflow resumed at N2, not from N1 — confirmed by the absence of a second `requirement_ingested` event in the trail above.

**Reproduce**: `pytest tests/integration/test_scenario_ambiguous.py -v` (end-to-end, asserts the same event sequence programmatically) and `pytest tests/orchestration/test_n4_clarification.py -v` (isolates the timeout/no-auto-answer guarantee).
