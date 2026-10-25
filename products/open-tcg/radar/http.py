"""Shared network setup: one identifying User-Agent and one verifying TLS context."""

from __future__ import annotations

import ssl

import httpx

from .config import REQUEST_TIMEOUT_S, USER_AGENT


def make_client() -> httpx.Client:
    return httpx.Client(
        timeout=httpx.Timeout(REQUEST_TIMEOUT_S, connect=10.0),
        follow_redirects=True,
        headers={"User-Agent": USER_AGENT},
    )


def tls_context() -> ssl.SSLContext:
    """Certificate-verifying TLS with certifi's roots.

    python.org Python builds ship without macOS system roots, and some stdlib
    clients (imaplib) do not verify certificates unless given a context.
    """
    import certifi

    return ssl.create_default_context(cafile=certifi.where())
