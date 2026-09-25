# ADR-014: Append-Only Event Log for Analytics Consistency

## Status
Accepted (Human Gate 4, 2026-09-24)

## Context
FR-SVC-007 requires basic redirect analytics (count, last-accessed); FR-SVC-009 requires concurrent creation/redirect requests not to produce inconsistent analytics counts. A representation must be chosen for how redirect analytics are stored and kept consistent under concurrency.

## Decision Drivers
- Must not produce inconsistent counts under concurrent redirect requests (FR-SVC-009, SC-010's spirit applied to analytics).
- Must support the three redirect outcomes distinctly (redirected/not_found/expired, FR-SVC-005).
- Should avoid a second, separately-maintained source of truth that could drift from the actual event history.

## Options Considered

**Option A — Append-only `RedirectEvent` log; redirect_count/last_accessed derived by aggregation query, not a separately incremented counter** — SELECTED
- Advantages: No read-modify-write race on a shared counter column (avoids the classic "lost update" concurrency bug); the event log itself is also useful audit/debugging evidence (which outcome occurred, when); single source of truth — no risk of the counter drifting from the actual event history.
- Disadvantages: Aggregation query cost grows with event volume for a given short code (acceptable at demonstration scale, PVT-002).
- Risks: None material at assessment scale.
- Implementation impact: Low — an `INSERT` per redirect request, a `COUNT`/`MAX` aggregate query for the detail endpoint.
- Assessment implications: Directly demonstrates a concurrency-safe design choice rather than requiring an explicit lock/transaction workaround for a shared counter.

**Option B — A mutable `redirect_count` column on `ShortLink`, incremented in place on each redirect**
- Advantages: O(1) read of the current count, no aggregation needed.
- Disadvantages: Requires careful transaction/locking discipline to avoid lost updates under concurrent increments (`UPDATE ... SET count = count + 1` is safe in SQLite within a single transaction, but combining it correctly with the outcome-distinction requirement (FR-SVC-005) and idempotency (FR-SVC-008) adds coupling between two concerns that Option A keeps naturally separate.
- Risks: A subtly incorrect increment implementation is a classic concurrency bug source — exactly the kind of thing FR-SVC-009 is designed to catch.
- Implementation impact: Slightly higher due to the need for explicit transactional care.
- Assessment implications: Viable, but Option A demonstrates the concurrency-safety property more directly and simply.

## Decision
Adopt Option A: analytics are derived from the append-only `RedirectEvent` log via aggregation, not from a separately-maintained mutable counter.

## Rationale
Avoids introducing a lost-update concurrency hazard for a value (redirect count) that can be correctly and simply derived from an append-only log that the system needs to maintain anyway (for outcome-distinction and audit purposes), directly supporting FR-SVC-009's concurrency-consistency requirement with less custom transactional logic than Option B.

## Consequences
- **Positive**: No custom locking/transaction logic needed for count consistency; the event log doubles as debugging/audit evidence for the URL-shortener domain (distinct from, but analogous to, the orchestration `AuditEvent` log).
- **Negative**: Aggregation cost scales with event volume per code; acceptable at PVT-002 demonstration scale, disclosed as a scaling consideration for a heavily-redirected code in a real production deployment.
- **Operational**: `RedirectEvent` table grows unboundedly (same indefinite-retention posture as orchestration audit evidence, per Clarifications 2026-09-24; AMB-006 — analytics retention after link expiry — remains open per the spec's deferred ambiguity).
- **Testing**: Concurrency test (FR-SVC-009, `tests/integration/`) fires concurrent redirect requests and asserts the aggregated count exactly matches the number of `redirected`-outcome requests.
- **Governance**: Consistent with the same append-only, evidence-oriented design principle used for orchestration `AuditEvent`s (ADR-010) — one architectural pattern applied twice, not two different philosophies.

## Risks and Mitigations
- Risk: aggregation query becomes a bottleneck for a very hot short code. Mitigation: out of scope at demonstration scale (PVT-002); an index on `RedirectEvent.short_code` keeps the aggregation efficient enough for the assessment's target load.

## Reversibility
High. Isolated to `src/persistence/short_links.py`'s analytics query; switching to a maintained counter later is an additive optimization, not a breaking change to the API contract (`ShortLinkDetail.redirect_count` stays the same field either way).

## Traceability
- Requirements: FR-SVC-005, FR-SVC-007, FR-SVC-009, SC-010 (adjacent).
- Spec sections: Functional Requirements — URL Shortener Domain, Key Entities (RedirectEvent).
- Plan sections: `data-model.md` (RedirectEvent aggregation note), Testing Plan (concurrency tests).
- Expected task identifiers: Delivery Sequence slice 3 (Core URL behavior).

## Validation
Verified by: `tests/integration/test_concurrent_redirects.py` asserting no lost updates under concurrent load; `tests/unit/test_analytics_aggregation.py` asserting count/last-accessed derivation correctness.
