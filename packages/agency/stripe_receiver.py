"""Receiver for forwarded Stripe events (Agency layer, G1).

The Netlify webhook function verifies the Stripe signature, then POSTs a reshaped
event to the local receiver with an ``x-agency-forward-secret`` header. This is
the pure handler that turns one such POST into a ledger update — transport-
agnostic (mounted at ``apps/api`` ``POST /stripe/forward``) and fully unit-
testable without a running server.

Status mapping (the forwarder turns a non-2xx into a non-2xx to Stripe, so
Stripe's retry schedule is the durable async queue):

* 503 — receiver not configured (no shared secret);
* 401 — bad/absent shared secret (constant-time compared);
* 400 — body is not a JSON object;
* 200 ``reconciled`` — applied to the ledger;
* 200 ``dead_lettered`` — unknown client, durably captured (do NOT retry);
* 422 — malformed event / mode mismatch (won't succeed on retry → stop);
* 500 — transient IO failure (retry).
"""

from __future__ import annotations

import hmac
import json
from dataclasses import dataclass
from pathlib import Path

from packages.agency.billing import (
    BillingDeadLetterError,
    BillingReconciliationError,
    reconcile_stripe_event,
)


@dataclass(frozen=True)
class ReceiverResult:
    status_code: int
    body: dict[str, object]


def verify_forward_secret(provided: str, expected: str) -> bool:
    """Constant-time comparison; an empty expected secret never matches."""
    if not expected:
        return False
    return hmac.compare_digest(provided or "", expected)


def handle_forwarded_event(
    *,
    provided_secret: str,
    raw_body: str,
    expected_secret: str,
    billing_root: Path | None = None,
    registry_path: Path | None = None,
) -> ReceiverResult:
    if not expected_secret:
        return ReceiverResult(503, {"error": "forward secret not configured"})
    if not verify_forward_secret(provided_secret, expected_secret):
        return ReceiverResult(401, {"error": "invalid forward secret"})

    try:
        event = json.loads(raw_body)
    except (json.JSONDecodeError, TypeError, ValueError) as exc:
        return ReceiverResult(400, {"error": f"invalid json: {exc}"})
    if not isinstance(event, dict):
        return ReceiverResult(400, {"error": "event must be a JSON object"})

    try:
        ledger = reconcile_stripe_event(
            event, billing_root=billing_root, registry_path=registry_path
        )
    except BillingDeadLetterError as exc:  # MUST precede BillingReconciliationError
        return ReceiverResult(200, {"dead_lettered": True, "detail": str(exc)})
    except BillingReconciliationError as exc:  # malformed / mode mismatch — won't retry
        return ReceiverResult(422, {"error": str(exc)})
    except OSError as exc:  # transient — 5xx so the forwarder makes Stripe retry
        return ReceiverResult(500, {"error": str(exc)})

    return ReceiverResult(
        200,
        {"reconciled": True, "product_id": ledger.product_id, "status": ledger.billing_status},
    )
