"""HMAC signing-secret loading: env var, macOS Keychain, filesystem fallback.

Split out of the original single-file ``approvals`` module. Behaviour is
unchanged. Re-exported from ``approvals/__init__.py``.
"""
from __future__ import annotations

import os
import secrets
import sys

from packages.config.settings import load_runtime_paths

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


class KeychainUserCancelled(KeychainError):
    """The user clicked Deny / Cancel on the Keychain dialog.

    Distinct from :class:`KeychainAccessDenied` because the recovery
    path is different: the fix is to re-run the verify command in a
    terminal and click "Always Allow" on the dialog, not to re-run
    ``bootstrap-keychain``. Raised when stderr contains
    ``-128`` / ``userCanceledErr``.
    """


class KeychainAlreadyExists(KeychainError):
    """Bootstrap refused to overwrite an existing item.

    Rotation uses :func:`_rotate_keychain_secret` (which inlines
    the delete step and then calls the bootstrap path). A plain
    ``bootstrap-keychain`` call refuses to clobber so the operator
    has to make rotation an explicit action with its own
    ``--confirm rotate`` gate.
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

    # Keychain path — macOS only, unless the FORCE_FILE escape hatch
    # is set. Inlined from the old _keychain_is_preferred() helper
    # because one call site and three lines don't earn their
    # indirection. (Simplicity review item on PR #9.)
    if sys.platform == "darwin" and not os.environ.get(FORCE_FILE_ENV_VAR):
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
        except KeychainUserCancelled as exc:
            raise RuntimeError(
                "Keychain dialog was cancelled. Run this command in a "
                "terminal and click 'Always Allow' on the dialog: "
                f"`security find-generic-password -s {KEYCHAIN_SERVICE} "
                f"-a {KEYCHAIN_ACCOUNT} -w`. That persists the choice "
                "so subsequent reads are silent. Underlying error: "
                f"{exc}"
            ) from exc
        except KeychainAccessDenied as exc:
            raise RuntimeError(
                "Refusing to sign with filesystem fallback: Keychain "
                "access denied for this process. If this process is "
                "legitimately allowed to sign approval tokens, re-run "
                "`bootstrap-keychain` and include this binary in the "
                "ACL, or click 'Always Allow' on the Keychain dialog "
                "the next time you run the verify command in a TTY. "
                "Filesystem fallback is intentionally disabled on "
                "macOS to preserve the Phase 3 threat-model guarantees. "
                f"Underlying error: {exc}"
            ) from exc
        except KeychainError as exc:
            # Catch-all for `/usr/bin/security` failures that aren't
            # cleanly classified (timeout, missing binary, unrecognized
            # non-zero exit, malformed stdout). Security-sentinel H1
            # on PR #9: the security invariant holds (no silent
            # fallback) because we re-raise, but the error message
            # needs to be operator-actionable, not raw subprocess
            # diagnostics.
            raise RuntimeError(
                "Unable to read approval signing key from macOS "
                "Keychain, and filesystem fallback is intentionally "
                "disabled on macOS. If this is the first read on a "
                "new machine and you're seeing a dialog-related error, "
                "run the verify command in a terminal and click "
                "'Always Allow'. If your Keychain daemon is hung or "
                "unreachable, you can set "
                "AI_COMPANY_OS_APPROVAL_KEY_FORCE_FILE=1 to take the "
                "filesystem path — but only as an explicit acknowledgement "
                "that you want to bypass the Phase 3 threat-model "
                "guarantees. Underlying error: "
                f"{type(exc).__name__}: {exc}"
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
    if _is_user_cancelled_stderr(stderr):
        raise KeychainUserCancelled(
            f"user cancelled the Keychain dialog: {stderr.strip()}"
        )
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
    underlying SecKeychainItemCopyContent call produces. Matching
    on stderr is fragile but it's the only option stdlib gives us.

    Marker list deliberately narrow (three-reviewer consensus on
    the PR #9 remediation pass):

    - ``"interaction is not allowed"`` — errSecInteractionNotAllowed
      when a process tries to read without a TTY available for the
      Keychain dialog. This is the production symptom when a
      launchd-started worker hasn't been pre-authorized.
    - ``"not authorized"`` — the generic "caller isn't on the ACL"
      text that several errSec* codes map to.
    - ``"-25308"`` — OSStatus numeric for errSecInteractionNotAllowed.
      Numeric markers are locale-independent and survive any
      localization of the English error strings; add more numeric
      markers (``"-25293"`` for errSecAuthFailed, etc.) as we
      encounter them in production.

    Markers deliberately NOT included:

    - ``"authorization"`` as a bare substring — too broad, would
      match "unknown authorization type" and similar non-denial
      errors. False-positive risk is high because a match here
      means we tell the operator to run ``bootstrap-keychain``
      when the real problem is something else.
    - ``"operation not permitted"`` — this is EPERM language, not
      Keychain language, and fires for sandbox/TCC errors that
      are NOT ACL denials.
    - ``"-128"`` / ``userCanceledErr`` — semantically distinct
      from ACL denial. When the user clicks "Deny" or "Cancel"
      on the first Keychain dialog, they're making an active
      choice, and the recovery path is "run the verify command
      manually and click Always Allow," not "re-run bootstrap-
      keychain." Mapped separately via :class:`KeychainUserCancelled`
      below.
    """
    lowered = stderr.lower()
    markers = (
        "interaction is not allowed",
        "not authorized",
        "-25308",
    )
    return any(m in lowered for m in markers)


