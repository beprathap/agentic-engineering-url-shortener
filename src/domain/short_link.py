"""URL-shortener domain logic: short-code generation and collision retry (ADR-004)."""

from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone
from typing import Callable

_ALPHABET = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"


def generate_short_code(length: int = 7) -> str:
    """Generate a random Base62 short code of the given length (default 7, per ADR-004)."""
    return "".join(secrets.choice(_ALPHABET) for _ in range(length))


class CollisionRetryExhausted(RuntimeError):
    """Raised when short-code generation could not find a free code within the retry budget."""


def generate_unique_short_code(
    is_taken: Callable[[str], bool],
    length: int = 7,
    max_attempts: int = 3,
) -> str:
    """Generate a short code, retrying on collision without exposing the collision to the caller.

    FR-SVC-003: collisions are resolved automatically; only exhausting the bounded
    retry budget (ADR-007 default: 3 attempts) surfaces as an error.
    """
    for _ in range(max_attempts):
        candidate = generate_short_code(length)
        if not is_taken(candidate):
            return candidate
    raise CollisionRetryExhausted(f"no unique short code found in {max_attempts} attempts")


def compute_default_expiration(created_at: datetime, default_expiration_days: int = 90) -> datetime:
    """Apply the confirmed default expiration policy (PVT-001: 90 days) when none is supplied."""
    return created_at + timedelta(days=default_expiration_days)


def utcnow() -> datetime:
    return datetime.now(timezone.utc)
