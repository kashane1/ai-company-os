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
import sys
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

# When set, skips the macOS Keychain read path and goes straight to
# the filesystem fallback. Intended for CI (non-macOS runners) and
# for hermetic unit tests that need to exercise the filesystem code
# without touching the real user Keychain. Never set this in
# production on a Mac — the whole point of the Keychain migration
# is that the filesystem path is no longer defensible under the
# Phase 3 same-uid threat model.
FORCE_FILE_ENV_VAR = "AI_COMPANY_OS_APPROVAL_KEY_FORCE_FILE"

# macOS Keychain item identity. The "service" field is what
# ``security find-generic-password -s`` looks up; the "account" field
# is what ``-a`` matches. Both are scoped to the user's login
# keychain by default, which is what we want — the system keychain
# would require root.
KEYCHAIN_SERVICE = "ai-company-os"
KEYCHAIN_ACCOUNT = "approval_signing_key"


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
    "KeychainError",
    "KeychainNotFound",
    "KeychainAccessDenied",
    "KeychainAlreadyExists",
    "SKILL_EVOLUTION_ACTION",
    "SKILL_EVOLUTION_APPROVAL_TYPE",
    "KEYCHAIN_SERVICE",
    "KEYCHAIN_ACCOUNT",
    "FORCE_FILE_ENV_VAR",
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


class KeychainError(RuntimeError):
    """Base class for macOS Keychain interaction failures."""


class KeychainNotFound(KeychainError):
    """The Keychain item (service, account) does not exist.

    Typically means the operator hasn't run ``bootstrap-keychain`` on
    this machine yet. Distinct from access-denied because the
    resolution is different (bootstrap vs. fix the ACL).
    """


class KeychainAccessDenied(KeychainError):
    """The Keychain item exists but this process is not on its ACL.

    This is the expected-and-good failure mode when a compromised
    sibling worker runs from an unexpected binary and tries to read
    the signing key. :func:`_load_signing_secret` deliberately
    refuses to fall through to the filesystem path in this case —
    silent fallback would undo the point of the migration.
    """


class KeychainAlreadyExists(KeychainError):
    """Bootstrap refused to overwrite an existing item.

    Rotation uses :func:`_rotate_keychain_secret` (delete + create).
    A plain ``bootstrap-keychain`` call refuses to clobber so the
    operator has to make rotation an explicit action.
    """


# ---------------------------------------------------------------------- #
# Signing secret resolution                                               #
# ---------------------------------------------------------------------- #


