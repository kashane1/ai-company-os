#!/usr/bin/env python3
"""Create a Stripe Checkout link for a client bundle OR a custom service set (G1).

Prices come from the catalog (inline price_data) — the same engine the web
build-your-own-bundle flow uses, so the CLI and the website charge identical
amounts. Test mode is ungated; live mode requires a granted stripe_live_subscription
approval (pass --approval-id). Paste the returned URL into the client's OFFER.md.

Requires STRIPE_SECRET_KEY in the env. Examples:
  # a named package (curated promo price):
  python scripts/agency/create_checkout.py --product-id joes-plumbing-site --bundle package_c
  # an arbitrary custom bundle (tier discount):
  python scripts/agency/create_checkout.py --product-id joes-site \\
      --service-id website --service-id hosting --service-id booking_setup
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from packages.agency.payments import (  # noqa: E402
    PaymentInitiationError,
    StripeCheckoutProvider,
    create_inline_checkout,
)
from packages.config.settings import STRIPE_SECRET_KEY_ENV_VAR, get_api_key  # noqa: E402
from packages.policies.approvals import PolicyViolation  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--product-id", required=True)
    parser.add_argument("--bundle", default="", help="a named package id (e.g. package_c)")
    parser.add_argument(
        "--service-id",
        dest="service_ids",
        action="append",
        default=[],
        help="a catalog service id; repeat for a custom bundle",
    )
    parser.add_argument("--mode", choices=["test", "live"], default="test")
    parser.add_argument("--approval-id", default="", help="required for --mode live")
    args = parser.parse_args()

    if bool(args.bundle) == bool(args.service_ids):
        print("ERROR: pass exactly one of --bundle or --service-id", file=sys.stderr)
        return 1

    secret = get_api_key(STRIPE_SECRET_KEY_ENV_VAR)
    if not secret:
        print(f"ERROR: {STRIPE_SECRET_KEY_ENV_VAR} not set", file=sys.stderr)
        return 1
    if args.mode == "live" and not secret.startswith("sk_live_"):
        print("ERROR: --mode live requires an sk_live_ key", file=sys.stderr)
        return 1

    try:
        session = create_inline_checkout(
            args.product_id,
            provider=StripeCheckoutProvider(secret),
            bundle=args.bundle or None,
            service_ids=args.service_ids or None,
            mode=args.mode,
            approval_id=args.approval_id,
        )
    except PolicyViolation as exc:
        print(f"ERROR {exc.code}: {exc}", file=sys.stderr)
        return 2
    except PaymentInitiationError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print(json.dumps(session.to_dict(), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
