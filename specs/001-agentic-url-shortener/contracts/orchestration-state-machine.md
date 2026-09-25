# Agentic Orchestration Architecture: Runtime State Machine / DAG

This defines the **runtime orchestration engine** that the delivered system executes for each ingested requirement (FR-ORC-001..020). It is distinct from the SpecKit meta-process used to build this repository (Constitution's "Development Workflow and Quality Gates" section) — this document describes the software artifact being built, not the process building it.

## Graph Overview

```text
N1 Requirement Ingestion
  └─▶ N2 Requirement Normalization
        └─▶ N3 Ambiguity Detection & Classification
              ├─(ambiguous)──▶ N4 Human Clarification ──(answered)──▶ N2 (re-normalize) ─┐
              │                        └─(timeout, 24h)──▶ SAFE_STOP                     │
              ├─(brownfield)─▶ N4b Impact Analysis ──▶ N5 Human Approval Gate: Requirements
              └─(greenfield, quality checks pass)────────▶ N5 Human Approval Gate: Requirements
                                                                    │
                                                    (approve)◀──────┘  (reject)──▶ N6' Rejection Handling ──▶ N6/N3 (per rejection reason)
                                                                    ▼
                                                          N6 Task Decomposition
                                                                    ▼
                                                    N7 Architecture & Design  (parallel-capable: independent design sub-tasks fan out, join here)
                                                                    ▼
                                                  N8 Human Approval Gate: Architecture
                                                                    │
                                                    (approve)◀──────┘  (reject)──▶ N7 (redesign)
                                                                    ▼
                                                          N9 Implementation (TDD)
                                              (independent decomposed tasks fan out in parallel)
                                                                    ▼  (synchronization join)
                        ┌───────────────────────────────────────────┼───────────────────────────────────────────┐
                        ▼ (parallel)                                ▼ (parallel)                                 ▼ (parallel)
                 N10 Testing                                 N11 Documentation                     N12 Security & Risk Validation
                        └───────────────────────────────────────────┼───────────────────────────────────────────┘
                                                        (synchronization join)
                                                                    ▼
                                              N13 Release-Readiness Determination
                                                    │  (human gate: Release-Readiness)
                                        (PASS)◀─────┘  (FAIL / EXCEPTION-REQUESTED)──▶ escalation / SAFE_STOP / exception approval loop
                                                                    ▼
                                              N14 Final Engineering Summary
                                                                    ▼
                                                               COMPLETED

Cross-cutting (attachable to any node): RETRY → FALLBACK → ROLLBACK/COMPENSATION → SAFE_STOP
Cross-cutting (attachable to any node once entered): REPLANNING (triggered by upstream artifact change, FR-ORC-012)
```

## Node Definitions

Each node below is defined with: Purpose, Inputs, Outputs, Preconditions, Postconditions, Responsible Actor, Allowed Transitions, Prohibited Transitions, Timeout Behavior, Retry Policy, Failure Classification, Fallback Behavior, Audit Events.

---

### N1 — Requirement Ingestion
- **Purpose**: Accept raw requirement text and create the `WorkflowInstance` + `Requirement` records.
- **Inputs**: Raw requirement text (from API consumer / software engineer).
- **Outputs**: `Requirement.raw_input` persisted; `WorkflowInstance` created with `status=running`, `current_stage=N1`.
- **Preconditions**: None (entry point).
- **Postconditions**: A stable `run_id` and `requirement_id` exist and are returned to the caller.
- **Responsible Actor**: System.
- **Allowed Transitions**: → N2.
- **Prohibited Transitions**: → any node beyond N2 (no skipping normalization).
- **Timeout Behavior**: N/A (synchronous, in-process).
- **Retry Policy**: N/A (pure validation of non-empty input; malformed input is a permanent rejection, not a retryable condition).
- **Failure Classification**: Permanent — empty/malformed raw input → reject with `400`-equivalent outcome, no `WorkflowInstance` created.
- **Fallback Behavior**: None (nothing to fall back to before a workflow exists).
- **Audit Events**: `workflow_created`, `requirement_ingested`.

---

### N2 — Requirement Normalization
- **Purpose**: Transform raw input into a structured `normalized_description`.
- **Inputs**: `Requirement.raw_input` (or, on re-entry from N4, the raw input plus the recorded clarification answer).
- **Outputs**: `Requirement.normalized_description`.
- **Preconditions**: N1 complete, or re-entered from N4 with an accepted clarification.
- **Postconditions**: `normalized_description` is non-null.
- **Responsible Actor**: Agent (system-executed normalization logic).
- **Allowed Transitions**: → N3.
- **Prohibited Transitions**: → N5/N6/N7 directly (classification must run first).
- **Timeout Behavior**: Bounded compute timeout (implementation-level constant, e.g. a few seconds); exceeding it is classified as a transient failure.
- **Retry Policy**: Up to 2 bounded retries with backoff on transient failure (PVT-004 default: 3 attempts total, exponential backoff from 200ms, applies here as the reference default).
- **Failure Classification**: Transient (timeout, internal exception) → retry; Permanent (raw input cannot be parsed at all) → SAFE_STOP with reason recorded.
- **Fallback Behavior**: None defined for this node; retries exhausted → SAFE_STOP (this is the node used to demonstrate User Story 7's "no fallback defined" branch).
- **Audit Events**: `requirement_normalized`, `retry_attempted` (if applicable).

---

### N3 — Ambiguity Detection & Classification
- **Purpose**: Run requirement-quality checks (completeness, consistency, testability, in-policy) and classify the requirement as `greenfield`, `brownfield`, or `ambiguous`.
- **Inputs**: `Requirement.normalized_description`.
- **Outputs**: `Requirement.quality_check_results` (structured PASS/FAIL per check), `Requirement.classification`.
- **Preconditions**: N2 complete.
- **Postconditions**: `classification` is set; if `ambiguous`, at least one quality check is FAIL or a policy/architecture conflict was detected.
- **Responsible Actor**: System.
- **Allowed Transitions**: → N4 (if `ambiguous`); → N4b (if `brownfield`); → N5 (if `greenfield` and all quality checks PASS).
- **Prohibited Transitions**: → N5 directly when `ambiguous` (this is the specific transition Constitution Principle III and Scenario C forbid); → N6/N7/N9 from here under any circumstance.
- **Timeout Behavior**: Bounded compute timeout, same order as N2.
- **Retry Policy**: N/A — this is a deterministic evaluation over already-normalized text; a failure here is a defect in the check logic itself (permanent), not a transient condition.
- **Failure Classification**: Permanent (check-execution defect) → SAFE_STOP.
- **Fallback Behavior**: None.
- **Audit Events**: `quality_checks_recorded`, `classification_assigned`.

---

### N4 — Human Clarification *(conditional: entered only when classification = ambiguous, or when a later node raises a mid-workflow ambiguity per FR-ORC-004/User Story 3)*
- **Purpose**: Present a structured clarification request (question, impact, current assumption, owner, required decision point) to the human and record their answer.
- **Inputs**: The specific ambiguity/conflict detected (from N3, or from a downstream node that suspended its path).
- **Outputs**: `Decision(decision_type=clarification_answer)`, updated `Requirement`/affected artifact.
- **Preconditions**: An ambiguity has been detected and the affected path has been suspended.
- **Postconditions**: Either an answer is recorded and the affected path is marked ready to resume, or the gate has timed out.
- **Responsible Actor**: Human (`reviewer_approver` capacity, per D-002).
- **Allowed Transitions**: → N2 (re-normalize with the clarified input) on answer, for pre-decomposition ambiguity; → the specific suspended downstream node (re-entered with updated context) for a mid-workflow ambiguity (User Story 3's "resume at the correct state").
- **Prohibited Transitions**: → N5/N6/N7/N9 directly without first returning through the normal path re-evaluation for the affected scope.
- **Timeout Behavior**: 24 hours (confirmed parameter). On timeout, → SAFE_STOP with `reason=clarification_gate_timeout`, never auto-approved (FR-ORC-006, edge case).
- **Retry Policy**: N/A — this is a human-wait state, not a retryable system operation.
- **Failure Classification**: Timeout is treated as a terminal condition for this gate instance requiring human escalation, not a transient failure to silently retry.
- **Fallback Behavior**: None — by design, ambiguity has no safe default (this is the entire point of Constitution Principle III / Scenario C).
- **Audit Events**: `clarification_requested`, `clarification_answered` OR `clarification_timed_out`.

---

### N4b — Impact Analysis *(conditional: entered only when classification = brownfield)*
- **Purpose**: Identify impacted components, interfaces, data flows, tests, documentation, regression risks, and rollout/rollback considerations before any implementation is authorized (Scenario B).
- **Inputs**: `Requirement.normalized_description`, current repository state (existing modules/tests/docs).
- **Outputs**: Impact-analysis artifact (persisted, linked to `run_id`).
- **Preconditions**: N3 classified the requirement as `brownfield`.
- **Postconditions**: Impact-analysis artifact exists with all required categories populated (none may be silently omitted).
- **Responsible Actor**: Agent (drafts); the artifact is then reviewed by Human at N5.
- **Allowed Transitions**: → N5.
- **Prohibited Transitions**: → N6/N7/N9 directly, bypassing N5's human approval of this specific artifact.
- **Timeout Behavior**: Bounded compute timeout for the drafting step.
- **Retry Policy**: Up to 3 bounded retries with backoff on transient tool/analysis failure.
- **Failure Classification**: Transient (analysis tooling error) → retry; Permanent (cannot determine impact, e.g. missing repository context) → SAFE_STOP, since implementing a brownfield change without impact analysis is explicitly prohibited.
- **Fallback Behavior**: None — an incomplete impact analysis blocks progression rather than proceeding with partial information.
- **Audit Events**: `impact_analysis_drafted`.

---

### N5 — Human Approval Gate: Requirements
- **Purpose**: Mandatory human sign-off before decomposition begins. For a `greenfield` path with all quality checks PASS, this gate is expedited (the system pre-populates the approval rationale as "auto-qualified: passed completeness/consistency/testability/in-policy checks") but is still a real, recorded human action — this is what distinguishes "no artificial clarification gate" (skipped) from "no approval gate at all" (never skipped, per Constitution Principle III). For `brownfield`, the human reviews the N4b impact-analysis artifact directly.
- **Inputs**: Classification, quality-check results, and (for brownfield) the impact-analysis artifact.
- **Outputs**: `Decision(decision_type=approval|rejection)`.
- **Preconditions**: N3 (and N4b if brownfield, N4 if previously ambiguous) complete.
- **Postconditions**: An explicit, recorded human decision exists.
- **Responsible Actor**: Human (`reviewer_approver` capacity).
- **Allowed Transitions**: → N6 (on approval).
- **Prohibited Transitions**: → N6 on silence/timeout without an explicit approval decision (FR-ORC-006).
- **Timeout Behavior**: 24 hours → SAFE_STOP / escalation.
- **Retry Policy**: N/A (human-wait state).
- **Failure Classification**: N/A.
- **Fallback Behavior**: On rejection → rejection-handling state; returns to N3 (re-classification) or N4b (re-analysis) depending on the rejection reason recorded.
- **Audit Events**: `requirements_approval_requested`, `requirements_approved` OR `requirements_rejected` OR `requirements_gate_timed_out`.

---

### N6 — Task Decomposition
- **Purpose**: Decompose the approved requirement into a dependency-ordered set of implementation tasks.
- **Inputs**: Approved requirement (+ impact analysis, if brownfield).
- **Outputs**: Task list with explicit dependencies (which tasks can run in parallel vs. must be sequential).
- **Preconditions**: N5 approved.
- **Postconditions**: Task list is traceable to the originating `requirement_id`.
- **Responsible Actor**: Agent.
- **Allowed Transitions**: → N7.
- **Prohibited Transitions**: → N9 directly (design must occur first).
- **Timeout Behavior**: Bounded compute timeout.
- **Retry Policy**: Up to 3 bounded retries with backoff on transient failure.
- **Failure Classification**: Transient → retry; Permanent (cannot decompose — e.g. contradictory approved requirement slipped through) → SAFE_STOP and flag for human review (this indicates an upstream gate defect).
- **Fallback Behavior**: None.
- **Audit Events**: `tasks_decomposed`.

---

### N7 — Architecture & Design
- **Purpose**: Produce/update the technical design (API/schema deltas, orchestration deltas) for the approved, decomposed requirement. Independent design sub-tasks (e.g., API contract changes vs. persistence schema changes) MAY fan out in parallel and synchronize before this node completes.
- **Inputs**: Task list from N6.
- **Outputs**: Design/ADR artifact(s), updated contracts if applicable.
- **Preconditions**: N6 complete.
- **Postconditions**: Design artifact(s) exist and are internally consistent (fan-out branches reconciled at the join).
- **Responsible Actor**: Agent (drafts); reviewed by Human at N8.
- **Allowed Transitions**: → N8.
- **Prohibited Transitions**: → N9 without N8 approval.
- **Timeout Behavior**: Bounded compute timeout per parallel branch; the join waits for all branches or a branch-level timeout, whichever comes first.
- **Retry Policy**: Up to 3 bounded retries per branch.
- **Failure Classification**: Transient → retry that branch; Permanent → SAFE_STOP the whole node (a single unreconcilable branch blocks the join, consistent with "prevent unsafe implementation").
- **Fallback Behavior**: None.
- **Audit Events**: `design_drafted`, `design_branches_synchronized`.

---

### N8 — Human Approval Gate: Architecture
- **Purpose**: Mandatory human approval of the design/ADR before implementation. This is the gate that MUST still be satisfied even when N4 (clarification) was skipped (User Story 1, acceptance scenario 3).
- **Inputs**: Design/ADR artifact(s).
- **Outputs**: `Decision(decision_type=approval|rejection)`.
- **Preconditions**: N7 complete.
- **Postconditions**: Explicit recorded decision.
- **Responsible Actor**: Human (`reviewer_approver` capacity).
- **Allowed Transitions**: → N9 (on approval).
- **Prohibited Transitions**: → N9 on silence/timeout.
- **Timeout Behavior**: 24 hours → SAFE_STOP / escalation.
- **Retry Policy**: N/A.
- **Failure Classification**: N/A.
- **Fallback Behavior**: On rejection → N7 (redesign) with the rejection reason attached.
- **Audit Events**: `architecture_approval_requested`, `architecture_approved` OR `architecture_rejected` OR `architecture_gate_timed_out`.

---

### N9 — Implementation (TDD)
- **Purpose**: Execute red-green-refactor TDD for each decomposed task. Independent tasks (no shared dependency per N6's task graph) fan out and run in parallel; a synchronization join occurs before proceeding to N10/N11/N12.
- **Inputs**: Approved design (N8), task list (N6).
- **Outputs**: Source code + tests, one commit-worthy unit per task.
- **Preconditions**: N8 approved.
- **Postconditions**: Every task has a failing-then-passing test recorded (Constitution Principle IV); no task is marked done without an executed, passing test.
- **Responsible Actor**: Agent.
- **Allowed Transitions**: → N10 and N11 and N12 (parallel fan-out) once the implementation join completes.
- **Prohibited Transitions**: → N13 directly, skipping testing/documentation/security validation.
- **Timeout Behavior**: Per-task bounded timeout; a single stuck task does not block independent tasks from completing.
- **Retry Policy**: Up to 3 bounded retries per task on transient failure (e.g., flaky test infra).
- **Failure Classification**: Transient → retry the task; Permanent (test cannot be made to pass within retry budget) → that task enters SAFE_STOP for human triage without blocking unrelated parallel tasks (bulkheading).
- **Fallback Behavior**: None beyond retry; a permanently failing task blocks only its own dependents, not the whole workflow, unless it is on the critical path.
- **Audit Events**: `task_implementation_started`, `task_test_failed_expected` (red), `task_test_passed` (green), `task_refactored`, `task_implementation_completed`.

---

### N10 — Testing *(parallel with N11, N12)*
- **Purpose**: Execute the full test suite (unit, integration, contract, orchestration-transition, reliability, security, end-to-end) for the affected scope; for brownfield, also execute the existing regression suite for impacted components (User Story 2, acceptance scenario 3).
- **Inputs**: Implemented code from N9.
- **Outputs**: Test results (pass/fail per suite).
- **Preconditions**: N9 join complete.
- **Postconditions**: All required test categories have an executed result (not merely "generated").
- **Responsible Actor**: System.
- **Allowed Transitions**: → synchronization join before N13.
- **Prohibited Transitions**: → N13 directly bypassing the join with N11/N12.
- **Timeout Behavior**: Bounded suite-execution timeout.
- **Retry Policy**: Up to 2 retries for infra-flaky failures only (never to "retry until green" a genuine logic failure — that is a permanent failure).
- **Failure Classification**: Transient (infra flake) → retry; Permanent (genuine test failure) → blocks the join, routes to N9 for correction.
- **Fallback Behavior**: None.
- **Audit Events**: `test_suite_executed`, `test_suite_result_recorded`.

---

### N11 — Documentation *(parallel with N10, N12)*
- **Purpose**: Update documentation/traceability artifacts to reflect the implemented change.
- **Inputs**: Implemented code, design artifacts.
- **Outputs**: Updated docs, traceability links.
- **Preconditions**: N9 join complete.
- **Postconditions**: Documentation references the current implementation state (Constitution Principle X).
- **Responsible Actor**: Agent.
- **Allowed Transitions**: → synchronization join before N13.
- **Prohibited Transitions**: None beyond the standard join gating.
- **Timeout Behavior**: Bounded.
- **Retry Policy**: Up to 3 bounded retries.
- **Failure Classification**: Transient → retry; Permanent → blocks the join (documentation is mandatory, not optional, per Evidence-Based Completion).
- **Fallback Behavior**: None.
- **Audit Events**: `documentation_updated`.

---

### N12 — Security & Risk Validation *(parallel with N10, N11)*
- **Purpose**: Execute the versioned policy checks (security, compliance/change-control, applicable Constitution principles), producing a `PolicyCheckResult` per check.
- **Inputs**: Implemented code, design artifacts, dependency manifest.
- **Outputs**: `PolicyCheckResult` rows (PASS/FAIL/EXCEPTION_REQUESTED/NOT_APPLICABLE).
- **Preconditions**: N9 join complete.
- **Postconditions**: Every applicable policy has exactly one outcome recorded for this run.
- **Responsible Actor**: System.
- **Allowed Transitions**: → synchronization join before N13.
- **Prohibited Transitions**: None beyond standard join gating.
- **Timeout Behavior**: Bounded.
- **Retry Policy**: Up to 2 retries for transient scan-tool failures.
- **Failure Classification**: Transient → retry; Permanent (genuine FAIL) → recorded as FAIL, does not block the join itself (the FAIL is evaluated at N13, not here) — this node's job is to evaluate and record, not to gate.
- **Fallback Behavior**: None.
- **Audit Events**: `policy_check_evaluated` (one per policy).

---

### N13 — Release-Readiness Determination
- **Purpose**: Aggregate all `PolicyCheckResult`s and test outcomes into an overall release-readiness outcome; route to human for the final Release-Readiness gate.
- **Inputs**: N10/N11/N12 outputs (post-join).
- **Outputs**: Overall outcome (PASS/FAIL), `Decision(decision_type=approval|rejection)` from the release owner.
- **Preconditions**: N10, N11, N12 all complete (join satisfied).
- **Postconditions**: A recorded, human-approved release-readiness decision exists; if FAIL, the workflow does not proceed to N14 as "released" (it may still produce a summary documenting the FAIL, per FR-ORC-019).
- **Responsible Actor**: System computes the aggregate; Human (`release_owner` capacity) makes the final call, including on any `EXCEPTION_REQUESTED` items.
- **Allowed Transitions**: → N14 (regardless of PASS/FAIL — a FAIL still produces a summary documenting why).
- **Prohibited Transitions**: Silently treating an unresolved `EXCEPTION_REQUESTED` or expired exception as PASS (FR-ORC-017).
- **Timeout Behavior**: 24 hours on the human decision → SAFE_STOP / escalation.
- **Retry Policy**: N/A for the human decision; the aggregation computation itself may retry transiently (up to 2 attempts).
- **Failure Classification**: N/A.
- **Fallback Behavior**: On a FAIL the human does not except, the workflow proceeds to N14 with a FAIL outcome recorded — it does not loop back automatically; a new requirement (a brownfield fix) would be required to address the FAIL, preserving Constitution Principle VI's "must fail if a mandatory... policy remains violated."
- **Audit Events**: `release_readiness_evaluated`, `release_readiness_approved` OR `release_readiness_rejected` OR `release_readiness_gate_timed_out`.

---

### N14 — Final Engineering Summary
- **Purpose**: Produce the evidence-derived final summary artifact (FR-ORC-019) — generated from recorded decisions, test results, and policy outcomes, not freeform narrative.
- **Inputs**: All persisted `Decision`, `AuditEvent`, `PolicyCheckResult`, and test-result records for the run.
- **Outputs**: Final summary artifact linked to `run_id`.
- **Preconditions**: N13 complete (PASS or FAIL — both produce a summary).
- **Postconditions**: `WorkflowInstance.status` → `completed`.
- **Responsible Actor**: System.
- **Allowed Transitions**: → COMPLETED (terminal).
- **Prohibited Transitions**: None (terminal node).
- **Timeout Behavior**: Bounded compute timeout.
- **Retry Policy**: Up to 2 bounded retries.
- **Failure Classification**: Transient → retry; Permanent → SAFE_STOP (a workflow that cannot produce its own evidence summary is itself a reportable defect).
- **Fallback Behavior**: None.
- **Audit Events**: `final_summary_generated`, `workflow_completed`.

---

## Cross-Cutting States (Applicable to Any Node)

### SAFE_STOP
- **Purpose**: Terminal-for-the-path state entered when continuation would be unsafe (timeout exhaustion, permanent failure with no fallback, detected contradiction).
- **Postconditions**: Reason recorded; `WorkflowInstance.status = safe_stopped`; visible to human for resolution.
- **Exit**: Only via explicit human action (e.g., providing the missing clarification, approving an exception, or authorizing a new remediation requirement). Never auto-resumes.
- **Audit Events**: `safe_stop_entered` (with `reason`).

### REPLANNING (FR-ORC-012/013, User Story 9)
- **Trigger**: An upstream artifact (e.g., an approved N7 design) changes materially while downstream work (N9+) is in flight.
- **Behavior**: Downstream work depending on the changed artifact is suspended; the affected nodes are re-entered from the point of change (typically re-enters N7 → N8 → N9 for the affected scope only); the new plan MUST pass through the same approval gates as the original (N8 again).
- **Audit Events**: `dependency_staleness_detected`, `replanning_triggered`, `replanning_completed`.

### RESUMPTION (FR-ORC-011, User Story 8)
- **Trigger**: Orchestration process interruption (e.g., restart) while a `WorkflowInstance` is not in a terminal state.
- **Behavior**: On restart, the engine loads `WorkflowInstance.current_stage` and resumes at that node without re-executing already-completed, side-effecting steps within it.
- **Audit Events**: `workflow_interrupted` (best-effort, recorded on next successful heartbeat/read), `workflow_resumed`.

## Rejection Handling
Any Human Approval Gate rejection routes back to the producing node (N5 reject → N3/N4b re-entry; N8 reject → N7 re-entry; N13 reject/FAIL → N14 with FAIL recorded) with the rejection rationale attached as a `Decision` record, never to an undefined state.
