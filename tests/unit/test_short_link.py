"""Unit tests for short-code generation (FR-SVC-001, FR-SVC-003, ADR-004)."""

import re

SHORT_CODE_PATTERN = re.compile(r"^[0-9a-zA-Z]{7}$")


def test_generated_short_code_matches_base62_seven_char_format():
    from src.domain.short_link import generate_short_code

    code = generate_short_code()

    assert SHORT_CODE_PATTERN.match(code), f"{code!r} does not match Base62 7-char format"


def test_generated_short_codes_are_not_trivially_constant():
    from src.domain.short_link import generate_short_code

    codes = {generate_short_code() for _ in range(20)}

    assert len(codes) > 1, "generator should not always return the same code"
