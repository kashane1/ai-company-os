#!/usr/bin/env python3
"""Verify a domain points at Netlify without breaking the client's email.

The post-cutover safety net. Multi-resolver + propagation-aware: it reports
``ok`` only when both Google and Cloudflare agree, ``propagating`` when they
disagree (re-check later), and ``fail`` when they agree the record is wrong — most
importantly catching a wiped MX (broken email).

Exit codes: 0 = all ok · 2 = a hard failure · 3 = still propagating.

Examples::

    python scripts/agency/verify_domain.py acme.com --site acme.netlify.app \\
        --expect-email "Google Workspace"
    python scripts/agency/verify_domain.py acme.com --site acme.netlify.app --no-https
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from packages.agency.domain_recon import DomainValidationError  # noqa: E402
from packages.agency.domain_verify import DomainVerifier, render_result  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("domain", help="the client's domain, e.g. acme.com")
    ap.add_argument("--site", required=True, help="Netlify site host the www CNAME should point at")
    ap.add_argument(
        "--expect-email",
        default="",
        help="email host recon recorded pre-cutover (e.g. 'Google Workspace'); MX must route there",
    )
    ap.add_argument("--no-https", action="store_true", help="skip the HTTPS liveness probe")
    ap.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    args = ap.parse_args()

    try:
        result = DomainVerifier().verify(
            args.domain,
            netlify_site=args.site,
            expected_email_host=args.expect_email,
            check_https=not args.no_https,
        )
    except DomainValidationError as exc:
        print(f"ERROR: invalid domain — {exc}", file=sys.stderr)
        return 1

    print(json.dumps(result.to_dict(), indent=2) if args.json else render_result(result))

    if result.ok:
        return 0
    return 2 if result.failures else 3


if __name__ == "__main__":
    raise SystemExit(main())
