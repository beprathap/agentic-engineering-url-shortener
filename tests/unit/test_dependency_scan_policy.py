"""Unit test: N12's policy checks include an actual dependency-scan invocation (plan.md §Security)."""

from unittest.mock import patch


def test_dependency_scan_check_present_and_invokes_pip_audit():
    from src.policy.checks import default_policy_checks

    checks = default_policy_checks()
    scan_checks = [c for c in checks if c.policy_id == "dependency-scan"]
    assert len(scan_checks) == 1


def test_dependency_scan_reports_pass_when_pip_audit_finds_nothing(tmp_path):
    from src.policy import checks as checks_module

    with patch.object(checks_module, "_run_pip_audit", return_value=True):
        result = [c for c in checks_module.default_policy_checks() if c.policy_id == "dependency-scan"][0]
        assert result.evaluate() is True


def test_dependency_scan_reports_fail_when_pip_audit_finds_a_vulnerability(tmp_path):
    from src.policy import checks as checks_module

    with patch.object(checks_module, "_run_pip_audit", return_value=False):
        result = [c for c in checks_module.default_policy_checks() if c.policy_id == "dependency-scan"][0]
        assert result.evaluate() is False
