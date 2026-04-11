"""Phase 3.1 — local magic-link approval endpoint.

A tiny FastAPI ``APIRouter`` that exposes:

- ``GET /approvals/{token_id}`` — renders a one-page confirm screen with a
  form that POSTs the signature back to the endpoint. No auth beyond
  possession of the token and a localhost bind.
- ``POST /approvals/{token_id}/confirm`` — verifies and burns the token,
  moves the referenced :class:`ApprovalRecord` to ``approved``.
- ``POST /approvals/{token_id}/second-factor`` — second-click window for
  P0 actions (App Store submission, protected-branch merge, billing, DNS).

Kashane runs this on his Mac. Remote approvals are explicitly out of scope
for Phase 3. The endpoint should only ever be mounted on ``127.0.0.1``.
"""

from __future__ import annotations

import os
from datetime import datetime, timezone

from fastapi import APIRouter, Form, HTTPException
from fastapi.responses import HTMLResponse
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


APPROVAL_SECRET_ENV_VAR = "AI_COMPANY_OS_APPROVAL_SECRET"


def get_secret() -> bytes:
    """Load the HMAC secret from the environment.

    Production loads this via ``packages.config.secrets.get_secret`` from
    macOS Keychain (Phase 0.4). Tests inject it via ``monkeypatch.setenv``.
    """
    raw = os.environ.get(APPROVAL_SECRET_ENV_VAR)
    if not raw:
        raise HTTPException(
            status_code=503,
            detail="approval secret not configured",
        )
    return raw.encode("utf-8")


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
  <form method="post" action="/approvals/{token_id}/confirm">
    <input type="hidden" name="signature" value="{signature}">
    <input type="hidden" name="device_fingerprint" value="mac-local">
    <button type="submit">Confirm</button>
  </form>
</body>
</html>
"""


@router.get("/{token_id}", response_class=HTMLResponse)
def render_confirm_page(token_id: str) -> HTMLResponse:
    store = ApprovalTokenStore()
    try:
        token = store.load(token_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="token not found") from exc
    html = _CONFIRM_HTML.format(
        token_id=token_id,
        action=token.action,
        subject_id=token.subject_id,
        approval_id=token.approval_id,
        action_class=token.action_class,
        issued_at=token.issued_at,
        ttl_seconds=token.ttl_seconds,
        signature=token.signature,
    )
    return HTMLResponse(content=html)


@router.post("/{token_id}/confirm", response_model=ConfirmResponse)
def confirm_token(
    token_id: str,
    signature: str = Form(...),
    device_fingerprint: str = Form(...),
) -> ConfirmResponse:
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