def _is_user_cancelled_stderr(stderr: str) -> bool:
    """Match the user-cancelled-the-dialog error markers.

    Distinct from :func:`_is_access_denied_stderr` because the
    recovery path is different: the operator ran an interactive
    ``security find-generic-password -w`` and clicked Deny/Cancel
    on the Keychain dialog. The fix is to re-run the command and
    click "Always Allow" instead. Nothing wrong with the ACL.
    """
    lowered = stderr.lower()
    return "-128" in lowered or "usercanceled" in lowered


def _bootstrap_keychain_secret(
    *, trusted_binaries: list[str] | None = None
) -> bytes:
    """Create a fresh Keychain item with the signing secret.

    Refuses to clobber an existing item. Two guards are in place:

    1. **Pre-flight existence check.** ``_read_keychain_secret()``
       is called first; if it succeeds (item exists), we raise
       :class:`KeychainAlreadyExists` with a hint to run
       ``rotate-keychain``. This gives an unambiguous structured
       error — no stderr parsing.
    2. **Add-time duplicate detection.** Even if the pre-flight
       check says "not found," a concurrent bootstrap could create
       the item between our read and our write. ``security
       add-generic-password`` without ``-U`` fails on conflict
       with ``errSecDuplicateItem`` (exit 45), and we parse that
       specific exit code back into :class:`KeychainAlreadyExists`
       so the caller sees a consistent error regardless of which
       guard fires. Kieran-python follow-up from PR #9 review.

    The ``-U`` flag is deliberately NOT passed — without it,
    ``add-generic-password`` fails fast on an existing item. The
    pre-flight check catches the common case; the errSecDuplicateItem
    parsing catches the TOCTOU-race case.

    ``trusted_binaries`` adds ``-T /path/to/bin`` entries to the
    ACL. Note that for our subprocess-to-``/usr/bin/security``
    model, these entries are LARGELY COSMETIC — the actual calling
    process at read time is ``/usr/bin/security``, not any binary
    on the trusted list. The real silent-read authorization comes
    from the operator clicking "Always Allow" on the first
    Keychain dialog, which persists. Pass ``[sys.executable]`` as
    a reasonable default so future refactors that call the
    ``SecKeychain*`` C API directly (which would make the ACL
    meaningful) inherit a sensible starting point.

    Returns the 32-byte secret (hex-decoded from the stored value).
    """
    import subprocess

    # Pre-flight: refuse to clobber an existing item. Returns a
    # structured KeychainAlreadyExists with an actionable hint.
    try:
        _read_keychain_secret()
    except KeychainNotFound:
        pass
    else:
        raise KeychainAlreadyExists(
            f"{KEYCHAIN_SERVICE}/{KEYCHAIN_ACCOUNT} already exists in "
            f"the login keychain. Use `rotate-keychain --confirm rotate` "
            f"to replace it, or delete it manually via "
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
    if result.returncode == 0:
        return bytes.fromhex(secret_hex)

    # errSecDuplicateItem — somebody else bootstrapped between our
    # pre-flight check and this add call. Surface as the same
    # structured error as the pre-flight branch.
    stderr = (result.stderr or "").lower()
    if result.returncode == 45 or "already exists" in stderr:
        raise KeychainAlreadyExists(
            f"{KEYCHAIN_SERVICE}/{KEYCHAIN_ACCOUNT} was created by "
            f"another process between pre-flight and add — likely a "
            f"concurrent bootstrap. Use `rotate-keychain --confirm "
            f"rotate` to replace with a fresh key."
        )
    raise KeychainError(
        f"failed to bootstrap keychain item: "
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

    Delete step is inlined here (single call site; the old
    ``_delete_keychain_secret`` helper was cut during the PR #9
    simplicity pass). Idempotent — a missing item is not an error,
    matches ``rm -f`` semantics.
    """
    import subprocess

    delete_result = subprocess.run(
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
    if delete_result.returncode not in (0, 44, 25293):
        raise KeychainError(
            f"failed to delete keychain item during rotate: "
            f"exit={delete_result.returncode} "
            f"stderr={delete_result.stderr.strip()}"
        )
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
