#!/usr/bin/env python3
"""Create a Stripe Checkout link (setup + monthly) for a client bundle (G1).

Test mode is ungated; live mode requires a granted stripe_live_subscription
approval (pass --approval-id). Paste the returned URL into the client's OFFER.md.

Requires STRIPE_SECRET_KEY and STRIPE_PRICE_MAP (JSON) in the env. Example:
  python scripts/agency/create_checkout.py --product-id joes-plumbing-site --bundle package_c
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
    create_client_checkout,
)
from packages.config.settings import STRIPE_SECRET_KEY_ENV_VAR, get_api_key  # noqa: E402
from packages.policies.approvals import PolicyViolation  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--product-id", required=True)
    parser.add_argument("--bundle", required=True)
    parser.add_argument("--mode", choices=["test", "live"], default="test")
    parser.add_argument("--approval-id", default="", help="required for --mode live")
    args = parser.parse_args()

    secret = get_api_key(STRIPE_SECRET_KEY_ENV_VAR)
    if not secret:
        print(f"ERROR: {STRIPE_SECRET_KEY_ENV_VAR} not set", file=sys.stderr)
        return 1
    if args.mode == "live" and not secret.startswith("sk_live_"):
        print("ERROR: --mode live requires an sk_live_ key", file=sys.stderr)
        return 1

    try:
        session = create_client_checkout(
            args.product_id,
            args.bundle,
            provider=StripeCheckoutProvider(secret),
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
