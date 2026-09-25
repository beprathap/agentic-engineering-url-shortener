"""URL validation: scheme allowlist and SSRF-adjacent hardening (FR-SVC-002, NFR-001)."""

from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urlparse

ALLOWED_SCHEMES = {"http", "https"}


class InvalidUrlError(ValueError):
    """Raised when a submitted URL is malformed, uses a disallowed scheme, or targets a
    loopback/private/link-local address."""


def _is_disallowed_ip(host: str) -> bool:
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        return False
    return ip.is_loopback or ip.is_private or ip.is_link_local or ip.is_reserved or ip.is_multicast


def validate_url(url: str) -> None:
    """Raise InvalidUrlError if the URL is malformed, has a disallowed scheme, or targets
    a loopback/private/link-local host. Returns None (does not normalize) on success.
    """
    if not url:
        raise InvalidUrlError("URL must not be empty")

    parsed = urlparse(url)

    if parsed.scheme not in ALLOWED_SCHEMES:
        raise InvalidUrlError(f"scheme {parsed.scheme!r} is not allowed")

    if not parsed.netloc:
        raise InvalidUrlError("URL is malformed: missing host")

    host = parsed.hostname
    if not host:
        raise InvalidUrlError("URL is malformed: missing host")

    if host == "localhost":
        raise InvalidUrlError("loopback host is not allowed")

    if _is_disallowed_ip(host):
        raise InvalidUrlError(f"host {host!r} resolves to a disallowed address range")

    # Host is a hostname, not a literal IP: resolve and re-check to catch
    # e.g. a DNS name that points at a loopback/private address.
    try:
        resolved = socket.gethostbyname(host)
    except (socket.gaierror, OSError):
        # Resolution failure at validation time is not itself a validation error;
        # DNS may be transiently unavailable. Persistence/redirect-time behavior
        # handles genuinely unreachable targets separately.
        return
    if _is_disallowed_ip(resolved):
        raise InvalidUrlError(f"host {host!r} resolves to a disallowed address range")
