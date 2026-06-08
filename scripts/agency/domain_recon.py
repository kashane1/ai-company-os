#!/usr/bin/env python3
"""Domain readiness recon — read a client's public DNS + registration state.

Preemptive: needs only the domain name, no client access. Reads public RDAP + DNS
over HTTPS and prints a readiness report (and, with ``--site``, the copy-paste
DNS records to point the domain at a Netlify site).

Examples::

    python scripts/agency/domain_recon.py acme.com
    python scripts/agency/domain_recon.py acme.com --site acme.netlify.app
    python scripts/agency/domain_recon.py acme.com --json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from packages.agency.domain_recon import (  # noqa: E402
    DomainRecon,
    DomainValidationError,
    netlify_external_dns_instructions,
    render_report,
)


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("domain", help="the client's domain, e.g. acme.com")
    ap.add_argument(
        "--site",
        default="",
        help="Netlify site host (e.g. acme.netlify.app) to render DNS instructions",
    )
    ap.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    args = ap.parse_args()

    try:
        report = DomainRecon().recon(args.domain)
    except DomainValidationError as exc:
        print(f"ERROR: invalid domain — {exc}", file=sys.stderr)
        return 1

    if args.json:
        out = report.to_dict()
        if args.site:
            out["netlify_instructions"] = netlify_external_dns_instructions(report, args.site)
        print(json.dumps(out, indent=2))
        return 0

    print(render_report(report))
    if args.site:
        print(netlify_external_dns_instructions(report, args.site))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
