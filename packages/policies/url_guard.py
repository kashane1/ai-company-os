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
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Callable
from urllib.parse import urljoin, urlsplit

ALLOWED_SCHEMES = ("http", "https")
ALLOWED_PORTS = (80, 443)

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


# ── Guarded fetch ────────────────────────────────────────────────────────────
# A validator that only checks the *initial* address is not enough: a public URL
# can 302 to an internal one, and the guard can't pin a socket. The guarded fetch
# below closes the call-site gaps the validator can't: it disables auto-redirect
# and re-runs the guard on EVERY hop, restricts to ports 80/443, caps the hop
# count and the response size (without trusting Content-Length), and times out.
#
# Residual risk: DNS rebinding between the per-hop guard and the actual socket
# connect is not fully closed (would need socket-level IP pinning). Documented;
# acceptable for the low-volume operator-triggered audit. TODO: pin the resolved
# IP at connect time.


@dataclass(frozen=True)
class FetchResponse:
    """Minimal response the opener seam returns (so tests need no network)."""

    status: int
    headers: dict[str, str]  # lower-cased keys
    body: bytes


@dataclass(frozen=True)
class FetchedPage:
    final_url: str
    status: int
    bytes_read: int
    text: str
    redirects: int


# (url, timeout_seconds, max_bytes) -> FetchResponse. Must NOT auto-follow 3xx.
Opener = Callable[[str, float, int], FetchResponse]

_REDIRECT_STATUSES = frozenset({301, 302, 303, 307, 308})


def _assert_allowed_port(url: str, allowed_ports: tuple[int, ...]) -> None:
    parts = urlsplit(url)
    try:
        port = parts.port
    except ValueError as exc:  # non-numeric port in the authority
        raise UnsafeUrlError(f"invalid port in url: {exc}") from exc
    if port is None:
        port = 443 if parts.scheme.lower() == "https" else 80
    if port not in allowed_ports:
        raise UnsafeUrlError(f"port {port} not allowed (only {allowed_ports})")


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # type: ignore[override]
        return None  # never auto-follow; the caller re-guards each hop


_NOREDIRECT_OPENER = urllib.request.build_opener(_NoRedirect)


def _default_opener(url: str, timeout: float, max_bytes: int) -> FetchResponse:
    request = urllib.request.Request(url, headers={"User-Agent": "bbw-website-audit/1.0"})
    try:
        resp = _NOREDIRECT_OPENER.open(request, timeout=timeout)
    except urllib.error.HTTPError as exc:  # 3xx (blocked redirect) + 4xx/5xx
        headers = {k.lower(): v for k, v in (exc.headers or {}).items()}
        return FetchResponse(status=exc.code, headers=headers, body=b"")
    with resp:
        headers = {k.lower(): v for k, v in resp.headers.items()}
        # Read a capped count — do NOT trust Content-Length.
        body = resp.read(max_bytes + 1)[:max_bytes]
    return FetchResponse(status=getattr(resp, "status", 200) or 200, headers=headers, body=body)


def fetch_public_url(
    url: str,
    *,
    resolver: Resolver = _default_resolver,
    opener: Opener = _default_opener,
    max_redirects: int = 5,
    max_bytes: int = 2_000_000,
    timeout: float = 5.0,
    allowed_ports: tuple[int, ...] = ALLOWED_PORTS,
) -> FetchedPage:
    """Fetch ``url`` only if every hop is a safe public http(s):80/443 target.

    Raises :class:`UnsafeUrlError` if any hop fails the guard / port / hop-count
    checks. The body is capped at ``max_bytes``.
    """
    current = (url or "").strip()
    for hop in range(max_redirects + 1):
        assert_safe_public_url(current, resolver=resolver)  # re-guard EVERY hop
        _assert_allowed_port(current, allowed_ports)
        resp = opener(current, timeout, max_bytes)
        if resp.status in _REDIRECT_STATUSES:
            location = resp.headers.get("location")
            if not location:
                raise UnsafeUrlError(f"redirect with no Location from {current!r}")
            current = urljoin(current, location)
            continue
        body = resp.body[:max_bytes]
        return FetchedPage(
            final_url=current,
            status=resp.status,
            bytes_read=len(body),
            text=body.decode("utf-8", "replace"),
            redirects=hop,
        )
    raise UnsafeUrlError(f"too many redirects (>{max_redirects})")
