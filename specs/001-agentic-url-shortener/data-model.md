# Phase 1 Data Model: Agentic Software Engineering System: URL Shortener

Derived from `spec.md` Key Entities, extended with the field-level and state-transition detail needed for implementation and contract generation. All persistence is SQLite (Decision 3, `research.md`).

## Domain: URL Shortener

### ShortLink

| Field | Type | Constraints | Notes |
|---|---|---|---|
| `short_code` | string | PK; exactly 7 chars; Base62 alphabet `[0-9a-zA-Z]` | Unique among rows where `status = 'active'` (FR-SVC-003) |
| `target_url` | string | required; must have passed URL validation (FR-SVC-002) | No uniqueness constraint — same URL may back multiple codes (per Clarifications 2026-09-24) |
| `created_at` | timestamp (UTC) | required | |
| `expires_at` | timestamp (UTC) | nullable | If null at creation, default expiration (PVT-001, pending approval) is applied by domain logic, not stored as null in practice |
| `status` | enum: `active`, `expired`, `deleted` | required | `expired` is derived at read-time from `expires_at < now()` OR set explicitly; `deleted` reserved for future brownfield soft-delete feature (not in v1 scope) |
| `idempotency_key` | string | nullable; unique when present | Enables FR-SVC-008 |

**State transitions**: `active → expired` (time-based, read-time derived or a background sweep — implementation decision, not architecture-level); `active → deleted` (out of v1 scope, reserved). No transition reverses `expired → active`.

### RedirectEvent

| Field | Type | Constraints | Notes |
|---|---|---|---|
| `id` | integer/UUID | PK | |
| `short_code` | string | FK → ShortLink.short_code | |
| `occurred_at` | timestamp (UTC) | required | |
| `outcome` | enum: `redirected`, `not_found`, `expired` | required | Distinguishes the three redirect outcomes (FR-SVC-005, edge cases) |

**Aggregation**: redirect count and last-accessed timestamp (FR-SVC-007) are derived from `RedirectEvent` rows with `outcome = 'redirected'` for a given `short_code`, rather than stored as a separately-maintained mutable counter — this avoids a second source of truth that could drift from the event log, and keeps the analytics data itself part of the audit-friendly, append-only record.

## Domain: Agentic Orchestration

### Requirement

| Field | Type | Constraints | Notes |
|---|---|---|---|
| `requirement_id` | string (stable ID) | PK | Stable identifier per spec rule (bidirectional traceability) |
| `raw_input` | text | required | Verbatim ingested text |
| `normalized_description` | text | nullable until normalization stage completes | |
| `classification` | enum: `greenfield`, `brownfield`, `ambiguous` | nullable until classified | Set by the requirement-quality/ambiguity-detection stage (FR-ORC-003/004) |
| `quality_check_results` | JSON | nullable until checked | Structured record of each completeness/consistency/testability/in-policy check and its outcome |
| `created_at` | timestamp (UTC) | required | |

### WorkflowInstance

| Field | Type | Constraints | Notes |
|---|---|---|---|
| `run_id` | UUID | PK | FR-ORC-001; the correlation identifier referenced throughout NFR-005 |
| `requirement_id` | string | FK → Requirement | |
| `current_stage` | string | required | References a node ID in the orchestration graph (see `contracts/orchestration-state-machine.md`) |
| `status` | enum: `running`, `clarification_pending`, `approval_pending`, `rejected`, `retrying`, `replanning`, `safe_stopped`, `completed`, `failed` | required | |
| `created_at` | timestamp (UTC) | required | |
| `updated_at` | timestamp (UTC) | required | |

### Decision

| Field | Type | Constraints | Notes |
|---|---|---|---|
| `decision_id` | UUID | PK | |
| `run_id` | UUID | FK → WorkflowInstance | |
| `decision_type` | enum: `approval`, `rejection`, `clarification_answer`, `exception_approval` | required | |
| `actor_role_capacity` | string | required | e.g., `reviewer_approver`, `release_owner` — records WHICH hat the single human operator wore (D-002) |
| `rationale` | text | required | Human governance requires recorded rationale, not just a boolean |
| `created_at` | timestamp (UTC) | required | |

### AuditEvent

| Field | Type | Constraints | Notes |
|---|---|---|---|
| `event_id` | UUID | PK | |
| `run_id` | UUID | FK → WorkflowInstance | |
| `actor_type` | enum: `human`, `system`, `agent` | required | FR-ORC-014 |
| `action` | string | required | e.g., `stage_entered`, `stage_completed`, `retry_attempted`, `fallback_invoked`, `replanning_triggered` |
| `occurred_at` | timestamp (UTC) | required | |
| `affected_artifact` | string | nullable | e.g., a file path, a stage ID, a decision ID |
| `result` | string | required | e.g., `success`, `failure`, `pending` |
| `reason` | text | nullable | Required whenever `result != 'success'` |

**Retention**: indefinite for this prototype, no automatic purge (Clarifications 2026-09-24; NFR-006).

### PolicyCheckResult

| Field | Type | Constraints | Notes |
|---|---|---|---|
| `result_id` | UUID | PK | |
| `run_id` | UUID | FK → WorkflowInstance | |
| `policy_id` | string | required | |
| `policy_version` | string | required | FR-ORC-016 |
| `outcome` | enum: `PASS`, `FAIL`, `EXCEPTION_REQUESTED`, `NOT_APPLICABLE` | required | |
| `evaluated_at` | timestamp (UTC) | required | |
| `exception_id` | UUID | FK → PolicyException, nullable | |

### PolicyException

| Field | Type | Constraints | Notes |
|---|---|---|---|
| `exception_id` | UUID | PK | |
| `applicable_policy` | string | required | |
| `reason` | text | required | |
| `scope` | text | required | |
| `approving_authority` | string | required | Role-capacity of the approving human (D-002) |
| `compensating_control` | text | required | |
| `approved_at` | timestamp (UTC) | required | |
| `expires_at` | timestamp (UTC) | required | FR-ORC-018 — exceptions must have an expiry/review condition |

**Expiry enforcement**: a `PolicyCheckResult` referencing an `exception_id` whose `PolicyException.expires_at < now()` at evaluation time MUST be treated as `FAIL`, not `EXCEPTION_REQUESTED` (edge case: "policy exception expires without renewal").

## Cross-Entity Invariants

- Every `AuditEvent`, `Decision`, and `PolicyCheckResult` MUST reference a valid `run_id` — no orphaned governance records (supports FR-ORC-014, User Story 6).
- A `WorkflowInstance` MUST NOT transition its `status` to `completed` while any linked `PolicyCheckResult.outcome = 'FAIL'` exists without a non-expired `exception_id` (supports FR-ORC-017, SC-006).
- A `ShortLink.short_code` collision during generation MUST NOT be visible outside the persistence layer as an error to the API caller (FR-SVC-003) — it is retried internally.
