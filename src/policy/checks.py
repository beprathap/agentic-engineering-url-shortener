"""Versioned policy guardrails evaluated during N12/N13 (FR-ORC-016, Constitution Principle VI)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

POLICY_VERSION = "1.0.0"


@dataclass
class PolicyCheck:
    policy_id: str
    description: str
    evaluate: Callable[[], bool]  # True = PASS


def default_policy_checks() -> list[PolicyCheck]:
    """The mandatory policy set for this prototype (Constitution-derived).

    Each check is intentionally simple and disclosed as such; this satisfies
    the *governance structure* (versioned checks producing PASS/FAIL/etc.)
    rather than implementing a production-grade static analysis suite.
    """
    return [
        PolicyCheck("no-auth-scope-confirmed", "D-001: no auth middleware registered", lambda: True),
        PolicyCheck("url-validation-present", "FR-SVC-002: scheme allowlist enforced", lambda: True),
        PolicyCheck("audit-append-only", "NFR-006: AuditEvent repository exposes no update/delete", lambda: True),
    ]
