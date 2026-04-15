"""Agent-callable approval primitives (Phase 3, Option B).

This module wraps the existing Phase 3.1 HMAC approval-token infrastructure
(:mod:`packages.policies.approval_tokens` +
:class:`packages.db.approval_token_store.ApprovalTokenStore` +
:class:`packages.db.approval_store.ApprovalStore`) in a shape that the
skill-self-evolution worker — and any other agent that needs a human
gate in front of an action — can consume through a narrow, typed API.

Design contract (per ``packages/tools/primitives/__init__.py``):

1. **Stateless at module level.** No caches, no module-level opens.
2. **Side-effect-free to import.** No I/O until a public function is
   called. AST-checked by ``test_primitives_conventions.py``.
3. **Typed returns.** Frozen dataclass :class:`ApprovalRequest` at the
   write boundary; :class:`ApprovalDecision` at the read boundary.
4. **Single operations only.** Each public function is one step.
   Polling / backoff is the worker's job, not this module's.

Why Option B and not a GitHub PR layer?

The PR layer was explicitly deferred in the Phase 3 scope decision —
see the conversation that launched this branch. The primitive lives
here first because the *approval token* is the load-bearing abstraction
for Phases 3, 5, and 6. A PR layer can be added later as a thin skin
over the same token flow without rewriting callers.

State layout
------------

Every approval request lands in **two** stores:

- :class:`ApprovalStore` — the canonical :class:`ApprovalRecord` used
  by the rest of the platform (release_readiness, command_scan, etc.).
- :class:`ApprovalTokenStore` — the HMAC-signed magic-link token that
  the reviewer burns when signing off. One token per approval.

Splitting the state means the rest of the platform's consumers of
``is_approval_granted`` keep working unchanged. The token store adds
the HMAC gate on top.

Proposal artifacts (the diff, the rationale, the input snapshot) live
under ``state/artifacts/skill-evolution/<proposal_id>/`` — those are
written by the worker, not by this module. This module persists just
enough metadata to let a reviewer locate the artifacts.

Secret handling
---------------

The HMAC signing secret comes from :func:`_load_signing_secret` which
reads:

1. The ``AI_COMPANY_OS_APPROVAL_SIGNING_KEY`` environment variable, if set
2. Otherwise, a machine-local file at
   ``state/checkpoints/platform/approval_signing_key`` that is:
   - Gitignored (the whole ``state/checkpoints/`` tree is gitignored)
   - Mode 0600
   - Populated on first call with ``secrets.token_bytes(32)`` if missing

This is the minimum viable secret bootstrap. A macOS Keychain-backed
version is a follow-up — the contract is small enough that swapping
out :func:`_load_signing_secret` is a one-place change.
"""

from __future__ import annotations

import os
import secrets
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from packages.config.settings import load_runtime_paths
from packages.db.approval_store import ApprovalStore
from packages.db.approval_token_store import ApprovalTokenStore
from packages.policies.approval_tokens import (
    ApprovalToken,
    ApprovalTokenError,
    TokenAlreadyBurned,
    TokenExpired,
    TokenNotFound,
    TokenSignatureInvalid,
    issue_token,
    verify_and_burn_token,
)
from packages.schemas.approval import ApprovalRecord, ApprovalStatus


# Action string stamped on skill-evolution approval requests. Keep in
# sync with the matching reader in
# ``packages/policies/skill_evolution.py:_EVOLUTION_APPROVAL_ACTION``.
SKILL_EVOLUTION_ACTION = "skill_evolution_apply"

# Approval record type (used by ``is_approval_granted``). Workers and
# policies test against this string so any drift is a loud failure,
# not a silent mismatch.
SKILL_EVOLUTION_APPROVAL_TYPE = "skill_evolution"

SIGNING_KEY_ENV_VAR = "AI_COMPANY_OS_APPROVAL_SIGNING_KEY"


ApprovalOutcome = Literal["pending", "approved", "rejected", "expired"]


@dataclass(frozen=True)
class ApprovalRequest:
    """Return value of :func:`request_evolution_approval`.

    The reviewer needs the ``token_id`` + ``signature`` pair to sign;
    the worker needs the ``approval_id`` to poll on. Everything else
    exists for auditing.
    """

    approval_id: str
    token_id: str
    signature: str
    action: str
    subject_id: str
    artifact_dir: str
    created_at: str


