"""Agency retainer billing ledger and Stripe event reconciliation.

Reconciliation is read-only with respect to Stripe — it applies *verified*
events (id + type + metadata) to a local per-client ledger and mirrors the
resulting ``billing_status`` onto the product registry. It is:

* **idempotent** — deduped on ``event.id`` (Stripe redelivers);
* **order-safe** — a dedicated integer cursor (``last_event_created``) drops a
  late status event so a stale ``invoice.paid`` can't resurrect a cancelled or
  disputed subscription. Severity-increasing terminal events (dispute/refund/
  cancel) are exempt from that drop (a dispute on an older charge must still win);
* **mode-fenced** — a live event cannot mutate a test ledger or vice-versa;
* **money-honest** — only ``invoice.paid`` activates (not ``subscription.created``);
* **fail-safe on an unknown client** — an event for a ``product_id`` with no
  registry record is written to a dead-letter store and surfaced, never silently
  applied to an orphan ledger.

The ledger is the source of truth for ``billing_status`` ([X-SOT]); the registry
copy is a denormalised cache for cheap display/lookup.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from packages.agency.registry import default_registry_path, load_registry, write_registry
from packages.config.settings import load_runtime_paths
from packages.schemas.product import BillingStatus


class BillingReconciliationError(ValueError):
    """Raised when a Stripe event cannot be mapped to one client ledger."""


class BillingDeadLetterError(BillingReconciliationError):
    """A verified event for an unknown ``product_id`` — captured, not applied.

    Subclasses :class:`BillingReconciliationError` so existing callers (the file
    CLI) keep handling it; a future HTTP receiver can catch this specifically and
    return 200 (the event is durably dead-lettered, so Stripe must not retry).
    """


# Severity-increasing terminal events are applied even if they arrive out of
# order (a dispute/refund on an older charge must not be swallowed by the cursor).
_TERMINAL_EVENT_TYPES = frozenset(
    {
        "charge.dispute.created",
        "charge.dispute.closed",
        "charge.refunded",
        "customer.subscription.deleted",
    }
)

# Events that must apply even if their timestamp is behind the ledger cursor.
# Terminal events are severity-increasing; ``invoice.paid`` is the activation and
# is emitted ~simultaneously with ``checkout.session.completed`` (often 1s OLDER),
# so the cursor must not drop it as "stale". Stale-resurrection is instead guarded
# by ``_target_status`` (a stale invoice.paid can't revive a cancelled/refunded
# ledger). Without this, a real first sale's activation is silently dropped.
_ORDER_EXEMPT_EVENT_TYPES = _TERMINAL_EVENT_TYPES | {"invoice.paid"}


@dataclass(frozen=True)
class BillingLedger:
    product_id: str
    provider: str = "stripe"
    mode: str = "test"
    bundle: str = ""
    # The purchased service set (from checkout metadata). For a named bundle this
    # mirrors the catalog; for a self-serve "custom" bundle it's the only record of
    # what was bought, so fulfillment can read it off the ledger.
    service_ids: list[str] = field(default_factory=list)
    customer_id: str = ""
    subscription_id: str = ""
    setup_price_id: str = ""
    monthly_price_id: str = ""
    latest_invoice_id: str = ""
    billing_status: str = BillingStatus.TRIAL.value
    idempotency_key: str = ""
    last_synced_at: str = ""
    # [X-CURSOR] numeric monotonic guard — Stripe ``created`` as an int epoch.
    last_event_created: int = 0
    processed_event_ids: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return {
            "product_id": self.product_id,
            "provider": self.provider,
            "mode": self.mode,
            "bundle": self.bundle,
            "service_ids": list(self.service_ids),
            "customer_id": self.customer_id,
            "subscription_id": self.subscription_id,
            "setup_price_id": self.setup_price_id,
            "monthly_price_id": self.monthly_price_id,
            "latest_invoice_id": self.latest_invoice_id,
            "billing_status": self.billing_status,
            "idempotency_key": self.idempotency_key,
            "last_synced_at": self.last_synced_at,
            "last_event_created": self.last_event_created,
            "processed_event_ids": list(self.processed_event_ids),
        }

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> "BillingLedger":
        return cls(
            product_id=str(payload["product_id"]),
            provider=str(payload.get("provider", "stripe")),
            mode=str(payload.get("mode", "test")),
            bundle=str(payload.get("bundle", "")),
            service_ids=[str(s) for s in list(payload.get("service_ids", []))],
            customer_id=str(payload.get("customer_id", "")),
            subscription_id=str(payload.get("subscription_id", "")),
            setup_price_id=str(payload.get("setup_price_id", "")),
            monthly_price_id=str(payload.get("monthly_price_id", "")),
            latest_invoice_id=str(payload.get("latest_invoice_id", "")),
            billing_status=str(payload.get("billing_status", BillingStatus.TRIAL.value)),
            idempotency_key=str(payload.get("idempotency_key", "")),
            last_synced_at=str(payload.get("last_synced_at", "")),
            last_event_created=_as_epoch(payload.get("last_event_created", 0)),
            processed_event_ids=[
                str(event_id) for event_id in list(payload.get("processed_event_ids", []))
            ],
        )


def default_billing_root(repo_root: Path | None = None) -> Path:
    return load_runtime_paths(repo_root).repo_root / "state" / "agency" / "billing"


def ledger_path(product_id: str, *, billing_root: Path | None = None) -> Path:
    return (billing_root or default_billing_root()) / f"{product_id}.json"


def load_ledger(product_id: str, *, billing_root: Path | None = None) -> BillingLedger | None:
    path = ledger_path(product_id, billing_root=billing_root)
    if not path.exists():
        return None
    return BillingLedger.from_dict(json.loads(path.read_text(encoding="utf-8")))


def save_ledger(ledger: BillingLedger, *, billing_root: Path | None = None) -> Path:
    path = ledger_path(ledger.product_id, billing_root=billing_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(ledger.to_dict(), indent=2) + "\n", encoding="utf-8")
    return path


def reconcile_stripe_event(
    event: dict[str, object],
    *,
    billing_root: Path | None = None,
    registry_path: Path | None = None,
) -> BillingLedger:
    """Apply one verified Stripe event to the local billing ledger."""
    event_id = str(event.get("id", ""))
    event_type = str(event.get("type", ""))
    if not event_id or not event_type:
        raise BillingReconciliationError("Stripe event requires id and type")
    obj = _event_object(event)
    metadata = dict(obj.get("metadata") or {})
    product_id = str(metadata.get("product_id", ""))
    bundle = str(metadata.get("bundle", ""))
    if not product_id or not bundle:
        # [B6] charge.dispute.created / charge.refunded objects don't carry our
        # subscription metadata. Fall back to an existing ledger matched on the
        # Stripe customer/subscription id before giving up.
        fallback = _find_ledger_by_object(obj, billing_root=billing_root)
        if fallback is None:
            raise BillingReconciliationError(
                "Stripe event metadata must include product_id and bundle"
            )
        product_id, bundle = fallback.product_id, fallback.bundle

    registry_path = registry_path or default_registry_path()

    # [C4] An event for a client with no registry record: dead-letter it and stop
    # — never write an orphan live ledger or crash. Caught here BEFORE save_ledger.
    if _registry_record(product_id, registry_path) is None:
        _write_dead_letter(event, billing_root=billing_root)
        raise BillingDeadLetterError(
            f"no registry record for product_id {product_id!r}; event dead-lettered"
        )

    current = load_ledger(product_id, billing_root=billing_root)

    # Idempotency: Stripe redelivers — re-applying a processed event is a no-op.
    if current and event_id in current.processed_event_ids:
        return current

    # [B2] Mode fence: a live event must not mutate a test ledger (or vice-versa).
    event_mode = _mode(event)
    if current and current.mode != event_mode:
        raise BillingReconciliationError(
            f"event mode {event_mode!r} disagrees with ledger mode {current.mode!r}"
        )

    epoch = _event_created_epoch(event)
    current_status = (
        BillingStatus.coerce(current.billing_status) if current else BillingStatus.TRIAL
    )

    # [B3] Order-safety: drop a late status event (older than the cursor) UNLESS
    # it's a severity-increasing terminal event. Still record the id (deduped).
    out_of_order = (
        current is not None
        and epoch < current.last_event_created
        and event_type not in _ORDER_EXEMPT_EVENT_TYPES
    )
    if out_of_order:
        recorded = BillingLedger.from_dict(
            {**current.to_dict(), "processed_event_ids": [*current.processed_event_ids, event_id]}
        )
        save_ledger(recorded, billing_root=billing_root)
        return recorded

    target = _target_status(current_status, event_type, obj)
    new_status = target if target is not None else current_status

    # Carry the purchased composition from metadata (set on both session and
    # subscription_data, so renewals keep it); fall back to the existing ledger.
    meta_service_ids = str(metadata.get("service_ids", "")).strip()
    service_ids = (
        [s for s in meta_service_ids.split(",") if s]
        if meta_service_ids
        else (current.service_ids if current else [])
    )

    ledger = BillingLedger(
        product_id=product_id,
        mode=event_mode,
        bundle=bundle,
        service_ids=service_ids,
        customer_id=str(obj.get("customer") or (current.customer_id if current else "")),
        subscription_id=str(
            obj.get("subscription")
            or (obj.get("id") if event_type.startswith("customer.subscription.") else "")
            or (current.subscription_id if current else "")
        ),
        setup_price_id=(current.setup_price_id if current else ""),
        monthly_price_id=str(
            metadata.get("monthly_price_id", current.monthly_price_id if current else "")
        ),
        latest_invoice_id=str(
            obj.get("latest_invoice")
            or (obj.get("id") if event_type.startswith("invoice.") else "")
        ),
        billing_status=new_status.value,
        idempotency_key=f"{product_id}:{bundle}:{event_mode}",
        last_synced_at=str(event.get("created", "")),
        last_event_created=max(epoch, current.last_event_created if current else 0),
        processed_event_ids=[*(current.processed_event_ids if current else []), event_id],
    )
    save_ledger(ledger, billing_root=billing_root)

    # [G3] "Money in hand" = invoice.paid. Stamp acceptance once, mirror status.
    _apply_to_registry(
        product_id,
        new_status,
        registry_path=registry_path,
        stamp_acceptance=event_type == "invoice.paid",
        accepted_by=str(obj.get("customer_email") or obj.get("customer") or "unknown"),
        accepted_at=str(event.get("created", "")),
    )
    return ledger


def reconcile_stripe_event_file(
    path: Path,
    *,
    billing_root: Path | None = None,
    registry_path: Path | None = None,
) -> BillingLedger:
    return reconcile_stripe_event(
        json.loads(path.read_text(encoding="utf-8")),
        billing_root=billing_root,
        registry_path=registry_path,
    )


def _event_object(event: dict[str, object]) -> dict[str, object]:
    data = event.get("data")
    if not isinstance(data, dict) or not isinstance(data.get("object"), dict):
        raise BillingReconciliationError("Stripe event data.object is required")
    return dict(data["object"])


def _mode(event: dict[str, object]) -> str:
    return "live" if bool(event.get("livemode", False)) else "test"


def _as_epoch(value: object) -> int:
    """Coerce a stored cursor value to an int (legacy/garbage -> 0)."""
    try:
        return int(value)  # int, float, or numeric str
    except (TypeError, ValueError):
        return 0


def _event_created_epoch(event: dict[str, object]) -> int:
    """Stripe ``created`` as an int epoch. Real events send an int; tolerate a
    numeric or ISO-8601 string; anything unparseable sorts as 0 (oldest)."""
    raw = event.get("created", 0)
    if isinstance(raw, (int, float)):
        return int(raw)
    text = str(raw).strip()
    if text.isdigit():
        return int(text)
    try:
        return int(datetime.fromisoformat(text.replace("Z", "+00:00")).timestamp())
    except (ValueError, OverflowError):
        return 0


def _target_status(
    current: BillingStatus, event_type: str, obj: dict[str, object]
) -> BillingStatus | None:
    """The status an event moves the ledger TO, or ``None`` for "no change".

    Returning ``None`` (not ``TRIAL``) on an unrecognised/non-activating event is
    deliberate — the old silent fall-through to ``trial`` could *downgrade* a paid
    client. Only ``invoice.paid`` activates ([B9]).
    """
    if event_type == "invoice.paid":
        # Activates from any non-terminal state (trial/active/past_due), regardless
        # of sibling-event ordering. But a genuinely stale invoice.paid must not
        # resurrect a terminal funds-gone state — this is the resurrection guard
        # that lets the cursor exempt invoice.paid (see _ORDER_EXEMPT_EVENT_TYPES).
        if current in (
            BillingStatus.CANCELLED,
            BillingStatus.REFUNDED,
            BillingStatus.DISPUTED,
        ):
            return None
        return BillingStatus.ACTIVE
    if event_type == "invoice.payment_failed":
        return BillingStatus.PAST_DUE
    if event_type == "customer.subscription.created":
        return None  # [B9] a created-but-unpaid subscription is NOT entitlement
    if event_type == "customer.subscription.deleted":
        return BillingStatus.CANCELLED
    if event_type == "charge.dispute.created":
        return BillingStatus.DISPUTED
    if event_type == "charge.dispute.closed":
        status = str(obj.get("status", ""))
        if status == "won":
            return BillingStatus.ACTIVE  # funds retained — restore entitlement
        if status == "lost":
            return BillingStatus.REFUNDED  # funds gone
        return None  # warning_closed / inquiry — no money moved
    if event_type == "charge.refunded":
        # Only a FULL refund stops work; a partial refund leaves entitlement.
        return BillingStatus.REFUNDED if bool(obj.get("refunded")) else None
    if event_type == "customer.subscription.updated":
        status = str(obj.get("status", ""))
        if status in {"active", "trialing"}:
            return BillingStatus.ACTIVE
        if status in {"past_due", "unpaid"}:
            return BillingStatus.PAST_DUE
        if status in {"canceled", "cancelled"}:
            return BillingStatus.CANCELLED
        return None
    return None  # unknown event — never silently downgrade


def _find_ledger_by_object(
    obj: dict[str, object], *, billing_root: Path | None = None
) -> BillingLedger | None:
    """Match a metadata-less event (dispute/refund) to a ledger by Stripe ids."""
    customer = str(obj.get("customer") or "")
    subscription = str(obj.get("subscription") or "")
    if not customer and not subscription:
        return None
    root = billing_root or default_billing_root()
    if not root.is_dir():
        return None
    for path in sorted(root.glob("*.json")):
        try:
            ledger = BillingLedger.from_dict(json.loads(path.read_text(encoding="utf-8")))
        except (ValueError, OSError):
            continue
        if (customer and ledger.customer_id == customer) or (
            subscription and ledger.subscription_id == subscription
        ):
            return ledger
    return None


def _registry_record(product_id: str, registry_path: Path) -> dict[str, object] | None:
    for record in load_registry(registry_path):
        if record.get("id") == product_id:
            return record
    return None


def _apply_to_registry(
    product_id: str,
    status: BillingStatus,
    *,
    registry_path: Path,
    stamp_acceptance: bool,
    accepted_by: str,
    accepted_at: str,
) -> None:
    """Field-level merge into the client block: status + write-once acceptance."""
    registry = load_registry(registry_path)
    for record in registry:
        if record.get("id") != product_id:
            continue
        client = dict(record.get("client") or {})
        client["billing_status"] = status.value
        # [G3] write-once: stamp acceptance only on the first paid invoice.
        if stamp_acceptance and not client.get("accepted_at"):
            client["accepted_at"] = accepted_at
            client["accepted_by"] = accepted_by
        record["client"] = client
        write_registry(registry_path, registry)
        return
    # Existence was checked before save_ledger; reaching here means a concurrent
    # delete. Treat as dead-letter rather than crashing the caller.
    raise BillingDeadLetterError(f"registry record for {product_id!r} vanished mid-reconcile")


def _write_dead_letter(event: dict[str, object], *, billing_root: Path | None = None) -> Path:
    root = (billing_root or default_billing_root()) / "dead-letter"
    root.mkdir(parents=True, exist_ok=True)
    event_id = str(event.get("id", "unknown")) or "unknown"
    safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in event_id)
    path = root / f"{safe}.json"
    path.write_text(json.dumps(event, indent=2) + "\n", encoding="utf-8")
    return path
