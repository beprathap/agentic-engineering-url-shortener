"""Injectable time abstraction (Section 14 Independent Reviewer Gate correction, 2026-09-24).

Gate timeouts (24h, ADR-006) and retry backoff (ADR-007) must be testable
without real-time waiting. All orchestration code that needs "now" or "sleep"
goes through a Clock instance rather than calling datetime.now()/time.sleep()
directly, so tests can inject a FakeClock that fast-forwards.
"""

from __future__ import annotations

import time
from datetime import datetime, timedelta, timezone
from typing import Protocol


class Clock(Protocol):
    def now(self) -> datetime: ...
    def sleep(self, seconds: float) -> None: ...


class SystemClock:
    """Real wall-clock time, used in production."""

    def now(self) -> datetime:
        return datetime.now(timezone.utc)

    def sleep(self, seconds: float) -> None:
        time.sleep(seconds)


class FakeClock:
    """Test double: time only advances when explicitly told to (fast-forward)."""

    def __init__(self, start: datetime | None = None):
        self._now = start or datetime.now(timezone.utc)
        self.sleep_calls: list[float] = []

    def now(self) -> datetime:
        return self._now

    def sleep(self, seconds: float) -> None:
        self.sleep_calls.append(seconds)
        self.advance(seconds)

    def advance(self, seconds: float) -> None:
        self._now += timedelta(seconds=seconds)

    def advance_hours(self, hours: float) -> None:
        self.advance(hours * 3600)
