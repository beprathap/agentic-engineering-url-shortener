# ADR-004: Base62 7-Character Short-Code Generation with Collision Retry

## Status
Accepted (Human Gate 4, 2026-09-24) (parameter already confirmed by human via `/speckit-clarify`, 2026-09-24; this ADR formalizes the resulting architectural decision)

## Context
FR-SVC-003 requires short-code uniqueness among active links with automatic, caller-invisible collision resolution. The Clarifications session confirmed Base62, 7 characters, as the format.

## Decision Drivers
- Collision probability at demonstration scale must be low enough that FR-SVC-003's uniqueness guarantee holds in practice, but not so astronomically low that the collision-retry path (an explicit reliability behavior) can never be exercised in testing.
- URL length/shareability (shorter is more "shortener-like").
- No caller-visible collision errors (FR-SVC-003).

## Options Considered

**Option A — Base62, 7 characters (~3.5 trillion combinations)** — SELECTED
- Advantages: Standard for URL shorteners; case-sensitive Base62 needs no special URL encoding; large enough keyspace for the assessment while still small enough that a test can force a collision (e.g., by seeding known codes) to exercise the retry path deterministically.
- Disadvantages: Slightly longer than a 6-char code.
- Risks: None material at this scale.
- Implementation impact: Trivial — random 7-char Base62 generation + uniqueness check + retry loop.
- Assessment implications: Retry-on-collision behavior (a named reliability capability) is straightforward to test deterministically.

**Option B — Base62, 6 characters (~56 billion combinations)**
- Advantages: Marginally shorter URLs.
- Disadvantages: Materially higher collision probability at scale (though still low for a demo); no meaningful advantage for this assessment's purposes.
- Risks: None material.
- Implementation impact: Same as Option A.
- Assessment implications: Neutral; rejected only because Option A was the human-confirmed choice.

**Option C — Base32, 8 characters, case-insensitive**
- Advantages: Avoids visual ambiguity (0/O, 1/l).
- Disadvantages: Longer codes for a comparable collision-resistance level; case-insensitivity does not add value for a programmatically-generated (not human-typed) code.
- Risks: None material.
- Implementation impact: Marginally higher (need a restricted alphabet excluding ambiguous characters).
- Assessment implications: Rejected — no benefit for this domain where codes are generated, not manually transcribed.

## Decision
Base62 alphabet (`0-9`, `a-z`, `A-Z`), fixed length 7. Generation: cryptographically-uninteresting random selection (this is not a security token) with a uniqueness check against active `ShortLink` rows; on collision, regenerate and retry, bounded by the standard retry policy (ADR-007), never surfaced to the caller as an error.

## Rationale
Matches the human-confirmed clarification, is the de facto standard for URL shorteners, and provides a keyspace that is both practically collision-free at demonstration scale and small enough to deterministically test the collision-retry path by pre-seeding the keyspace in a test.

## Consequences
- **Positive**: Simple, standard, testable.
- **Negative**: None material at this scale.
- **Operational**: Uniqueness check requires an indexed lookup on `short_code` scoped to `status='active'` (per `data-model.md`).
- **Testing**: Collision path is tested by seeding a small artificial keyspace in a unit test (e.g., temporarily restricting the alphabet/length in a test double) rather than relying on chance.
- **Governance**: A future change to code length/alphabet is a brownfield change with its own impact analysis (does not require re-issuing existing codes, since old codes remain valid under the old format).

## Risks and Mitigations
- Risk: naive collision-retry implemented as an unbounded loop could hang under a pathological test. Mitigation: bounded retry (ADR-007) applies here too — collision retry has a maximum attempt count before escalating to SAFE_STOP-equivalent for that request (a request-level, not workflow-level, safe-stop — surfaced as a 503).

## Reversibility
High. Isolated to `src/domain/short_link.py`'s generation function; changing length/alphabet does not affect existing persisted codes.

## Traceability
- Requirements: FR-SVC-001, FR-SVC-003, edge case "collision race."
- Spec sections: Confirmed Parameters, Functional Requirements.
- Plan sections: Data Model (ShortLink), Testing Plan.
- Expected task identifiers: Delivery Sequence slice 3 (Core URL behavior).

## Validation
Verified by: `tests/unit/test_short_link.py` asserting format compliance (regex `^[0-9a-zA-Z]{7}$`) and a deterministic collision-injection test asserting retry-then-success without a caller-visible error.
