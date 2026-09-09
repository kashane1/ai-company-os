"""Phase 3.1 — local magic-link approval endpoint.

A tiny FastAPI ``APIRouter`` that exposes:

- ``GET /approvals/{token_id}`` — renders a one-page confirm screen with a
  form that POSTs the signature back to the endpoint. No auth beyond
  possession of the token and a localhost bind.
- ``POST /approvals/{token_id}/confirm`` — verifies and burns the token;
  P0 actions remain pending for a second confirmation.
- ``POST /approvals/{token_id}/second-factor`` — second-click window for
  P0 actions (App Store submission, protected-branch merge, billing, DNS).

Kashane runs this on his Mac. Remote approvals are explicitly out of scope
for Phase 3. The endpoint should only ever be mounted on ``127.0.0.1``.
"""

from __future__ import annotations

from datetime import datetime, timezone
from html import escape

from fastapi import APIRouter, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from pydantic import BaseModel

from apps.api.control_plane import ControlPlaneService
from packages.db.approval_token_store import ApprovalTokenStore
from packages.policies.approval_tokens import (
    ApprovalTokenError,
    DeviceMismatch,
    SecondFactorOutOfWindow,
    SecondFactorRequired,
    TokenAlreadyBurned,
    TokenExpired,
    TokenNotFound,
    TokenSignatureInvalid,
    record_second_factor,
    verify_and_burn_token,
)
from packages.schemas.approval import ApprovalStatus
from packages.tools.primitives.approvals import SIGNING_KEY_ENV_VAR, _load_signing_secret

# Kept as the endpoint's public constant for callers/tests. The actual secret
# resolution is shared with worker and reviewer approval primitives.
APPROVAL_SECRET_ENV_VAR = SIGNING_KEY_ENV_VAR


def get_secret() -> bytes:
    """Load the shared approval signing secret or return a safe 503."""
    try:
        return _load_signing_secret()
    except (RuntimeError, ValueError):
        raise HTTPException(
            status_code=503,
            detail="approval signing secret unavailable",
        ) from None


router = APIRouter(prefix="/approvals", tags=["approvals"])


class ConfirmResponse(BaseModel):
    approval_id: str
    status: str
    action: str
    subject_id: str
    p0: bool
    second_factor_required: bool
    approved_at: str


_CONFIRM_HTML = """<!doctype html>
<html>
<head><meta charset="utf-8"><title>Approve {action}</title></head>
<body style="font-family: -apple-system, sans-serif; max-width: 640px; margin: 4em auto;">
  <h1>Approve <code>{action}</code></h1>
  <p>Subject: <code>{subject_id}</code></p>
  <p>Approval id: <code>{approval_id}</code></p>
  <p>Class: <strong>{action_class}</strong></p>
  <p>Issued: {issued_at}</p>
  <p>TTL: {ttl_seconds}s</p>
  <form method="post" action="{confirm_path}">
    <input type="hidden" name="signature" value="{signature}">
    <input type="hidden" name="device_fingerprint" value="{device_fingerprint}">
    <button type="submit">{button_label}</button>
  </form>
</body>
</html>
"""


@router.get("/{token_id}", response_class=HTMLResponse)
def render_confirm_page(token_id: str, request: Request) -> HTMLResponse:
    store = ApprovalTokenStore()
    try:
        token = store.load(token_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="token not found") from exc
    second_step = token.action_class == "p0" and bool(token.approved_at)
    endpoint = "confirm_second_factor" if second_step else "confirm_token"
    rendered = _CONFIRM_HTML.format(
        confirm_path=escape(request.url_for(endpoint, token_id=token_id).path, quote=True),
        device_fingerprint=escape(
            token.expected_device_fingerprint or token.device_fingerprint or "mac-local",
            quote=True,
        ),
        button_label="Confirm a second time" if second_step else "Confirm",
        action=escape(token.action, quote=True),
        subject_id=escape(token.subject_id, quote=True),
        approval_id=escape(token.approval_id, quote=True),
        action_class=escape(token.action_class, quote=True),
        issued_at=escape(token.issued_at, quote=True),
        ttl_seconds=escape(str(token.ttl_seconds), quote=True),
        signature=escape(token.signature, quote=True),
    )
    return HTMLResponse(
        content=rendered,
        headers={
            "Cache-Control": "no-store",
            "Referrer-Policy": "no-referrer",
            "Content-Security-Policy": "default-src 'none'; style-src 'unsafe-inline'; "
            "form-action 'self'; frame-ancestors 'none'",
        },
    )