def _load_signing_secret() -> bytes:
    """Resolve the HMAC secret used to sign + verify approval tokens.

    Resolution order:

    1. ``AI_COMPANY_OS_APPROVAL_SIGNING_KEY`` env var — hex-encoded,
       must decode to at least 32 bytes after stripping whitespace.
       Empty / whitespace-only / non-hex input all raise. Highest
       precedence so CI and hermetic unit tests stay platform-
       independent without touching any real secret store.

    2. **macOS: Keychain** (generic-password item at
       ``service=ai-company-os``, ``account=approval_signing_key``).
       Read via ``security find-generic-password -w``. The Keychain
       item is bootstrapped by ``approval-reviewer bootstrap-keychain``
       with a binary ACL that names only the specific Python
       interpreter and CLI binaries allowed to read it without a
       user prompt. A same-uid compromised sibling worker run from an
       unexpected path is denied by Keychain Services out-of-process.

       On :class:`KeychainNotFound`, the function raises with an
       operator-facing hint to run ``bootstrap-keychain``. On
       :class:`KeychainAccessDenied`, it raises WITHOUT falling
       through to the filesystem — silent fallback would let a
       compromised caller bypass the ACL by letting Keychain deny
       and then reading the filesystem key. The operator must
       explicitly add the denied binary to the ACL, or set
       ``AI_COMPANY_OS_APPROVAL_KEY_FORCE_FILE=1`` to acknowledge
       they want the filesystem path.

    3. **Non-macOS or ``AI_COMPANY_OS_APPROVAL_KEY_FORCE_FILE=1``:
       filesystem fallback.** File at
       ``state/checkpoints/platform/approval_signing_key``, owner-only
       (mode 0600), atomic exclusive bootstrap via
       ``O_CREAT|O_EXCL|O_WRONLY|O_NOFOLLOW``. The symlink / race /
       mode hardening from the previous Phase 3 PR is preserved.

    Threat-model delta vs. the previous filesystem-only version
    (security-sentinel C1 on PR #8):

    - **Before:** a same-uid compromised process could read the
      signing key via ``os.open(..., O_NOFOLLOW)`` and sign
      arbitrary tokens. The HMAC gate was decoration against that
      threat.
    - **After:** same-uid reads go through Keychain Services, which
      enforces a binary-path ACL out-of-process. A process run from
      a path not on the ACL gets denied even at the same uid.

    See ``docs/plans/2026-04-15-macos-keychain-approval-signing-migration.md``
    for the full migration plan and the list of open questions that
    did NOT fit in this landing (notably: signature-at-rest, which
    is a separate follow-up).
    """
    raw = os.environ.get(SIGNING_KEY_ENV_VAR)
    if raw is not None:
        return _decode_env_secret(raw)

    if _keychain_is_preferred():
        try:
            return _read_keychain_secret()
        except KeychainNotFound as exc:
            raise RuntimeError(
                "Approval signing key not found in macOS Keychain. "
                "Run `.venv/bin/python apps/approval-reviewer/main.py "
                "bootstrap-keychain` once on this machine to create it, "
                "then retry. See "
                "docs/plans/2026-04-15-macos-keychain-approval-signing-migration.md "
                "for the full procedure."
            ) from exc
        except KeychainAccessDenied as exc:
            raise RuntimeError(
                "Refusing to sign with filesystem fallback: Keychain "
                "access denied for this process. If this process is "
                "legitimately allowed to sign approval tokens, re-run "
                "`bootstrap-keychain` and include this binary in the "
                "ACL. Filesystem fallback is intentionally disabled on "
                "macOS to preserve the Phase 3 threat-model guarantees. "
                f"Underlying error: {exc}"
            ) from exc

    return _read_filesystem_secret()


def _decode_env_secret(raw: str) -> bytes:
    """Validate and decode the hex-encoded signing secret from env."""
    stripped = raw.strip()
    if not stripped:
        raise ValueError(
            f"{SIGNING_KEY_ENV_VAR} is empty or whitespace-only; "
            f"unset it or provide a hex-encoded 32+ byte key"
        )
    try:
        secret = bytes.fromhex(stripped)
    except ValueError as exc:
        raise ValueError(
            f"{SIGNING_KEY_ENV_VAR} is not valid hex: {exc}"
        ) from exc
    if len(secret) < 32:
        raise ValueError(
            f"{SIGNING_KEY_ENV_VAR} decoded to {len(secret)} bytes; "
            f"minimum is 32 (256 bits)"
        )
    return secret


def _keychain_is_preferred() -> bool:
    """True iff this platform should read the signing secret from
    Keychain. macOS only, unless the force-file override is set."""
    if sys.platform != "darwin":
        return False
    if os.environ.get(FORCE_FILE_ENV_VAR):
        return False
    return True


