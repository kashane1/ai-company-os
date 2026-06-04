"""Local receiver for forwarded Stripe events (Agency layer, G1).

Mounted on 127.0.0.1 only. The Netlify webhook function (which verifies the
Stripe signature) POSTs reshaped events here with an ``x-agency-forward-secret``
header; we verify that secret and reconcile into the billing ledger. The actual
logic lives in ``packages.agency.stripe_receiver`` so it's unit-testable without
a server.
"""

from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from packages.agency.stripe_receiver import handle_forwarded_event
from packages.config.settings import (
    AGENCY_STRIPE_EVENT_FORWARD_SECRET_ENV_VAR,
    get_api_key,
)

router = APIRouter(prefix="/stripe", tags=["stripe"])


@router.post("/forward")
async def receive_forwarded_event(request: Request) -> JSONResponse:
    raw = await request.body()
    result = handle_forwarded_event(
        provided_secret=request.headers.get("x-agency-forward-secret", ""),
        raw_body=raw.decode("utf-8", "replace"),
        expected_secret=get_api_key(AGENCY_STRIPE_EVENT_FORWARD_SECRET_ENV_VAR) or "",
    )
    return JSONResponse(status_code=result.status_code, content=result.body)
