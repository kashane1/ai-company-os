"""Stripe Checkout initiation for a client engagement (Agency layer, G1).

The reconciler (``billing.py``) is the *read* side — it applies verified webhook
events to the ledger. This is the *write* side: build one hosted Checkout Session
for a bundle (a one-time setup fee + a recurring monthly retainer) and hand the
operator a URL to drop into ``OFFER.md``.

Key correctness rules (from the research pass):

* ``mode="subscription"`` with two line items — the one-time setup price lands on
  the initial invoice only, the monthly price recurs.
* Metadata ``{product_id, bundle, mode}`` is set on BOTH the session and
  ``subscription_data`` so every future ``invoice.paid`` carries it (the invoice
  object otherwise has none — see billing.py ``_find_ledger_by_object`` fallback).
* An idempotency key keyed on ``(product_id, bundle, mode)`` collapses retries.
* **Live mode is approval-gated** (``stripe_live_subscription``); test mode is free.
* Price ids are environment-scoped config (``STRIPE_PRICE_MAP``), never catalog data.

The Stripe call is behind a :class:`CheckoutProvider` seam so this is fully
unit-testable with a fake — no network, no ``stripe`` import in tests.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable, Protocol, runtime_checkable

from packages.config.settings import STRIPE_PRICE_MAP_ENV_VAR, get_api_key
from packages.db.approval_store import ApprovalStore
from packages.policies.agency_gates import assert_retainer_approval_granted

# Stripe Checkout sessions expire between 30 min and 24h from creation.
_MIN_EXPIRES = 30 * 60
_MAX_EXPIRES = 24 * 60 * 60

Clock = Callable[[], datetime]


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class PaymentInitiationError(ValueError):
    """Bad checkout input — unknown bundle/mode or a missing price-map entry."""


@dataclass(frozen=True)
class PriceMapEntry:
    setup_price_id: str
    monthly_price_id: str


@dataclass(frozen=True)
class CheckoutRequest:
    """What the provider must turn into a hosted Checkout Session."""

    line_items: tuple[dict[str, object], ...]
    mode: str  # always "subscription" here
    session_metadata: dict[str, str]
    subscription_metadata: dict[str, str]
    idempotency_key: str
    expires_at: int
    success_url: str
    cancel_url: str


@dataclass(frozen=True)
class CheckoutSession:
    url: str
    session_id: str
    expires_at: int

    def to_dict(self) -> dict[str, object]:
        return {"url": self.url, "session_id": self.session_id, "expires_at": self.expires_at}


@runtime_checkable
class CheckoutProvider(Protocol):
    def create_subscription_checkout(self, request: CheckoutRequest) -> CheckoutSession: ...


class StripeCheckoutProvider:
    """Real provider — wraps the Stripe SDK. ``stripe`` is imported lazily so the
    seam (and its tests) don't require the package."""

    def __init__(self, secret_key: str) -> None:
        self._secret_key = secret_key

    def create_subscription_checkout(self, request: CheckoutRequest) -> CheckoutSession:
        import stripe  # lazy — only the real path needs it

        session = stripe.checkout.Session.create(
            mode=request.mode,
            line_items=list(request.line_items),
            metadata=request.session_metadata,
            subscription_data={"metadata": request.subscription_metadata},
            expires_at=request.expires_at,
            success_url=request.success_url,
            cancel_url=request.cancel_url,
            api_key=self._secret_key,
            idempotency_key=request.idempotency_key,
        )
        return CheckoutSession(
            url=str(session.url),
            session_id=str(session.id),
            expires_at=int(session.expires_at or request.expires_at),
        )


def load_price_map() -> dict[str, object]:
    """Parse ``STRIPE_PRICE_MAP`` (JSON) from the environment, or ``{}``."""
    raw = get_api_key(STRIPE_PRICE_MAP_ENV_VAR)
    if not raw:
        return {}
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise PaymentInitiationError(f"STRIPE_PRICE_MAP is not valid JSON: {exc}") from exc
    if not isinstance(parsed, dict):
        raise PaymentInitiationError("STRIPE_PRICE_MAP must be a JSON object")
    return parsed


def resolve_price_entry(
    price_map: dict[str, object], bundle: str, mode: str
) -> PriceMapEntry:
    by_bundle = price_map.get(bundle)
    entry = by_bundle.get(mode) if isinstance(by_bundle, dict) else None
    if not isinstance(entry, dict):
        raise PaymentInitiationError(
            f"no price-map entry for bundle {bundle!r} in {mode!r} mode"
        )
    setup = str(entry.get("setup", ""))
    monthly = str(entry.get("monthly", ""))
    if not setup or not monthly:
        raise PaymentInitiationError(
            f"price-map entry for {bundle!r}/{mode!r} needs both 'setup' and 'monthly'"
        )
    return PriceMapEntry(setup_price_id=setup, monthly_price_id=monthly)


def create_client_checkout(
    product_id: str,
    bundle: str,
    *,
    provider: CheckoutProvider,
    mode: str = "test",
    price_map: dict[str, object] | None = None,
    approval_id: str = "",
    store: ApprovalStore | None = None,
    success_url: str = "https://better-business-web.netlify.app/thanks/",
    cancel_url: str = "https://better-business-web.netlify.app/",
    expires_in_seconds: int = _MAX_EXPIRES,
    now: Clock = _utc_now,
) -> CheckoutSession:
    """Create a subscription Checkout (setup + monthly) for a client bundle.

    Live mode requires a granted ``stripe_live_subscription`` approval; test mode
    is ungated.
    """
    if mode not in {"test", "live"}:
        raise PaymentInitiationError(f"mode must be 'test' or 'live', got {mode!r}")
    if mode == "live":
        # Real money — gate it (PAYMENTS/stripe_live_subscription).
        assert_retainer_approval_granted(
            approval_id,
            product_id=product_id,
            approval_type="stripe_live_subscription",
            store=store,
        )

    resolved_map = price_map if price_map is not None else load_price_map()
    entry = resolve_price_entry(resolved_map, bundle, mode)

    metadata = {"product_id": product_id, "bundle": bundle, "mode": mode}
    expires_in = max(_MIN_EXPIRES, min(_MAX_EXPIRES, expires_in_seconds))
    request = CheckoutRequest(
        line_items=(
            {"price": entry.monthly_price_id, "quantity": 1},  # recurring retainer
            {"price": entry.setup_price_id, "quantity": 1},  # one-time setup (first invoice)
        ),
        mode="subscription",
        session_metadata=dict(metadata),
        subscription_metadata=dict(metadata),
        idempotency_key=f"checkout:{product_id}:{bundle}:{mode}",
        expires_at=int(now().timestamp()) + expires_in,
        success_url=success_url,
        cancel_url=cancel_url,
    )
    return provider.create_subscription_checkout(request)
