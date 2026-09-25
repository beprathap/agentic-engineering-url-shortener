"""Environment-variable configuration with fail-fast validation (Constitution Principle V)."""

from __future__ import annotations

import os
from dataclasses import dataclass


class ConfigError(ValueError):
    """Raised when configuration is malformed; fail-fast rather than fall back to an insecure default."""


@dataclass(frozen=True)
class Settings:
    db_path: str
    default_expiration_days: int
    short_code_length: int
    short_code_max_generation_attempts: int
    gate_timeout_seconds: int
    retry_max_attempts: int
    retry_backoff_base_ms: int


def load_settings(env: dict[str, str] | None = None) -> Settings:
    """Build Settings from environment variables, applying confirmed spec defaults.

    Fails fast (raises ConfigError) on malformed values rather than silently
    substituting an insecure or nonsensical default.
    """
    e = env if env is not None else os.environ

    def _int(name: str, default: int) -> int:
        raw = e.get(name)
        if raw is None:
            return default
        try:
            value = int(raw)
        except ValueError as exc:
            raise ConfigError(f"{name} must be an integer, got {raw!r}") from exc
        if value <= 0:
            raise ConfigError(f"{name} must be positive, got {value}")
        return value

    return Settings(
        db_path=e.get("DB_PATH", "url_shortener.db"),
        default_expiration_days=_int("DEFAULT_EXPIRATION_DAYS", 90),  # PVT-001, confirmed
        short_code_length=_int("SHORT_CODE_LENGTH", 7),  # ADR-004, confirmed
        short_code_max_generation_attempts=_int("SHORT_CODE_MAX_ATTEMPTS", 3),
        gate_timeout_seconds=_int("GATE_TIMEOUT_SECONDS", 24 * 60 * 60),  # confirmed 24h
        retry_max_attempts=_int("RETRY_MAX_ATTEMPTS", 3),  # PVT-004, confirmed
        retry_backoff_base_ms=_int("RETRY_BACKOFF_BASE_MS", 200),  # PVT-004, confirmed
    )
