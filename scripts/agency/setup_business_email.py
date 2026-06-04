#!/usr/bin/env python3
"""Emit the business-email runbook (and optionally record completion) — G5.

Examples:
  # write BUSINESS_EMAIL.md for the operator to follow:
  python scripts/agency/setup_business_email.py --business "Joe's Plumbing" \\
    --domain joesplumbing.com --out docs/products/joes-plumbing-site

  # mark it done once mail flows:
  python scripts/agency/setup_business_email.py --business "Joe's Plumbing" \\
    --domain joesplumbing.com --product-id joes-plumbing-site --mark-complete \\
    --verified --mx-configured
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from packages.agency.business_email import (  # noqa: E402
    DEFAULT_ALIASES,
    BusinessEmailSetup,
    derive_domain,
    emit_business_email_runbook,
    save_business_email_setup,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--business", required=True)
    parser.add_argument("--domain", default="")
    parser.add_argument("--site-url", default="")
    parser.add_argument("--provider", default="Google Workspace")
    parser.add_argument("--aliases", default=",".join(DEFAULT_ALIASES))
    parser.add_argument("--out", type=Path, help="client docs dir → writes BUSINESS_EMAIL.md")
    parser.add_argument("--product-id", default="")
    parser.add_argument("--mark-complete", action="store_true")
    parser.add_argument("--verified", action="store_true")
    parser.add_argument("--mx-configured", action="store_true")
    args = parser.parse_args()

    domain = args.domain or (derive_domain(args.site_url) if args.site_url else "")
    if not domain:
        print("ERROR: provide --domain or --site-url", file=sys.stderr)
        return 1
    aliases = tuple(a.strip() for a in args.aliases.split(",") if a.strip())

    done: dict[str, object] = {}
    if args.out:
        path = emit_business_email_runbook(
            args.business, args.out, domain=domain, provider=args.provider, aliases=aliases
        )
        done["runbook"] = str(path)

    if args.mark_complete:
        if not args.product_id:
            print("ERROR: --mark-complete requires --product-id", file=sys.stderr)
            return 1
        record = BusinessEmailSetup(
            product_id=args.product_id,
            domain=domain,
            provider=args.provider,
            aliases=list(aliases),
            mx_configured=args.mx_configured,
            verified=args.verified,
            completed_at=datetime.now(timezone.utc).isoformat(),
        )
        done["record"] = str(save_business_email_setup(record))

    if not done:
        print("ERROR: nothing to do — pass --out and/or --mark-complete", file=sys.stderr)
        return 1
    print(json.dumps(done, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
