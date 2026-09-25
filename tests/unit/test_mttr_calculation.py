"""Unit test: MTTR excludes unrecovered failures from its denominator (plan.md §Observability)."""


def test_mttr_excludes_unrecovered_failures_from_denominator():
    from datetime import datetime, timedelta, timezone

    from src.telemetry.metrics import RecoveryEvent, compute_mttr

    base = datetime(2026, 1, 1, tzinfo=timezone.utc)
    events = [
        RecoveryEvent(
            failure_detected_at=base,
            recovery_start_at=base,
            recovery_complete_at=base + timedelta(seconds=10),
            recovered=True,
        ),
        RecoveryEvent(
            failure_detected_at=base,
            recovery_start_at=base,
            recovery_complete_at=base + timedelta(seconds=30),
            recovered=True,
        ),
        RecoveryEvent(
            failure_detected_at=base,
            recovery_start_at=base,
            recovery_complete_at=None,
            recovered=False,  # unrecovered - must be excluded from MTTR
        ),
    ]

    result = compute_mttr(events)

    assert result.mttr_seconds == 20.0  # (10 + 30) / 2, NOT divided by 3
    assert result.recovered_count == 2
    assert result.unrecovered_count == 1


def test_mttr_with_no_recovered_events_returns_none_not_zero():
    from src.telemetry.metrics import RecoveryEvent, compute_mttr
    from datetime import datetime, timezone

    events = [
        RecoveryEvent(
            failure_detected_at=datetime.now(timezone.utc),
            recovery_start_at=datetime.now(timezone.utc),
            recovery_complete_at=None,
            recovered=False,
        ),
    ]

    result = compute_mttr(events)

    assert result.mttr_seconds is None, "MTTR must be undefined (not 0) with zero recovered events"
    assert result.unrecovered_count == 1