@router.post("/{token_id}/confirm", response_model=ConfirmResponse)
def confirm_token(
    token_id: str,
    request: Request,
    signature: str = Form(...),
    device_fingerprint: str = Form(...),
) -> ConfirmResponse | RedirectResponse:
    store = ApprovalTokenStore()
    secret = get_secret()
    try:
        record = verify_and_burn_token(
            token_id=token_id,
            provided_signature=signature,
            device_fingerprint=device_fingerprint,
            secret=secret,
            store=store,
        )
    except TokenNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except TokenSignatureInvalid as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    except TokenExpired as exc:
        raise HTTPException(status_code=410, detail=str(exc)) from exc
    except TokenAlreadyBurned as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except DeviceMismatch as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ApprovalTokenError as exc:  # defensive catch-all
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    service = ControlPlaneService()
    # Primary-confirm only flips the approval to ``approved`` for non-P0
    # actions. P0 actions stay pending until second-factor lands. This is
    # what the release-readiness policy cross-checks via the
    # approval-token-audit validator (Phase 3.2a).
    if record.action_class == "default":
        service.decide_approval(
            approval_id=record.approval_id,
            status=ApprovalStatus.APPROVED,
            decided_by=f"magic-link:{device_fingerprint}",
            decision_notes=f"token {token_id} burned",
        )

    if record.action_class == "p0" and "text/html" in request.headers.get("accept", ""):
        return RedirectResponse(
            request.url_for("render_confirm_page", token_id=token_id).path,
            status_code=303,
            headers={"Cache-Control": "no-store"},
        )
    return ConfirmResponse(
        approval_id=record.approval_id,
        status="approved" if record.action_class == "default" else "awaiting_second_factor",
        action=record.action,
        subject_id=record.subject_id,
        p0=record.action_class == "p0",
        second_factor_required=record.action_class == "p0",
        approved_at=record.approved_at or "",
    )


@router.post("/{token_id}/second-factor", response_model=ConfirmResponse)
def confirm_second_factor(
    token_id: str,
    signature: str = Form(...),
    device_fingerprint: str = Form(...),
) -> ConfirmResponse:
    store = ApprovalTokenStore()
    secret = get_secret()
    try:
        record = record_second_factor(
            token_id=token_id,
            provided_signature=signature,
            device_fingerprint=device_fingerprint,
            secret=secret,
            store=store,
        )
    except TokenNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except TokenSignatureInvalid as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    except SecondFactorRequired as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except TokenAlreadyBurned as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except SecondFactorOutOfWindow as exc:
        raise HTTPException(status_code=410, detail=str(exc)) from exc
    except DeviceMismatch as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ApprovalTokenError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    service = ControlPlaneService()
    service.decide_approval(
        approval_id=record.approval_id,
        status=ApprovalStatus.APPROVED,
        decided_by=f"magic-link-p0:{device_fingerprint}",
        decision_notes=f"token {token_id} second-factor burned",
    )
    return ConfirmResponse(
        approval_id=record.approval_id,
        status="approved",
        action=record.action,
        subject_id=record.subject_id,
        p0=True,
        second_factor_required=False,
        approved_at=record.approved_at or datetime.now(timezone.utc).isoformat(),
    )
