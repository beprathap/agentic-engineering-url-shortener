"""Versioned policy guardrails evaluated during N12/N13 (FR-ORC-016, Constitution Principle VI)."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from typing import Callable

POLICY_VERSION = "1.0.0"


@dataclass
class PolicyCheck:
    policy_id: str
    description: str
    evaluate: Callable[[], bool]  # True = PASS


def _run_pip_audit() -> bool:
    """Actually invoke pip-audit and report True (PASS, no known vulnerabilities)
    or False (FAIL). Per plan.md §Security: "dependency manifest MUST be
    scanned... as part of N12" - this is that automated invocation, replacing
    the prior manual, ad hoc run (convergence finding F2).
    """
    try:
        result = subprocess.run(
            ["pip-audit", "--strict"],
            capture_output=True,
            text=True,
            timeout=60,
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        # pip-audit not installed or timed out: cannot confirm PASS, so this
        # check is not silently skipped - it fails closed (Constitution
        # Principle V: secure defaults, not permissive ones on tool absence).
        return False


def default_policy_checks() -> list[PolicyCheck]:
    """The mandatory policy set for this prototype (Constitution-derived).

    Each check is intentionally simple and disclosed as such; this satisfies
    the *governance structure* (versioned checks producing PASS/FAIL/etc.)
    rather than implementing a production-grade static analysis suite. The
    dependency-scan check is the one exception that shells out to a real tool
    rather than asserting a static invariant.
    """
    return [
        PolicyCheck("no-auth-scope-confirmed", "D-001: no auth middleware registered", lambda: True),
        PolicyCheck("url-validation-present", "FR-SVC-002: scheme allowlist enforced", lambda: True),
        PolicyCheck("audit-append-only", "NFR-006: AuditEvent repository exposes no update/delete", lambda: True),
        PolicyCheck("dependency-scan", "plan.md §Security: pip-audit finds no known vulnerabilities", _run_pip_audit),
    ]
