"""SSRF guard — validate a URL targets a *public* host before fetching it.

Any externally-supplied URL is untrusted: a prospect's listed website, and
especially the "current website" field on the public review form. Left
unchecked, a submitted ``http://169.254.169.254/...`` (cloud metadata),
``http://127.0.0.1`` / ``http://10.x`` etc. turns our website auditor into an
SSRF proxy against the always-on Mac and its local services.

Call :func:`assert_safe_public_url` (or the boolean :func:`is_safe_public_url`)
immediately before any network fetch, and re-check the *final* URL after any
redirects (a public URL can 302 to an internal one).

Limitation: DNS rebinding (host resolves public here, private at fetch time) is
not fully closed — pin the resolved IP at the socket layer for that. This guard
blocks the common, direct cases and resolution-time private targets.
"""

from __future__ import annotations

import ipaddress
import socket
from typing import Callable
from urllib.parse import urlsplit

ALLOWED_SCHEMES = ("http", "https")

# Resolver seam so tests don't touch the network. Returns IP strings for a host.
Resolver = Callable[[str], list[str]]


class UnsafeUrlError(ValueError):
    """Raised when a URL is not a safe public http(s) target."""


def _default_resolver(host: str) -> list[str]:
    try:
        infos = socket.getaddrinfo(host, None)
    except socket.gaierror:
        return []
    return [info[4][0].split("%")[0] for info in infos]


def _ip_is_public(ip: ipaddress._BaseAddress) -> bool:
    if isinstance(ip, ipaddress.IPv6Address) and ip.ipv4_mapped is not None:
        ip = ip.ipv4_mapped
    return not (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_multicast
        or ip.is_reserved
        or ip.is_unspecified
    )


def assert_safe_public_url(url: str, *, resolver: Resolver = _default_resolver) -> None:
    """Raise :class:`UnsafeUrlError` unless ``url`` is a public http(s) target."""
    if not url or not isinstance(url, str):
        raise UnsafeUrlError("empty url")
    parts = urlsplit(url.strip())
    if parts.scheme.lower() not in ALLOWED_SCHEMES:
        raise UnsafeUrlError(f"scheme {parts.scheme!r} not allowed (http/https only)")
    if parts.username or parts.password:
        raise UnsafeUrlError("credentials in URL are not allowed")
    host = parts.hostname
    if not host:
        raise UnsafeUrlError("url has no host")

    # Literal IP host: check directly (no DNS).
    try:
        literal = ipaddress.ip_address(host)
    except ValueError:
        literal = None
    if literal is not None:
        if not _ip_is_public(literal):
            raise UnsafeUrlError(f"host {host!r} is a non-public address")
        return

    addrs = resolver(host)
    if not addrs:
        raise UnsafeUrlError(f"could not resolve host {host!r}")
    for addr in addrs:
        try:
            ip = ipaddress.ip_address(addr)
        except ValueError:
            continue
        if not _ip_is_public(ip):
            raise UnsafeUrlError(f"host {host!r} resolves to non-public address {addr}")


def is_safe_public_url(url: str, *, resolver: Resolver = _default_resolver) -> bool:
    """Boolean form of :func:`assert_safe_public_url`."""
    try:
        assert_safe_public_url(url, resolver=resolver)
        return True
    except UnsafeUrlError:
        return False
