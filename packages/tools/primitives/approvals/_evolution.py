"""Evolution approval flow: request / poll / submit / reject.

Split out of the original single-file ``approvals`` module. Behaviour is
unchanged. Re-exported from ``approvals/__init__.py``.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from packages.db.approval_store import ApprovalStore
from packages.db.approval_token_store import ApprovalTokenStore
from packages.policies.approval_tokens import (
    ApprovalToken,
    TokenNotFound,
    TokenSignatureInvalid,
    issue_token,
    verify_and_burn_token,
)
from packages.schemas.approval import ApprovalRecord, ApprovalStatus
from packages.tools.primitives.approvals._models import (
    SKILL_EVOLUTION_ACTION,
    SKILL_EVOLUTION_APPROVAL_TYPE,
    ApprovalDecision,
    ApprovalOutcome,
    ApprovalRequest,
)
from packages.tools.primitives.approvals._signing import _load_signing_secret

# ---------------------------------------------------------------------- #
# Writer — called by the worker before it blocks on human review          #
# ---------------------------------------------------------------------- #


def request_evolution_approval(
    *,
    proposal_id: str,
    target_skill_id: str,
    rationale: str,
    artifact_dir: Path,
    expected_device_fingerprint: str | None = None,
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

    # Bind the expected device fingerprint at issue time so the
    # burn-side check in ``verify_and_burn_token`` actually fires.
    # Security-sentinel H1 on the first Phase 3 PR: the earlier
    # version left ``expected_device_fingerprint=None``, which
    # short-circuited the burn-side check and accepted any device.
    # Default to the issuing host so a reviewer signing from the
    # same box satisfies the check without manual configuration;
    # callers can override to enforce a different device.
    binding = expected_device_fingerprint or _default_device_binding()
    secret = _load_signing_secret()
    token = issue_token(
        approval_id=approval_id,
        subject_id=target_skill_id,
        action=SKILL_EVOLUTION_ACTION,
        secret=secret,
        store=tokens,
        expected_device_fingerprint=binding,
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

    # Pre-flight: load the token and verify the approval_id BEFORE
    # calling verify_and_burn_token. The underlying burn is a
    # read-modify-write that persists ``burn_count=1`` BEFORE this
    # wrapper would have had a chance to reject on approval_id
    # mismatch — which, pre-fix, meant an attacker (or a CLI bug)
    # could permanently burn a legitimate token by submitting with
    # a wrong approval_id, DoS'ing the real reviewer. Blocker #2 from
    # the kieran-python review of the first Phase 3 PR.
    try:
        pre_check = tokens.load(token_id)
    except FileNotFoundError as exc:
        raise TokenNotFound(token_id) from exc
    if pre_check.approval_id != approval_id:
        raise TokenSignatureInvalid(
            f"token approval_id {pre_check.approval_id!r} != "
            f"{approval_id!r} — refusing to burn"
        )

    # Raises on any HMAC/burn/expiry failure; re-raised to the CLI.
    burned: ApprovalToken = verify_and_burn_token(
        token_id=token_id,
        provided_signature=provided_signature,
        device_fingerprint=device_fingerprint,
        secret=secret,
        store=tokens,
    )
    # Defensive post-check — should be a tautology after the pre-check
    # above. Kept so a future refactor that drops the pre-check fails
    # loudly instead of silently.
    if burned.approval_id != approval_id:  # pragma: no cover
        raise TokenSignatureInvalid(
            f"post-burn approval_id {burned.approval_id!r} != {approval_id!r}"
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


# NOTE: the public `__all__` lives in this package's __init__.py (it spans all
# three submodules). The flat module's mid-file __all__ was intentionally dropped
# here during the split — keeping it would (wrongly) scope `import *` on this
# submodule to names it doesn't define.


# ---------------------------------------------------------------------- #
# Internals                                                               #
# ---------------------------------------------------------------------- #


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _default_device_binding() -> str:
    """Hostname as a default device fingerprint for token issue.

    A reviewer signing from the same host the worker ran on passes
    the binding check without any manual wiring; a reviewer signing
    from elsewhere must explicitly override both
    ``expected_device_fingerprint`` (at issue time) and
    ``--device`` on the CLI (at burn time). This is the minimum
    viable binding — a hostname is trivially spoofable by a
    process running on a different host, but defends against the
    "stolen signature file, replayed from a different machine"
    scenario that matters most against the Phase 3 threat model.
    """
    import socket

    return socket.gethostname() or "unknown-host"


# ---------------------------------------------------------------------- #
# Keychain error taxonomy                                                 #
# ---------------------------------------------------------------------- #


