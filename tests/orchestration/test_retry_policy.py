"""Unit test for the shared bounded-retry utility (FR-ORC-007, PVT-004, ADR-007)."""

import pytest


def test_retries_bounded_number_of_times_with_exponential_backoff():
    from src.orchestration.clock import FakeClock
    from src.orchestration.engine import retry_with_backoff

    clock = FakeClock()
    attempts = {"n": 0}

    def flaky():
        attempts["n"] += 1
        if attempts["n"] < 3:
            raise TimeoutError("transient")
        return "ok"

    result = retry_with_backoff(flaky, clock=clock, max_attempts=3, base_backoff_ms=200)

    assert result == "ok"
    assert attempts["n"] == 3
    # exponential backoff from 200ms: 200ms, 400ms (2 sleeps for 3 attempts)
    assert clock.sleep_calls == [0.2, 0.4]


def test_retry_exhausted_raises_the_last_exception():
    from src.orchestration.clock import FakeClock
    from src.orchestration.engine import retry_with_backoff

    clock = FakeClock()

    def always_fails():
        raise TimeoutError("still transient")

    with pytest.raises(TimeoutError):
        retry_with_backoff(always_fails, clock=clock, max_attempts=3, base_backoff_ms=200)