def _read_keychain_secret() -> bytes:
    """Read the generic-password item from the login keychain.

    Shells out to ``/usr/bin/security`` with ``find-generic-password
    -w`` to print the raw password to stdout. Decodes the printed hex
    back to bytes. Raises :class:`KeychainNotFound` on exit code 44
    (errSecItemNotFound), :class:`KeychainAccessDenied` on any other
    non-zero exit with stderr matching known access-denied markers,
    :class:`KeychainError` otherwise.

    ``subprocess`` is lazy-imported inside the function body to
    satisfy the primitives subpackage's "no top-level subprocess
    import" convention (AST-enforced by
    ``test_primitives_conventions.py``).
    """
    import subprocess

    try:
        result = subprocess.run(
            [
                "/usr/bin/security",
                "find-generic-password",
                "-s",
                KEYCHAIN_SERVICE,
                "-a",
                KEYCHAIN_ACCOUNT,
                "-w",
            ],
            capture_output=True,
            text=True,
            timeout=10.0,
        )
    except FileNotFoundError as exc:
        raise KeychainError(
            f"/usr/bin/security not available ({exc}); is this macOS?"
        ) from exc
    except subprocess.TimeoutExpired as exc:
        raise KeychainError(
            f"keychain lookup timed out after {exc.timeout}s"
        ) from exc

    if result.returncode == 0:
        printed = result.stdout.strip()
        if not printed:
            raise KeychainError(
                "keychain returned exit 0 but no payload"
            )
        return _decode_env_secret(printed)

    # Non-zero. errSecItemNotFound is 44 on modern macOS, 25293 on
    # some older releases. Treat both as KeychainNotFound.
    if result.returncode in (44, 25293):
        raise KeychainNotFound(
            f"{KEYCHAIN_SERVICE}/{KEYCHAIN_ACCOUNT} not found in "
            f"login keychain"
        )

    stderr = result.stderr or ""
    if _is_access_denied_stderr(stderr):
        raise KeychainAccessDenied(
            f"keychain access denied: {stderr.strip()}"
        )
    raise KeychainError(
        f"/usr/bin/security exited {result.returncode}: {stderr.strip()}"
    )


def _is_access_denied_stderr(stderr: str) -> bool:
    """Match the known access-denied error markers from
    ``/usr/bin/security``.

    The CLI doesn't expose a stable exit code for "item exists but
    the caller isn't on the ACL" — it returns whatever OSStatus the
    underlying SecKeychainItemCopyContent call produces, which
    varies across macOS versions. Matching on stderr text is
    fragile but it's the only option stdlib gives us. The markers
    below come from the macOS Sonoma + Tahoe ``security(1)`` output.
    """
    lowered = stderr.lower()
    markers = (
        "interaction is not allowed",
        "user interaction is not allowed",
        "authorization",
        "not authorized",
        "operation not permitted",
        "-25308",  # errSecInteractionNotAllowed
        "-128",    # userCanceledErr
    )
    return any(m in lowered for m in markers)


def _bootstrap_keychain_secret(
    *, trusted_binaries: list[str] | None = None
) -> bytes:
    """Create a fresh Keychain item with the signing secret.

    Refuses to clobber an existing item — callers that want to rotate
    must call :func:`_delete_keychain_secret` first. ``trusted_binaries``
    adds ``-T /path/to/bin`` entries to the ACL; if empty, the operator
    will be prompted on every read (which is the wrong default for a
    worker running under launchd — always pass at least the venv python
    and the approval-reviewer entrypoint).

    Returns the 32-byte secret (hex-decoded from the stored value).
    """
    import subprocess

    # Check first — security add-generic-password will happily
    # overwrite with -U, which is exactly what we want to prevent.
    try:
        _read_keychain_secret()
    except KeychainNotFound:
        pass
    else:
        raise KeychainAlreadyExists(
            f"{KEYCHAIN_SERVICE}/{KEYCHAIN_ACCOUNT} already exists in "
            f"the login keychain. Use rotate-keychain to replace it, "
            f"or delete it manually via "
            f"`security delete-generic-password -s {KEYCHAIN_SERVICE} "
            f"-a {KEYCHAIN_ACCOUNT}`."
        )

    secret_hex = secrets.token_bytes(32).hex()
    cmd = [
        "/usr/bin/security",
        "add-generic-password",
        "-s",
        KEYCHAIN_SERVICE,
        "-a",
        KEYCHAIN_ACCOUNT,
        "-w",
        secret_hex,
        "-D",
        "ai-company-os approval signing key",
    ]
    for binary in trusted_binaries or []:
        cmd.extend(["-T", binary])

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=10.0,
    )
    if result.returncode != 0:
        raise KeychainError(
            f"failed to bootstrap keychain item: "
            f"exit={result.returncode} stderr={result.stderr.strip()}"
        )
    return bytes.fromhex(secret_hex)


