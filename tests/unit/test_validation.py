"""Unit tests for URL validation (FR-SVC-002, NFR-001)."""

import pytest


def test_accepts_http_and_https_urls():
    from src.domain.validation import validate_url

    validate_url("http://example.com/path")
    validate_url("https://example.com/path")


@pytest.mark.parametrize(
    "url",
    [
        "javascript:alert(1)",
        "data:text/html,<script>alert(1)</script>",
        "ftp://example.com/file",
        "not a url",
        "",
    ],
)
def test_rejects_disallowed_schemes_and_malformed_urls(url):
    from src.domain.validation import InvalidUrlError, validate_url

    with pytest.raises(InvalidUrlError):
        validate_url(url)


@pytest.mark.parametrize(
    "url",
    [
        "http://localhost/admin",
        "http://127.0.0.1/admin",
        "http://169.254.169.254/latest/meta-data",
        "http://192.168.1.1/",
        "http://10.0.0.1/",
    ],
)
def test_rejects_loopback_and_private_address_targets(url):
    from src.domain.validation import InvalidUrlError, validate_url

    with pytest.raises(InvalidUrlError):
        validate_url(url)
