"""Shared HTTP client. One identifying User-Agent for every source."""

from __future__ import annotations

import httpx

from .config import REQUEST_TIMEOUT_S, USER_AGENT


def make_client() -> httpx.Client:
    return httpx.Client(
        timeout=httpx.Timeout(REQUEST_TIMEOUT_S, connect=10.0),
        follow_redirects=True,
        headers={"User-Agent": USER_AGENT},
    )
