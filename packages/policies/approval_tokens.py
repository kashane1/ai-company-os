"""Phase 3.1 — magic-link approval tokens.

Approval requests are delivered as a single magic-link URL to the local
approval endpoint (``apps/api/approval_endpoint.py``). The link carries a
fresh HMAC-signed token that is:

- **Short-lived** — ``DEFAULT_TTL`` (30 min) for normal actions, ``P0_TTL``
  (5 min) for App Store submissions, protected-branch merges, billing, DNS.
- **Single-use** — the token burn count is tracked in the token store and
  flips to 1 on first successful confirm. Re-use is rejected.
- **Device-bound** — the confirming device fingerprint is recorded in the
  audit trail alongside the expected fingerprint (if any).
- **Second-factor-gated for P0** — a second click must occur within a
  60-second window of the first confirm. The second click carries its own
  HMAC and burns separately.

The token store is intentionally file-backed and testable (see
``packages/db/approval_token_store.py``). All cryptography is ``hmac``/
``secrets`` from the stdlib; no third-party crypto dependency is added.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
from dataclasses import asdict, dataclass, field, replace
from datetime import datetime, timedelta, timezone
from typing import Literal


ActionClass = Literal["default", "p0"]


DEFAULT_TTL = timedelta(minutes=30)
P0_TTL = timedelta(minutes=5)
P0_SECOND_FACTOR_WINDOW = timedelta(seconds=60)

# Actions that require P0 handling (short TTL + second factor).
P0_ACTIONS: frozenset[str] = frozenset(
    {
        "submit_appstore",
        "submit_testflight",
        "release_to_store",
        "merge_protected_branch",
        "billing_charge",
        "dns_change",
        # Phase 3 — skill self-evolution applies are at least as
        # dangerous as protected-branch merges: the approved diff is
        # canonical skill code that the worker imports on its next
        # run. Security-sentinel H2 on the first Phase 3 PR flagged
        # this as a missing P0 classification. 5-min TTL + second-
        # factor requirement applies.
        "skill_evolution_apply",
    }
)


class ApprovalTokenError(Exception):
    """Base class for approval-token rejection reasons."""


class TokenNotFound(ApprovalTokenError):
    pass


class TokenExpired(ApprovalTokenError):
    pass


class TokenAlreadyBurned(ApprovalTokenError):
    pass


class TokenSignatureInvalid(ApprovalTokenError):
    pass


class SecondFactorRequired(ApprovalTokenError):
    pass


class SecondFactorOutOfWindow(ApprovalTokenError):
    pass


class DeviceMismatch(ApprovalTokenError):
    pass


@dataclass(frozen=True)
class ApprovalToken:
    """Persistent record of a magic-link token.

    The ``token_id`` is the public identifier that appears in the magic-link
    URL path. The ``signature`` is the stdlib HMAC over ``token_id`` using a
    per-repo server secret. Verifying the link is constant-time comparison
    against this signature.
    """

    token_id: str
    signature: str
    approval_id: str
    subject_id: str
    action: str
    action_class: ActionClass
    issued_at: str  # ISO-8601 UTC
    ttl_seconds: int
    expected_device_fingerprint: str | None = None
    burn_count: int = 0
    approved_at: str | None = None
    device_fingerprint: str | None = None
    second_factor_at: str | None = None
    transitions: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> "ApprovalToken":
        return cls(
            token_id=str(payload["token_id"]),
            signature=str(payload["signature"]),
            approval_id=str(payload["approval_id"]),
            subject_id=str(payload["subject_id"]),
            action=str(payload["action"]),
            action_class=str(payload.get("action_class", "default")),  # type: ignore[arg-type]
            issued_at=str(payload["issued_at"]),
            ttl_seconds=int(payload["ttl_seconds"]),
            expected_device_fingerprint=(
                str(payload["expected_device_fingerprint"])
                if payload.get("expected_device_fingerprint")
                else None
            ),
            burn_count=int(payload.get("burn_count", 0)),
            approved_at=(
                str(payload["approved_at"]) if payload.get("approved_at") else None
            ),
            device_fingerprint=(
                str(payload["device_fingerprint"])
                if payload.get("device_fingerprint")
                else None
            ),
            second_factor_at=(
                str(payload["second_factor_at"])
                if payload.get("second_factor_at")
                else None
            ),
            transitions=list(payload.get("transitions", [])),  # type: ignore[arg-type]
        )


def classify_action(action: str) -> ActionClass:
    return "p0" if action in P0_ACTIONS else "default"


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: datetime) -> str:
    return dt.isoformat()


def _parse(dt_iso: str) -> datetime:
    return datetime.fromisoformat(dt_iso)


def _sign(secret: bytes, token_id: str) -> str:
    mac = hmac.new(secret, token_id.encode("utf-8"), hashlib.sha256).digest()
    return base64.urlsafe_b64encode(mac).decode("ascii").rstrip("=")


def _mint_token_id() -> str:
    return secrets.token_urlsafe(32)


def issue_token(
    *,
    approval_id: str,
    subject_id: str,
    action: str,
    secret: bytes,
    store: "ApprovalTokenStoreProtocol",
    expected_device_fingerprint: str | None = None,
    now: datetime | None = None,
) -> ApprovalToken:
    """Mint a fresh magic-link token and persist it."""
    cls = classify_action(action)
    ttl = P0_TTL if cls == "p0" else DEFAULT_TTL
    token_id = _mint_token_id()
    record = ApprovalToken(
        token_id=token_id,
        signature=_sign(secret, token_id),
        approval_id=approval_id,
        subject_id=subject_id,
        action=action,
        action_class=cls,
        issued_at=_iso(now or _now()),
        ttl_seconds=int(ttl.total_seconds()),
        expected_device_fingerprint=expected_device_fingerprint,
        transitions=["issued"],
    )
    store.save(record)
    return record


def verify_and_burn_token(
    *,
    token_id: str,
    provided_signature: str,
    device_fingerprint: str,
    secret: bytes,
    store: "ApprovalTokenStoreProtocol",
    now: datetime | None = None,
) -> ApprovalToken:
    """Validate a magic-link click and burn the token on first use.

    Raises an :class:`ApprovalTokenError` subclass on any failure. On
    success the token's ``burn_count`` is incremented to 1 and its
    ``approved_at`` / ``device_fingerprint`` / ``transitions`` are updated.
    """
    expected_sig = _sign(secret, token_id)
    if not hmac.compare_digest(expected_sig, provided_signature):
        raise TokenSignatureInvalid("signature mismatch")

    try:
        record = store.load(token_id)
    except FileNotFoundError as exc:
        raise TokenNotFound(token_id) from exc

    if not hmac.compare_digest(record.signature, provided_signature):
        raise TokenSignatureInvalid("persisted signature mismatch")

    current_time = now or _now()
    expires_at = _parse(record.issued_at) + timedelta(seconds=record.ttl_seconds)
    if current_time > expires_at:
        raise TokenExpired(f"token expired at {expires_at.isoformat()}")

    if record.burn_count >= 1:
        raise TokenAlreadyBurned(f"burn_count={record.burn_count}")

    if (
        record.expected_device_fingerprint
        and record.expected_device_fingerprint != device_fingerprint
    ):
        raise DeviceMismatch("expected device fingerprint did not match")

    updated = replace(
        record,
        burn_count=1,
        approved_at=_iso(current_time),
        device_fingerprint=device_fingerprint,
        transitions=list(record.transitions) + ["approved"],
    )
    store.save(updated)
    return updated


def record_second_factor(
    *,
    token_id: str,
    provided_signature: str,
    device_fingerprint: str,
    secret: bytes,
    store: "ApprovalTokenStoreProtocol",
    now: datetime | None = None,
) -> ApprovalToken:
    """Record the second-factor confirm click for a P0 token.

    Must be called *after* ``verify_and_burn_token`` and within
    ``P0_SECOND_FACTOR_WINDOW`` of ``approved_at``.
    """
    expected_sig = _sign(secret, token_id)
    if not hmac.compare_digest(expected_sig, provided_signature):
        raise TokenSignatureInvalid("signature mismatch")

    try:
        record = store.load(token_id)
    except FileNotFoundError as exc:
        raise TokenNotFound(token_id) from exc

    if record.action_class != "p0":
        raise ApprovalTokenError("second factor only required for p0 tokens")

    if not record.approved_at:
        raise SecondFactorRequired("primary confirm must land first")

    current_time = now or _now()
    approved_at = _parse(record.approved_at)
    window = current_time - approved_at
    if window > P0_SECOND_FACTOR_WINDOW or window < timedelta(0):
        raise SecondFactorOutOfWindow(
            f"second factor {window.total_seconds():.1f}s outside window"
        )

    if (
        record.expected_device_fingerprint
        and record.expected_device_fingerprint != device_fingerprint
    ):
        raise DeviceMismatch("expected device fingerprint did not match")

    updated = replace(
        record,
        second_factor_at=_iso(current_time),
        transitions=list(record.transitions) + ["second_factor"],
    )
    store.save(updated)
    return updated


class ApprovalTokenStoreProtocol:
    """Structural protocol for the token store.

    Kept as a plain class rather than ``typing.Protocol`` to stay
    importable without a runtime-checkable dependency.
    """

    def save(self, token: ApprovalToken) -> None:  # pragma: no cover - interface
        raise NotImplementedError

    def load(self, token_id: str) -> ApprovalToken:  # pragma: no cover - interface
        raise NotImplementedError

    def list_by_approval(
        self, approval_id: str
    ) -> list[ApprovalToken]:  # pragma: no cover - interface
        raise NotImplementedError
