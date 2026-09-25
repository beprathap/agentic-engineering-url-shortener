"""Unit test: permanent-failure classification routes directly to safe-stop, no retry (NFR-002)."""

import pytest


class PermanentFailure(Exception):
    """Marker exception type classified as permanent (never retried)."""


def test_permanent_failure_is_not_retried():
    from src.orchestration.clock import FakeClock
    from src.orchestration.engine import classify_and_execute

    clock = FakeClock()
    attempts = {"n": 0}

    def fails_permanently():
        attempts["n"] += 1
        raise PermanentFailure("cannot be fixed by retrying")

    with pytest.raises(PermanentFailure):
        classify_and_execute(
            fails_permanently,
            clock=clock,
            permanent_exception_types=(PermanentFailure,),
            max_attempts=3,
        )

    assert attempts["n"] == 1, "permanent failure must not be retried"


def test_transient_failure_is_retried():
    from src.orchestration.clock import FakeClock
    from src.orchestration.engine import classify_and_execute

    clock = FakeClock()
    attempts = {"n": 0}

    def fails_then_succeeds():
        attempts["n"] += 1
        if attempts["n"] < 2:
            raise TimeoutError("transient")
        return "ok"

    result = classify_and_execute(
        fails_then_succeeds,
        clock=clock,
        permanent_exception_types=(PermanentFailure,),
        max_attempts=3,
    )

    assert result == "ok"
    assert attempts["n"] == 2
