"""Idempotently create the Stripe Products + Prices for every bundle, and emit a
``STRIPE_PRICE_MAP`` block ready to paste into ``.env`` (first-sale runbook Step 1/2).

Why this exists
---------------
The runbook says: create each bundle's **setup (one-time)** and **monthly
(recurring)** Price, give each a stable ``lookup_key`` so the test↔live
``price_…`` divergence stops mattering, then drop the ids into ``STRIPE_PRICE_MAP``.
Done by hand in the Dashboard that's ~12 clicks per bundle and easy to fat-finger
an amount. This does it from the **authoritative marketed prices** in
``products/better-business-web/site/src/data/packages.json`` so Stripe can never
disagree with what the customer sees on the pricing page.

Design
------
* **No SDK / no CLI** — talks to the Stripe REST API over stdlib ``urllib`` so
  there's nothing to ``pip install`` first.
* **Idempotent** — keyed on ``lookup_key`` (``<bundle>_setup`` / ``<bundle>_monthly``).
  Re-running reuses the existing Price+Product instead of duplicating. Run it as
  many times as you like.
* **Mode-explicit** — ``--mode test`` refuses an ``sk_live_`` key and vice-versa,
  so you can't accidentally create live Prices with a test key or the reverse.

Usage
-----
    # test mode (uses STRIPE_SECRET_KEY=sk_test_… from .env or env)
    python scripts/agency/stripe_bootstrap.py --mode test

    # live mode (after you've set sk_live_…)
    python scripts/agency/stripe_bootstrap.py --mode live

It prints, at the end, the ``"<mode>"`` block of ``STRIPE_PRICE_MAP`` — merge it
into the existing env value (keep both ``test`` and ``live`` blocks once you have
them) and the checkout flow is wired.
"""

from __future__ import annotations

import argparse
import json
import ssl
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

# The python.org framework build ships without a configured CA bundle, so urllib
# can't verify api.stripe.com's cert. Back the TLS context with certifi (pulled in
# via httpx) when present; fall back to the stdlib default otherwise.
try:
    import certifi

    _SSL_CTX: ssl.SSLContext | None = ssl.create_default_context(cafile=certifi.where())
except Exception:  # pragma: no cover — certifi should be present
    _SSL_CTX = None

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from packages.config.settings import STRIPE_SECRET_KEY_ENV_VAR, get_api_key  # noqa: E402

API = "https://api.stripe.com/v1"
PACKAGES_JSON = ROOT / "products/better-business-web/site/src/data/packages.json"
CURRENCY = "usd"


def _call(method: str, path: str, secret: str, form: dict[str, object] | None = None) -> dict:
    """Minimal Stripe REST call. Secret key is HTTP-basic username, blank password."""
    url = f"{API}{path}"
    data = None
    if form is not None:
        data = urllib.parse.urlencode(form, doseq=True).encode()
    req = urllib.request.Request(url, data=data, method=method)
    token = urllib.parse.quote(secret)
    import base64

    req.add_header("Authorization", "Basic " + base64.b64encode(f"{secret}:".encode()).decode())
    if data is not None:
        req.add_header("Content-Type", "application/x-www-form-urlencoded")
    try:
        with urllib.request.urlopen(req, context=_SSL_CTX) as resp:  # noqa: S310 — fixed host
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        body = exc.read().decode()
        raise SystemExit(f"Stripe API {method} {path} -> {exc.code}: {body}") from exc


def _find_price_by_lookup_key(secret: str, lookup_key: str) -> dict | None:
    q = urllib.parse.urlencode({"lookup_keys[]": lookup_key, "limit": 1, "active": "true"})
    result = _call("GET", f"/prices?{q}", secret)
    data = result.get("data") or []
    return data[0] if data else None


def _ensure_product(secret: str, bundle_id: str, name: str, existing_product: str | None) -> str:
    if existing_product:
        return existing_product
    product = _call(
        "POST",
        "/products",
        secret,
        {"name": name, "metadata[bundle]": bundle_id},
    )
    return product["id"]


def _ensure_price(
    secret: str,
    *,
    lookup_key: str,
    product_id: str,
    amount_cents: int,
    recurring: bool,
) -> str:
    existing = _find_price_by_lookup_key(secret, lookup_key)
    if existing:
        return existing["id"]
    form: dict[str, object] = {
        "currency": CURRENCY,
        "unit_amount": amount_cents,
        "product": product_id,
        "lookup_key": lookup_key,
        "transfer_lookup_key": "true",  # steal the key from any stale/inactive price
    }
    if recurring:
        form["recurring[interval]"] = "month"
    price = _call("POST", "/prices", secret, form)
    return price["id"]


def bootstrap(secret: str, mode: str) -> dict[str, dict[str, str]]:
    data = json.loads(PACKAGES_JSON.read_text(encoding="utf-8"))
    bundles = data["bundles"] if isinstance(data, dict) else data
    price_block: dict[str, dict[str, str]] = {}
    for b in bundles:
        bundle_id = b["id"]
        setup_key = f"{bundle_id}_setup"
        monthly_key = f"{bundle_id}_monthly"

        # Reuse a product if either price already exists for this bundle.
        product_id: str | None = None
        for existing in (
            _find_price_by_lookup_key(secret, setup_key),
            _find_price_by_lookup_key(secret, monthly_key),
        ):
            if existing and existing.get("product"):
                product_id = existing["product"]
                break
        product_id = _ensure_product(secret, bundle_id, b["name"], product_id)

        setup_id = _ensure_price(
            secret,
            lookup_key=setup_key,
            product_id=product_id,
            amount_cents=int(round(float(b["setup"]) * 100)),
            recurring=False,
        )
        monthly_id = _ensure_price(
            secret,
            lookup_key=monthly_key,
            product_id=product_id,
            amount_cents=int(round(float(b["monthly"]) * 100)),
            recurring=True,
        )
        price_block[bundle_id] = {"setup": setup_id, "monthly": monthly_id}
        print(
            f"  {bundle_id}: product={product_id} "
            f"setup={setup_id} (${b['setup']}) monthly={monthly_id} (${b['monthly']}/mo)",
            file=sys.stderr,
        )
    return price_block


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("test", "live"), default="test")
    args = parser.parse_args()

    secret = get_api_key(STRIPE_SECRET_KEY_ENV_VAR)
    if not secret:
        print(f"ERROR: {STRIPE_SECRET_KEY_ENV_VAR} not set", file=sys.stderr)
        return 1
    if args.mode == "test" and not secret.startswith("sk_test_"):
        print("ERROR: --mode test requires an sk_test_ key", file=sys.stderr)
        return 1
    if args.mode == "live" and not secret.startswith("sk_live_"):
        print("ERROR: --mode live requires an sk_live_ key", file=sys.stderr)
        return 1

    print(f"Bootstrapping Stripe products/prices in {args.mode} mode…", file=sys.stderr)
    block = bootstrap(secret, args.mode)

    # Emit bundle-first, mode-nested — the shape resolve_price_entry() expects:
    #   {"package_a": {"test": {"setup": ..., "monthly": ...}}, ...}
    # When you later run --mode live, deep-merge the "live" entries into each bundle
    # (keep the existing "test" entries). build_outreach-style merge handled by the
    # .env writer; this just prints the block for the current mode.
    price_map = {bundle: {args.mode: entry} for bundle, entry in block.items()}
    print(f'\n# --- STRIPE_PRICE_MAP additions for mode "{args.mode}" ---', file=sys.stderr)
    print(json.dumps(price_map, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
