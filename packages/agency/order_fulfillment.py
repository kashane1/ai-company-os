"""Process a pulled self-serve order → client-site registry record (Agency layer).

The create-checkout Netlify function writes each build-your-own-bundle order to a
Netlify Blobs store; ``scripts/web/pull-orders.mjs`` drains it into
``state/agency/inbound-orders/<product_id>.json``. This module turns one such
order into a ``client-site`` registry record (via
:func:`packages.agency.promotion.promote_order_to_client`) so the billing
reconciler finds it and activates on ``invoice.paid`` instead of dead-lettering.

Run the poller, then this, BEFORE the stripe-events drain — ordering matters.
"""

from __future__ import annotations

import json
from pathlib import Path

from packages.agency.promotion import promote_order_to_client
from packages.config.settings import load_runtime_paths


def default_inbound_root(repo_root: Path | None = None) -> Path:
    return load_runtime_paths(repo_root).repo_root / "state" / "agency" / "inbound-orders"


def process_inbound_order(
    product_id: str,
    *,
    inbound_root: Path | None = None,
    registry_path: Path | None = None,
    docs_root_parent: Path | None = None,
    repo_root: Path | None = None,
) -> dict[str, object]:
    """Promote the pulled order ``product_id`` into a client-site registry record."""
    root = inbound_root or default_inbound_root(repo_root)
    order_path = root / f"{product_id}.json"
    if not order_path.exists():
        raise FileNotFoundError(f"no inbound order {product_id!r} under {root}")
    order = json.loads(order_path.read_text(encoding="utf-8"))

    return promote_order_to_client(
        product_id=str(order["product_id"]),
        business_name=str(order.get("business", "")),
        service_ids=[str(s) for s in order.get("service_ids", [])],
        bundle=str(order.get("bundle", "custom")),
        registry_path=registry_path,
        docs_root_parent=docs_root_parent,
        repo_root=repo_root,
    )