def _delete_keychain_secret() -> None:
    """Remove the Keychain item, if present. Idempotent — a missing
    item is not an error (matches ``rm -f`` semantics). Any other
    non-zero exit raises :class:`KeychainError`.
    """
    import subprocess

    result = subprocess.run(
        [
            "/usr/bin/security",
            "delete-generic-password",
            "-s",
            KEYCHAIN_SERVICE,
            "-a",
            KEYCHAIN_ACCOUNT,
        ],
        capture_output=True,
        text=True,
        timeout=10.0,
    )
    if result.returncode == 0:
        return
    if result.returncode in (44, 25293):
        return  # already gone
    raise KeychainError(
        f"failed to delete keychain item: "
        f"exit={result.returncode} stderr={result.stderr.strip()}"
    )


def _rotate_keychain_secret(
    *, trusted_binaries: list[str] | None = None
) -> bytes:
    """Delete the existing Keychain item and bootstrap a fresh one.

    Every outstanding unburned token is permanently invalidated by
    rotation because the HMAC key has changed — workers blocked on
    approvals will start seeing signature-mismatch errors on their
    next poll. That's the intended behavior; operators MUST
    re-enqueue those proposals after rotating.
    """
    _delete_keychain_secret()
    return _bootstrap_keychain_secret(trusted_binaries=trusted_binaries)


# ---------------------------------------------------------------------- #
# Filesystem fallback — unchanged hardening from PR #8                    #
# ---------------------------------------------------------------------- #


def _read_filesystem_secret() -> bytes:
    """Read the signing secret from the hardened filesystem path,
    bootstrapping it atomically on first use.

    This is the non-macOS path and the explicit-override escape hatch
    (``AI_COMPANY_OS_APPROVAL_KEY_FORCE_FILE=1``). Production macOS
    should never reach this branch — :func:`_load_signing_secret`
    routes to Keychain and refuses to fall through on access-denied.
    All the hardening from PR #8 is preserved verbatim: symlink
    refusal via ``O_NOFOLLOW``, atomic bootstrap via ``O_CREAT|O_EXCL``,
    mode 0600 enforced on both write (atomic at create) and read
    (via ``fstat``), and minimum 32-byte length.
    """
    paths = load_runtime_paths()
    key_path = paths.platform_state_root / "approval_signing_key"

    try:
        read_fd = os.open(
            os.fspath(key_path),
            os.O_RDONLY | os.O_NOFOLLOW,
        )
    except FileNotFoundError:
        read_fd = None
    except OSError as exc:
        raise RuntimeError(
            f"refusing to load approval signing key from {key_path}: "
            f"path is a symlink or otherwise unsafe ({exc})"
        ) from exc

    if read_fd is not None:
        try:
            st = os.fstat(read_fd)
            if st.st_mode & 0o077:
                raise RuntimeError(
                    f"refusing to load approval signing key from "
                    f"{key_path}: mode {oct(st.st_mode & 0o777)} has "
                    f"group/world permissions; expected 0600"
                )
            secret_from_file = os.read(read_fd, 4096)
        finally:
            os.close(read_fd)
        if len(secret_from_file) < 32:
            raise RuntimeError(
                f"approval signing key at {key_path} is "
                f"{len(secret_from_file)} bytes; minimum is 32"
            )
        return secret_from_file

    # Bootstrap path — atomic exclusive create with strict mode.
    key_path.parent.mkdir(parents=True, exist_ok=True)
    secret = secrets.token_bytes(32)
    try:
        bootstrap_fd = os.open(
            os.fspath(key_path),
            os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_NOFOLLOW,
            0o600,
        )
    except FileExistsError:
        return _read_filesystem_secret()

    try:
        os.write(bootstrap_fd, secret)
    finally:
        os.close(bootstrap_fd)
    return secret