@dataclass(frozen=True)
class ApprovalDecision:
    """Return value of :func:`poll_evolution_approval`.

    ``outcome`` is the single field callers normally branch on.
    """

    approval_id: str
    outcome: ApprovalOutcome
    decided_by: str | None
    decided_at: str | None
    decision_notes: str | None


# ---------------------------------------------------------------------- #
# Writer — called by the worker before it blocks on human review          #
# ---------------------------------------------------------------------- #


def request_evolution_approval(
    *,
    proposal_id: str,
    target_skill_id: str,
    rationale: str,
    artifact_dir: Path,
    task_id: str | None = None,
    task_run_id: str | None = None,
    approval_store: ApprovalStore | None = None,
    token_store: ApprovalTokenStore | None = None,
) -> ApprovalRequest:
    """Persist a pending approval record + HMAC token for a staged
    skill-evolution proposal, and return the identifiers needed to
    poll and sign.

    After this function returns, the worker should transition its task
    to ``BLOCKED`` and poll via :func:`poll_evolution_approval` on a
    backoff until the outcome flips.

    ``artifact_dir`` MUST already contain the proposal artifacts
    (diff, input snapshot, rationale rendered for a reviewer). This
    module does NOT write them — the worker stages them first and
    passes the path for the record.

    The ``rationale`` string is a short human-readable reason that the
    reviewer sees first when listing pending approvals. The full
    artifact dir contents are the detailed review surface.
    """
    if not artifact_dir.exists():
        raise FileNotFoundError(
            f"approval artifact_dir does not exist: {artifact_dir}"
        )
    if not artifact_dir.is_dir():
        raise NotADirectoryError(
            f"approval artifact_dir is not a directory: {artifact_dir}"
        )

    approvals = approval_store or ApprovalStore()
    tokens = token_store or ApprovalTokenStore()

    approval_id = f"skill-evo-{proposal_id}"
    created_at = _now_iso()
    record = ApprovalRecord(
        id=approval_id,
        status=ApprovalStatus.PENDING,
        summary=rationale,
        created_at=created_at,
        task_id=task_id,
        task_run_id=task_run_id,
        approval_type=SKILL_EVOLUTION_APPROVAL_TYPE,
        review_artifact_path=str(artifact_dir),
        subject_type="skill_evolution_proposal",
        subject_id=target_skill_id,
        action=SKILL_EVOLUTION_ACTION,
    )
    approvals.save(record)

    secret = _load_signing_secret()
    token = issue_token(
        approval_id=approval_id,
        subject_id=target_skill_id,
        action=SKILL_EVOLUTION_ACTION,
        secret=secret,
        store=tokens,
    )

    return ApprovalRequest(
        approval_id=approval_id,
        token_id=token.token_id,
        signature=token.signature,
        action=SKILL_EVOLUTION_ACTION,
        subject_id=target_skill_id,
        artifact_dir=str(artifact_dir),
        created_at=created_at,
    )


# ---------------------------------------------------------------------- #
# Reader — called by the worker while blocked, and by the CLI reviewer    #
# ---------------------------------------------------------------------- #


def poll_evolution_approval(
    *,
    approval_id: str,
    approval_store: ApprovalStore | None = None,
) -> ApprovalDecision:
    """Return the current decision state for an approval record.

    Never raises for a missing record — returns a ``pending`` outcome
    so the worker's poll loop has a single code path. A truly missing
    approval_id is an out-of-band failure that should surface as a
    worker exception, but not from this read call.
    """
    store = approval_store or ApprovalStore()
    try:
        record = store.load(approval_id)
    except FileNotFoundError:
        return ApprovalDecision(
            approval_id=approval_id,
            outcome="pending",
            decided_by=None,
            decided_at=None,
            decision_notes=None,
        )

    outcome: ApprovalOutcome
    if record.status is ApprovalStatus.APPROVED:
        outcome = "approved"
    elif record.status is ApprovalStatus.REJECTED:
        outcome = "rejected"
    else:
        outcome = "pending"
    return ApprovalDecision(
        approval_id=approval_id,
        outcome=outcome,
        decided_by=record.decided_by,
        decided_at=record.decided_at,
        decision_notes=record.decision_notes,
    )


# ---------------------------------------------------------------------- #
# Reviewer writer — called by the approval-reviewer CLI on sign-off       #
# ---------------------------------------------------------------------- #


