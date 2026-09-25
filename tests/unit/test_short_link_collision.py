"""Unit tests for bounded collision-retry on short-code generation (FR-SVC-003, ADR-004)."""

import pytest


def test_collision_triggers_retry_then_succeeds_without_caller_visible_error():
    from src.domain.short_link import generate_unique_short_code

    taken = {"AAAAAAA"}  # force the first attempt(s) to collide

    call_count = {"n": 0}

    def is_taken(code: str) -> bool:
        call_count["n"] += 1
        if call_count["n"] == 1:
            return True  # force a collision on first attempt
        return code in taken

    code = generate_unique_short_code(is_taken, max_attempts=3)

    assert code not in taken
    assert call_count["n"] >= 2, "retry should have been attempted after the first collision"


def test_collision_retry_exhausted_raises_after_max_attempts():
    from src.domain.short_link import CollisionRetryExhausted, generate_unique_short_code

    def always_taken(code: str) -> bool:
        return True

    with pytest.raises(CollisionRetryExhausted):
        generate_unique_short_code(always_taken, max_attempts=3)
