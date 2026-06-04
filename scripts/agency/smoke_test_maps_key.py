#!/usr/bin/env python3
"""Smoke-test the live GOOGLE_MAPS_DEMO_API_KEY against Google's Maps APIs.

Makes real network calls. Probes the two surfaces packages/agency/demo_maps.py
uses, independently, because a demo key may have only one enabled:

  1. Maps Embed API  (the intended use — interactive iframe, unbilled for `place`)
  2. Maps Static API (opt-in `<img>` map)

Exit code is 0 when the PRIMARY surface (Embed API) accepts the key, non-zero
otherwise. The Static result is reported but does not fail the check, since a
key restricted to Embed-only is still a valid demo key.

    python scripts/agency/smoke_test_maps_key.py
    python scripts/agency/smoke_test_maps_key.py --query "Statue of Liberty, NY"
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

import httpx  # noqa: E402

from packages.agency.demo_maps import (  # noqa: E402
    demo_maps_key,
    embed_place_url,
    static_map_url,
)
from packages.config.settings import GOOGLE_MAPS_DEMO_API_KEY_ENV_VAR  # noqa: E402

# Substrings Google returns in an Embed API error page / Static API error body
# when the key is bad, the API is disabled, or the referrer/IP is blocked.
REJECTION_MARKERS = (
    "rejected your request",
    "not authorized to use this",
    "api key is invalid",
    "invalid api key",
    "apinotactivatedmaperror",
    "missingkeymaperror",
    "referernotallowedmaperror",
    "this ip, site or mobile application is not authorized",
)


def _redacted(url: str, key: str) -> str:
    return url.replace(key, f"{key[:6]}…{key[-4:]}" if len(key) > 10 else "…")


def _find_marker(text: str) -> str | None:
    lowered = text.lower()
    for marker in REJECTION_MARKERS:
        if marker in lowered:
            return marker
    return None


def _probe_embed(client: httpx.Client, query: str, key: str) -> bool:
    url = embed_place_url(query, key=key)
    print(f"\n[Embed API]  GET {_redacted(url, key)}")
    try:
        resp = client.get(url)
    except httpx.HTTPError as exc:
        print(f"  FAIL — request error: {exc}")
        return False
    marker = _find_marker(resp.text)
    if resp.status_code == 200 and marker is None:
        print(f"  PASS — {resp.status_code}, {len(resp.text)} bytes, no rejection markers")
        return True
    if marker is not None:
        print(f"  FAIL — {resp.status_code}, rejection marker: {marker!r}")
    else:
        print(f"  FAIL — HTTP {resp.status_code}: {resp.text[:200].strip()!r}")
    return False


def _probe_static(client: httpx.Client, query: str, key: str) -> bool:
    url = static_map_url(query, key=key)
    print(f"\n[Static API] GET {_redacted(url, key)}")
    try:
        resp = client.get(url)
    except httpx.HTTPError as exc:
        print(f"  WARN — request error: {exc}")
        return False
    content_type = resp.headers.get("content-type", "")
    if resp.status_code == 200 and content_type.startswith("image/"):
        print(f"  PASS — {resp.status_code}, {content_type}, {len(resp.content)} bytes")
        return True
    body = resp.text[:200].strip()
    print(f"  INFO — {resp.status_code}, content-type={content_type or '?'}: {body!r}")
    print("         (Static API not required for demos — Embed-only keys are fine.)")
    return False


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--query",
        default="Googleplex, Mountain View, CA",
        help="Place query to probe (default: a well-known landmark).",
    )
    args = parser.parse_args()

    key = demo_maps_key()
    if not key:
        print(
            f"ERROR: {GOOGLE_MAPS_DEMO_API_KEY_ENV_VAR} is not set (.env or env).",
            file=sys.stderr,
        )
        return 2

    print(f"Smoke-testing {GOOGLE_MAPS_DEMO_API_KEY_ENV_VAR} (query: {args.query!r})")
    with httpx.Client(timeout=15.0, follow_redirects=True) as client:
        embed_ok = _probe_embed(client, args.query, key)
        _probe_static(client, args.query, key)

    print("\n" + "=" * 60)
    if embed_ok:
        print("RESULT: PASS — demo Maps key works for the Maps Embed API.")
        return 0
    print(
        "RESULT: FAIL — Embed API rejected the key. Check that the key is valid, "
        "the 'Maps Embed API' is enabled, and HTTP-referrer restrictions allow "
        "server-side / your test referrer."
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