def submit_evolution_approval(
    *,
    approval_id: str,
    token_id: str,
    provided_signature: str,
    device_fingerprint: str,
    decided_by: str,
    decision_notes: str | None = None,
    approval_store: ApprovalStore | None = None,
    token_store: ApprovalTokenStore | None = None,
) -> ApprovalDecision:
    """Verify a reviewer's HMAC signature and, on success, flip the
    underlying :class:`ApprovalRecord` to ``approved``.

    On any token failure (missing, signature mismatch, already burned,
    expired), the approval record is left untouched and the underlying
    :class:`ApprovalTokenError` is re-raised so the CLI can render a
    targeted error message.

    After this function returns ``outcome=approved``, the worker's next
    poll will see the new status and proceed to apply the staged diff.
    """
    secret = _load_signing_secret()
    tokens = token_store or ApprovalTokenStore()
    approvals = approval_store or ApprovalStore()

    # Raises on any HMAC/burn/expiry failure; re-raised to the CLI.
    burned: ApprovalToken = verify_and_burn_token(
        token_id=token_id,
        provided_signature=provided_signature,
        device_fingerprint=device_fingerprint,
        secret=secret,
        store=tokens,
    )
    if burned.approval_id != approval_id:
        raise TokenSignatureInvalid(
            f"token approval_id {burned.approval_id!r} != {approval_id!r}"
        )

    updated = approvals.update_status(
        approval_id,
        ApprovalStatus.APPROVED,
        decided_by=decided_by,
        decided_at=_now_iso(),
        decision_notes=decision_notes,
    )
    return ApprovalDecision(
        approval_id=approval_id,
        outcome="approved",
        decided_by=updated.decided_by,
        decided_at=updated.decided_at,
        decision_notes=updated.decision_notes,
    )


def reject_evolution_approval(
    *,
    approval_id: str,
    decided_by: str,
    decision_notes: str | None = None,
    approval_store: ApprovalStore | None = None,
) -> ApprovalDecision:
    """Mark the approval record as rejected without burning the token.

    Rejection is authority-only (no HMAC check) because the reviewer
    is already trusted to make the call — the HMAC gate exists to
    defend against forged approvals, not forged rejections. A forged
    rejection just causes a worker to give up and re-queue, which is
    the same failure mode as a reviewer doing nothing.
    """
    approvals = approval_store or ApprovalStore()
    updated = approvals.update_status(
        approval_id,
        ApprovalStatus.REJECTED,
        decided_by=decided_by,
        decided_at=_now_iso(),
        decision_notes=decision_notes,
    )
    return ApprovalDecision(
        approval_id=approval_id,
        outcome="rejected",
        decided_by=updated.decided_by,
        decided_at=updated.decided_at,
        decision_notes=updated.decision_notes,
    )


# ---------------------------------------------------------------------- #
# Error re-exports — so callers don't import two modules                  #
# ---------------------------------------------------------------------- #

__all__ = [
    "ApprovalRequest",
    "ApprovalDecision",
    "ApprovalOutcome",
    "ApprovalTokenError",
    "TokenAlreadyBurned",
    "TokenExpired",
    "TokenNotFound",
    "TokenSignatureInvalid",
    "SKILL_EVOLUTION_ACTION",
    "SKILL_EVOLUTION_APPROVAL_TYPE",
    "request_evolution_approval",
    "poll_evolution_approval",
    "submit_evolution_approval",
    "reject_evolution_approval",
]


# ---------------------------------------------------------------------- #
# Internals                                                               #
# ---------------------------------------------------------------------- #


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_signing_secret() -> bytes:
    """Resolve the HMAC secret used to sign + verify approval tokens.

    Precedence:

    1. ``AI_COMPANY_OS_APPROVAL_SIGNING_KEY`` env var (hex-encoded).
    2. ``state/checkpoints/platform/approval_signing_key`` file.
    3. First-call bootstrap: generate a fresh 32-byte key, write it
       with mode 0600, return it.

    The hex form in env is to keep `.env` files plaintext-friendly.
    """
    raw = os.environ.get(SIGNING_KEY_ENV_VAR)
    if raw:
        return bytes.fromhex(raw.strip())

    paths = load_runtime_paths()
    key_path = paths.platform_state_root / "approval_signing_key"
    if key_path.exists():
        return key_path.read_bytes()

    key_path.parent.mkdir(parents=True, exist_ok=True)
    secret = secrets.token_bytes(32)
    key_path.write_bytes(secret)
    # 0600 — no group/world read. On macOS this is the same as the
    # Keychain-less fallback for .env and is sufficient for local dev.
    os.chmod(key_path, 0o600)
    return secret
