"""Phase 3 — unit tests for packages/tools/primitives/approvals.py."""
from __future__ import annotations

from pathlib import Path

import pytest

from packages.config.settings import TEST_REPO_ROOT_ENV_VAR, ensure_runtime_directories
from packages.db.approval_store import ApprovalStore
from packages.db.approval_token_store import ApprovalTokenStore
from packages.policies.approval_tokens import TokenSignatureInvalid
from packages.schemas.approval import ApprovalStatus
from packages.tools.primitives.approvals import (
    SKILL_EVOLUTION_ACTION,
    SKILL_EVOLUTION_APPROVAL_TYPE,
    poll_evolution_approval,
    reject_evolution_approval,
    request_evolution_approval,
    submit_evolution_approval,
)


@pytest.fixture
def isolated_state(tmp_path, monkeypatch):
    monkeypatch.setenv(TEST_REPO_ROOT_ENV_VAR, str(tmp_path))
    # Deterministic signing secret so the test asserts against a
    # stable HMAC chain and isn't sensitive to first-call bootstrap.
    monkeypatch.setenv(
        "AI_COMPANY_OS_APPROVAL_SIGNING_KEY", "00" * 32
    )
    ensure_runtime_directories()
    artifact_dir = tmp_path / "artifacts" / "skill-evolution" / "proposal-1"
    artifact_dir.mkdir(parents=True)
    (artifact_dir / "diff.patch").write_text("--- a/x\n+++ b/x\n")
    return artifact_dir


def test_request_evolution_approval_persists_record_and_token(isolated_state: Path) -> None:
    approvals = ApprovalStore()
    tokens = ApprovalTokenStore()
    req = request_evolution_approval(
        proposal_id="proposal-1",
        target_skill_id="demo-evolvable-skill",
        rationale="test proposal",
        artifact_dir=isolated_state,
        task_id="task-1",
        approval_store=approvals,
        token_store=tokens,
    )
    assert req.approval_id == "skill-evo-proposal-1"
    assert req.action == SKILL_EVOLUTION_ACTION

    record = approvals.load(req.approval_id)
    assert record.status is ApprovalStatus.PENDING
    assert record.approval_type == SKILL_EVOLUTION_APPROVAL_TYPE
    assert record.subject_id == "demo-evolvable-skill"
    assert record.summary == "test proposal"
    assert record.review_artifact_path == str(isolated_state)

    # Token is discoverable by approval id and matches the returned
    # signature — that's how the reviewer verifies without state
    # transfer.
    by_approval = tokens.list_by_approval(req.approval_id)
    assert len(by_approval) == 1
    assert by_approval[0].signature == req.signature
    assert by_approval[0].token_id == req.token_id


def test_request_raises_if_artifact_dir_missing(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv(TEST_REPO_ROOT_ENV_VAR, str(tmp_path))
    monkeypatch.setenv("AI_COMPANY_OS_APPROVAL_SIGNING_KEY", "00" * 32)
    ensure_runtime_directories()
    missing = tmp_path / "nope"
    with pytest.raises(FileNotFoundError):
        request_evolution_approval(
            proposal_id="p",
            target_skill_id="x",
            rationale="r",
            artifact_dir=missing,
        )


def test_poll_before_sign_reports_pending(isolated_state: Path) -> None:
    req = request_evolution_approval(
        proposal_id="p",
        target_skill_id="demo",
        rationale="r",
        artifact_dir=isolated_state,
        expected_device_fingerprint="test-device",
    )
    decision = poll_evolution_approval(approval_id=req.approval_id)
    assert decision.outcome == "pending"
    assert decision.decided_by is None


def test_poll_missing_approval_returns_pending(isolated_state: Path) -> None:
    # Missing approval is NOT an error — the worker's poll loop
    # expects a uniform code path.
    decision = poll_evolution_approval(approval_id="skill-evo-missing")
    assert decision.outcome == "pending"


def test_submit_approves_with_correct_hmac(isolated_state: Path) -> None:
    req = request_evolution_approval(
        proposal_id="p",
        target_skill_id="demo",
        rationale="r",
        artifact_dir=isolated_state,
        expected_device_fingerprint="test-device",
    )
    decision = submit_evolution_approval(
        approval_id=req.approval_id,
        token_id=req.token_id,
        provided_signature=req.signature,
        device_fingerprint="test-device",
        decided_by="alice@host",
        decision_notes="LGTM",
    )
    assert decision.outcome == "approved"
    assert decision.decided_by == "alice@host"
    assert decision.decision_notes == "LGTM"

    # Subsequent poll sees the approved state.
    readback = poll_evolution_approval(approval_id=req.approval_id)
    assert readback.outcome == "approved"


def test_submit_with_wrong_signature_raises(isolated_state: Path) -> None:
    req = request_evolution_approval(
        proposal_id="p",
        target_skill_id="demo",
        rationale="r",
        artifact_dir=isolated_state,
        expected_device_fingerprint="test-device",
    )
    with pytest.raises(TokenSignatureInvalid):
        submit_evolution_approval(
            approval_id=req.approval_id,
            token_id=req.token_id,
            provided_signature="AAAA" * 10,  # wrong
            device_fingerprint="test-device",
            decided_by="mallory",
        )
    # Record still pending — a forged attempt did not mutate state.
    decision = poll_evolution_approval(approval_id=req.approval_id)
    assert decision.outcome == "pending"


def test_submit_with_mismatched_approval_id_does_not_burn_token(
    isolated_state: Path,
) -> None:
    """Regression for kieran review Blocker #2: the burn must NOT fire
    on an approval_id mismatch, otherwise an attacker (or a CLI bug)
    could permanently DoS the legitimate reviewer by submitting with a
    wrong id using a captured valid signature. The legitimate reviewer
    must still be able to sign afterwards."""
    from packages.db.approval_token_store import ApprovalTokenStore

    req = request_evolution_approval(
        proposal_id="p",
        target_skill_id="demo",
        rationale="r",
        artifact_dir=isolated_state,
        expected_device_fingerprint="test-device",
    )
    with pytest.raises(TokenSignatureInvalid):
        submit_evolution_approval(
            approval_id="skill-evo-different",
            token_id=req.token_id,
            provided_signature=req.signature,
            device_fingerprint="test-device",
            decided_by="bob",
        )

    # Critical: the token must NOT have been burned. The legitimate
    # reviewer must still be able to sign with the correct approval_id.
    token_after = ApprovalTokenStore().load(req.token_id)
    assert token_after.burn_count == 0, (
        "burn_count must stay 0 after a mismatched-approval_id attempt; "
        "any non-zero value indicates the DoS regression from kieran "
        "review Blocker #2"
    )

    # And the real reviewer can still approve:
    # The token was issued with expected_device_fingerprint="test-device"
    # so a legitimate burn must use the same binding.
    decision = submit_evolution_approval(
        approval_id=req.approval_id,
        token_id=req.token_id,
        provided_signature=req.signature,
        device_fingerprint="test-device",
        decided_by="alice",
    )
    assert decision.outcome == "approved"


def test_submit_with_wrong_device_fingerprint_is_rejected(
    isolated_state: Path,
) -> None:
    """Security-sentinel H1 regression: the expected_device_fingerprint
    must be bound at issue time AND enforced on burn. The earlier
    version left the field None, which short-circuited the check in
    ``verify_and_burn_token`` and accepted any device on sign."""
    from packages.policies.approval_tokens import DeviceMismatch

    req = request_evolution_approval(
        proposal_id="p",
        target_skill_id="demo",
        rationale="r",
        artifact_dir=isolated_state,
        expected_device_fingerprint="the-real-host",
    )
    with pytest.raises(DeviceMismatch):
        submit_evolution_approval(
            approval_id=req.approval_id,
            token_id=req.token_id,
            provided_signature=req.signature,
            device_fingerprint="attacker-host",
            decided_by="alice",
        )
    # Token not burned — legitimate reviewer can still sign.
    decision = submit_evolution_approval(
        approval_id=req.approval_id,
        token_id=req.token_id,
        provided_signature=req.signature,
        device_fingerprint="the-real-host",
        decided_by="alice",
    )
    assert decision.outcome == "approved"


def test_signing_secret_rejects_empty_env_var(tmp_path, monkeypatch) -> None:
    """Security-sentinel C2.3 regression: a whitespace-only env var
    must not silently produce an empty HMAC key."""
    from packages.tools.primitives.approvals import _load_signing_secret

    monkeypatch.setenv(TEST_REPO_ROOT_ENV_VAR, str(tmp_path))
    ensure_runtime_directories()
    monkeypatch.setenv("AI_COMPANY_OS_APPROVAL_SIGNING_KEY", "   ")
    with pytest.raises(ValueError, match="empty or whitespace-only"):
        _load_signing_secret()


def test_signing_secret_rejects_short_env_var(tmp_path, monkeypatch) -> None:
    """Hex env var that decodes to fewer than 32 bytes is rejected."""
    from packages.tools.primitives.approvals import _load_signing_secret

    monkeypatch.setenv(TEST_REPO_ROOT_ENV_VAR, str(tmp_path))
    ensure_runtime_directories()
    monkeypatch.setenv("AI_COMPANY_OS_APPROVAL_SIGNING_KEY", "00" * 16)  # 16 bytes
    with pytest.raises(ValueError, match="minimum is 32"):
        _load_signing_secret()


def test_signing_secret_rejects_non_hex_env_var(tmp_path, monkeypatch) -> None:
    from packages.tools.primitives.approvals import _load_signing_secret

    monkeypatch.setenv(TEST_REPO_ROOT_ENV_VAR, str(tmp_path))
    ensure_runtime_directories()
    monkeypatch.setenv("AI_COMPANY_OS_APPROVAL_SIGNING_KEY", "not-hex-" * 8)
    with pytest.raises(ValueError, match="not valid hex"):
        _load_signing_secret()


def test_signing_secret_bootstrap_writes_mode_0600(tmp_path, monkeypatch) -> None:
    """First-call bootstrap must create the key file with exactly
    0600 permissions atomically — no race window where the file is
    readable by other users."""
    import os as _os
    import stat

    from packages.tools.primitives.approvals import _load_signing_secret
    from packages.config.settings import load_runtime_paths

    monkeypatch.setenv(TEST_REPO_ROOT_ENV_VAR, str(tmp_path))
    monkeypatch.delenv("AI_COMPANY_OS_APPROVAL_SIGNING_KEY", raising=False)
    # These tests exercise the filesystem fallback — force it on
    # macOS by setting the escape-hatch env var. Without this, the
    # function routes to Keychain and the filesystem hardening
    # path never runs.
    monkeypatch.setenv("AI_COMPANY_OS_APPROVAL_KEY_FORCE_FILE", "1")
    ensure_runtime_directories()

    secret = _load_signing_secret()
    assert len(secret) == 32

    key_path = load_runtime_paths().platform_state_root / "approval_signing_key"
    assert key_path.exists()
    mode = stat.S_IMODE(_os.stat(key_path).st_mode)
    assert mode == 0o600, f"expected 0600, got {oct(mode)}"


def test_signing_secret_refuses_symlink(tmp_path, monkeypatch) -> None:
    """Security-sentinel C2.1 regression: a symlink at the key path
    must be refused, not silently followed. Without this, an attacker
    who plants a symlink to a known-content file hijacks the HMAC
    key on the worker's next restart."""
    import os as _os

    from packages.tools.primitives.approvals import _load_signing_secret
    from packages.config.settings import load_runtime_paths

    monkeypatch.setenv(TEST_REPO_ROOT_ENV_VAR, str(tmp_path))
    monkeypatch.delenv("AI_COMPANY_OS_APPROVAL_SIGNING_KEY", raising=False)
    # These tests exercise the filesystem fallback — force it on
    # macOS by setting the escape-hatch env var. Without this, the
    # function routes to Keychain and the filesystem hardening
    # path never runs.
    monkeypatch.setenv("AI_COMPANY_OS_APPROVAL_KEY_FORCE_FILE", "1")
    ensure_runtime_directories()

    paths = load_runtime_paths()
    key_path = paths.platform_state_root / "approval_signing_key"
    key_path.parent.mkdir(parents=True, exist_ok=True)
    target = tmp_path / "attacker_key"
    target.write_bytes(b"\x00" * 32)
    _os.symlink(target, key_path)

    with pytest.raises(RuntimeError, match="symlink or otherwise unsafe"):
        _load_signing_secret()


def test_signing_secret_refuses_group_readable_file(tmp_path, monkeypatch) -> None:
    """An existing key file with group-readable bits must be
    refused. Protects against a process that somehow created the
    file with wrong permissions earlier."""
    import os as _os

    from packages.tools.primitives.approvals import _load_signing_secret
    from packages.config.settings import load_runtime_paths

    monkeypatch.setenv(TEST_REPO_ROOT_ENV_VAR, str(tmp_path))
    monkeypatch.delenv("AI_COMPANY_OS_APPROVAL_SIGNING_KEY", raising=False)
    # These tests exercise the filesystem fallback — force it on
    # macOS by setting the escape-hatch env var. Without this, the
    # function routes to Keychain and the filesystem hardening
    # path never runs.
    monkeypatch.setenv("AI_COMPANY_OS_APPROVAL_KEY_FORCE_FILE", "1")
    ensure_runtime_directories()

    paths = load_runtime_paths()
    key_path = paths.platform_state_root / "approval_signing_key"
    key_path.parent.mkdir(parents=True, exist_ok=True)
    key_path.write_bytes(b"\x00" * 32)
    _os.chmod(key_path, 0o644)  # group/world readable

    with pytest.raises(RuntimeError, match="group/world permissions"):
        _load_signing_secret()


# ---------------------------------------------------------------------- #
# Keychain migration — mocked subprocess, platform-independent            #
# ---------------------------------------------------------------------- #


class _FakeCompletedProcess:
    def __init__(self, returncode: int, stdout: str = "", stderr: str = ""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


def _install_fake_security(monkeypatch, handler):
    """Patch ``subprocess.run`` inside approvals._read/_bootstrap_keychain_secret
    with a test-controlled handler. The real ``/usr/bin/security``
    binary is never invoked — the Keychain code paths are unit-
    testable without touching the user's real keychain."""
    import subprocess as _subprocess

    real_run = _subprocess.run

    def fake_run(cmd, **kwargs):
        if cmd and cmd[0] == "/usr/bin/security":
            return handler(cmd, kwargs)
        return real_run(cmd, **kwargs)

    monkeypatch.setattr(_subprocess, "run", fake_run)


def _force_keychain_platform(monkeypatch):
    """Force the function to take the Keychain branch regardless of
    the real platform. Sets sys.platform to 'darwin' and clears the
    force-file escape hatch. Used by every keychain test so Linux
    CI runners exercise the branch too."""
    import sys as _sys

    monkeypatch.setattr(_sys, "platform", "darwin")
    monkeypatch.delenv("AI_COMPANY_OS_APPROVAL_KEY_FORCE_FILE", raising=False)
    monkeypatch.delenv("AI_COMPANY_OS_APPROVAL_SIGNING_KEY", raising=False)


def test_keychain_hit_returns_decoded_secret(tmp_path, monkeypatch) -> None:
    """Successful `security find-generic-password -w` call returns
    the stored hex; _load_signing_secret decodes it to bytes."""
    from packages.tools.primitives.approvals import _load_signing_secret

    monkeypatch.setenv(TEST_REPO_ROOT_ENV_VAR, str(tmp_path))
    ensure_runtime_directories()
    _force_keychain_platform(monkeypatch)

    fixed_hex = "aa" * 32

    def handler(cmd, kwargs):
        assert "find-generic-password" in cmd
        assert "-s" in cmd and "ai-company-os" in cmd
        assert "-a" in cmd and "approval_signing_key" in cmd
        return _FakeCompletedProcess(0, stdout=fixed_hex + "\n")

    _install_fake_security(monkeypatch, handler)
    secret = _load_signing_secret()
    assert secret == bytes.fromhex(fixed_hex)


def test_keychain_not_found_raises_with_bootstrap_hint(
    tmp_path, monkeypatch
) -> None:
    """Exit code 44 (errSecItemNotFound) surfaces as an operator-
    facing RuntimeError naming the bootstrap command, NOT a silent
    fall-through to the filesystem."""
    from packages.tools.primitives.approvals import _load_signing_secret

    monkeypatch.setenv(TEST_REPO_ROOT_ENV_VAR, str(tmp_path))
    ensure_runtime_directories()
    _force_keychain_platform(monkeypatch)

    def handler(cmd, kwargs):
        return _FakeCompletedProcess(
            44, stderr="security: SecKeychainSearchCopyNext: The specified item could not be found in the keychain.\n"
        )

    _install_fake_security(monkeypatch, handler)
    with pytest.raises(RuntimeError, match="bootstrap-keychain"):
        _load_signing_secret()


def test_keychain_access_denied_refuses_filesystem_fallback(
    tmp_path, monkeypatch
) -> None:
    """Security-sentinel C1 guarantee: when Keychain denies access,
    the function raises — it does NOT fall through to the filesystem
    path. Silent fallback would defeat the whole migration because
    a compromised caller could get denied at Keychain and then read
    the filesystem key."""
    from packages.tools.primitives.approvals import _load_signing_secret

    monkeypatch.setenv(TEST_REPO_ROOT_ENV_VAR, str(tmp_path))
    ensure_runtime_directories()
    _force_keychain_platform(monkeypatch)

    # Also create a filesystem key so we can prove the function is
    # refusing to read it even though it exists.
    paths = ensure_runtime_directories()
    key_path = paths.platform_state_root / "approval_signing_key"
    key_path.write_bytes(b"\x99" * 32)
    import os as _os

    _os.chmod(key_path, 0o600)

    def handler(cmd, kwargs):
        return _FakeCompletedProcess(
            51,
            stderr="security: User interaction is not allowed.\n",
        )

    _install_fake_security(monkeypatch, handler)
    with pytest.raises(RuntimeError, match="Refusing to sign with filesystem fallback"):
        _load_signing_secret()


def test_force_file_env_var_routes_to_filesystem_on_macos(
    tmp_path, monkeypatch
) -> None:
    """The explicit escape hatch
    ``AI_COMPANY_OS_APPROVAL_KEY_FORCE_FILE=1`` takes the filesystem
    path even on macOS. Required for CI and for the first-landing
    dry-run procedure."""
    import sys as _sys

    from packages.tools.primitives.approvals import _load_signing_secret

    monkeypatch.setenv(TEST_REPO_ROOT_ENV_VAR, str(tmp_path))
    monkeypatch.delenv("AI_COMPANY_OS_APPROVAL_SIGNING_KEY", raising=False)
    monkeypatch.setattr(_sys, "platform", "darwin")
    monkeypatch.setenv("AI_COMPANY_OS_APPROVAL_KEY_FORCE_FILE", "1")
    ensure_runtime_directories()

    # If the function took the Keychain branch it would fail (no
    # handler installed). Taking the filesystem branch bootstraps a
    # key and returns 32 bytes.
    secret = _load_signing_secret()
    assert len(secret) == 32


def test_non_darwin_platform_routes_to_filesystem(tmp_path, monkeypatch) -> None:
    """Non-macOS platforms (Linux CI, Windows) always take the
    filesystem path — the Keychain branch is darwin-only."""
    import sys as _sys

    from packages.tools.primitives.approvals import _load_signing_secret

    monkeypatch.setenv(TEST_REPO_ROOT_ENV_VAR, str(tmp_path))
    monkeypatch.delenv("AI_COMPANY_OS_APPROVAL_SIGNING_KEY", raising=False)
    monkeypatch.delenv("AI_COMPANY_OS_APPROVAL_KEY_FORCE_FILE", raising=False)
    monkeypatch.setattr(_sys, "platform", "linux")
    ensure_runtime_directories()

    secret = _load_signing_secret()
    assert len(secret) == 32


def test_env_var_has_highest_precedence_even_on_macos(
    tmp_path, monkeypatch
) -> None:
    """The env-var override short-circuits both Keychain AND
    filesystem paths. Highest precedence, cross-platform."""
    import sys as _sys

    from packages.tools.primitives.approvals import _load_signing_secret

    monkeypatch.setenv(TEST_REPO_ROOT_ENV_VAR, str(tmp_path))
    monkeypatch.setattr(_sys, "platform", "darwin")
    monkeypatch.setenv("AI_COMPANY_OS_APPROVAL_SIGNING_KEY", "bb" * 32)
    monkeypatch.delenv("AI_COMPANY_OS_APPROVAL_KEY_FORCE_FILE", raising=False)
    ensure_runtime_directories()

    # No subprocess handler installed — if the env path didn't
    # short-circuit, the Keychain branch would fire and error.
    secret = _load_signing_secret()
    assert secret == bytes.fromhex("bb" * 32)


def test_keychain_timeout_raises_keychain_error(tmp_path, monkeypatch) -> None:
    """A hanging `security` invocation must be bounded. If it
    exceeds the 10-second timeout, KeychainError is raised (which
    the wrapper surfaces as a RuntimeError)."""
    import subprocess as _subprocess

    from packages.tools.primitives.approvals import (
        _read_keychain_secret,
        KeychainError,
    )

    monkeypatch.setenv(TEST_REPO_ROOT_ENV_VAR, str(tmp_path))
    ensure_runtime_directories()
    _force_keychain_platform(monkeypatch)

    def raising(cmd, **kwargs):
        raise _subprocess.TimeoutExpired(cmd=cmd, timeout=10.0)

    monkeypatch.setattr(_subprocess, "run", raising)
    with pytest.raises(KeychainError, match="timed out"):
        _read_keychain_secret()


def test_bootstrap_refuses_existing_keychain_item(tmp_path, monkeypatch) -> None:
    """bootstrap-keychain must refuse to clobber an existing item —
    rotation is a deliberate, separate action."""
    from packages.tools.primitives.approvals import (
        _bootstrap_keychain_secret,
        KeychainAlreadyExists,
    )

    monkeypatch.setenv(TEST_REPO_ROOT_ENV_VAR, str(tmp_path))
    ensure_runtime_directories()
    _force_keychain_platform(monkeypatch)

    def handler(cmd, kwargs):
        if "find-generic-password" in cmd:
            # Item exists — return a valid-looking payload.
            return _FakeCompletedProcess(0, stdout="cc" * 32 + "\n")
        # add-generic-password should never be reached.
        raise AssertionError(
            f"bootstrap clobbered existing item: {cmd}"
        )

    _install_fake_security(monkeypatch, handler)
    with pytest.raises(KeychainAlreadyExists):
        _bootstrap_keychain_secret(trusted_binaries=["/usr/bin/python3"])


def test_bootstrap_creates_item_when_absent(tmp_path, monkeypatch) -> None:
    """bootstrap-keychain on a fresh machine runs
    `security add-generic-password` with the expected -T flags
    and returns the 32-byte secret."""
    from packages.tools.primitives.approvals import _bootstrap_keychain_secret

    monkeypatch.setenv(TEST_REPO_ROOT_ENV_VAR, str(tmp_path))
    ensure_runtime_directories()
    _force_keychain_platform(monkeypatch)

    added: list[list[str]] = []

    def handler(cmd, kwargs):
        if "find-generic-password" in cmd:
            return _FakeCompletedProcess(44, stderr="not found")
        if "add-generic-password" in cmd:
            added.append(cmd)
            return _FakeCompletedProcess(0)
        raise AssertionError(f"unexpected security call: {cmd}")

    _install_fake_security(monkeypatch, handler)
    secret = _bootstrap_keychain_secret(
        trusted_binaries=["/opt/venv/bin/python", "/opt/app/cli"]
    )
    assert len(secret) == 32
    assert len(added) == 1
    cmd = added[0]
    assert "-T" in cmd
    assert "/opt/venv/bin/python" in cmd
    assert "/opt/app/cli" in cmd


def test_keychain_user_cancelled_has_distinct_recovery_hint(
    tmp_path, monkeypatch
) -> None:
    """PR #9 review: clicking Deny on the Keychain dialog
    (-128 userCanceledErr) must surface a dialog-specific
    recovery message, NOT the ACL-refresh message that
    KeychainAccessDenied produces. The fixes are different:
    for user-cancelled the operator runs the verify command in
    a TTY and clicks Always Allow; for access-denied they
    re-run bootstrap-keychain with the right --trusted-binary."""
    from packages.tools.primitives.approvals import _load_signing_secret

    monkeypatch.setenv(TEST_REPO_ROOT_ENV_VAR, str(tmp_path))
    ensure_runtime_directories()
    _force_keychain_platform(monkeypatch)

    def handler(cmd, kwargs):
        return _FakeCompletedProcess(
            -128,
            stderr="security: SecKeychainItemCopyContent (-128)\n",
        )

    _install_fake_security(monkeypatch, handler)
    with pytest.raises(RuntimeError, match="Always Allow"):
        _load_signing_secret()


def test_keychain_bare_error_has_actionable_hint(
    tmp_path, monkeypatch
) -> None:
    """Security-sentinel H1 on PR #9: any KeychainError that
    isn't NotFound/AccessDenied/UserCancelled (timeout, missing
    binary, malformed stdout, unclassified non-zero exit) must
    surface as a RuntimeError naming FORCE_FILE as the escape
    hatch, NOT propagate as a raw KeychainError. The security
    invariant (no silent fallback) holds either way, but the
    operator UX must be actionable."""
    import subprocess as _subprocess

    from packages.tools.primitives.approvals import _load_signing_secret

    monkeypatch.setenv(TEST_REPO_ROOT_ENV_VAR, str(tmp_path))
    ensure_runtime_directories()
    _force_keychain_platform(monkeypatch)

    def raising(cmd, **kwargs):
        raise _subprocess.TimeoutExpired(cmd=cmd, timeout=10.0)

    monkeypatch.setattr(_subprocess, "run", raising)
    with pytest.raises(
        RuntimeError, match="AI_COMPANY_OS_APPROVAL_KEY_FORCE_FILE"
    ):
        _load_signing_secret()


def test_bootstrap_detects_duplicate_item_at_add_time(
    tmp_path, monkeypatch
) -> None:
    """TOCTOU race: the pre-flight check says not-found, but a
    concurrent bootstrap creates the item before our add call.
    `security add-generic-password` without -U returns exit 45
    (errSecDuplicateItem) in that case, and we map it back to
    KeychainAlreadyExists so the caller sees a consistent error
    regardless of which guard fires."""
    from packages.tools.primitives.approvals import (
        _bootstrap_keychain_secret,
        KeychainAlreadyExists,
    )

    monkeypatch.setenv(TEST_REPO_ROOT_ENV_VAR, str(tmp_path))
    ensure_runtime_directories()
    _force_keychain_platform(monkeypatch)

    def handler(cmd, kwargs):
        if "find-generic-password" in cmd:
            return _FakeCompletedProcess(44, stderr="not found")
        if "add-generic-password" in cmd:
            return _FakeCompletedProcess(
                45,
                stderr=(
                    "security: add-generic-password: The specified "
                    "item already exists in the keychain.\n"
                ),
            )
        raise AssertionError(f"unexpected security call: {cmd}")

    _install_fake_security(monkeypatch, handler)
    with pytest.raises(KeychainAlreadyExists, match="concurrent bootstrap"):
        _bootstrap_keychain_secret(trusted_binaries=["/usr/bin/python3"])


def test_access_denied_marker_list_does_not_match_unrelated_errors(
    tmp_path, monkeypatch
) -> None:
    """Simplicity review: the old marker list matched
    `"authorization"` as a bare substring, which is too broad.
    The trimmed list must not match unrelated errors that happen
    to contain the word 'authorization' — those should fall
    through to the bare-KeychainError path and get the generic
    wrapper, not the "re-run bootstrap-keychain" hint which
    would be misleading."""
    from packages.tools.primitives.approvals import _load_signing_secret

    monkeypatch.setenv(TEST_REPO_ROOT_ENV_VAR, str(tmp_path))
    ensure_runtime_directories()
    _force_keychain_platform(monkeypatch)

    def handler(cmd, kwargs):
        return _FakeCompletedProcess(
            50, stderr="security: unknown authorization type 'foo'\n"
        )

    _install_fake_security(monkeypatch, handler)
    with pytest.raises(RuntimeError) as exc:
        _load_signing_secret()
    msg = str(exc.value)
    assert "Refusing to sign" not in msg
    assert "re-run `bootstrap-keychain`" not in msg
    assert "AI_COMPANY_OS_APPROVAL_KEY_FORCE_FILE" in msg


def test_rotate_deletes_then_creates(tmp_path, monkeypatch) -> None:
    """rotate-keychain = delete + bootstrap. Old tokens become
    unverifiable, which is the intended consequence of rotation."""
    from packages.tools.primitives.approvals import _rotate_keychain_secret

    monkeypatch.setenv(TEST_REPO_ROOT_ENV_VAR, str(tmp_path))
    ensure_runtime_directories()
    _force_keychain_platform(monkeypatch)

    calls: list[str] = []
    state = {"exists": True}

    def handler(cmd, kwargs):
        if "delete-generic-password" in cmd:
            calls.append("delete")
            state["exists"] = False
            return _FakeCompletedProcess(0)
        if "find-generic-password" in cmd:
            calls.append("find")
            if state["exists"]:
                return _FakeCompletedProcess(0, stdout="dd" * 32 + "\n")
            return _FakeCompletedProcess(44, stderr="not found")
        if "add-generic-password" in cmd:
            calls.append("add")
            state["exists"] = True
            return _FakeCompletedProcess(0)
        raise AssertionError(f"unexpected security call: {cmd}")

    _install_fake_security(monkeypatch, handler)
    secret = _rotate_keychain_secret(trusted_binaries=["/opt/venv/bin/python"])
    assert len(secret) == 32
    # Sequence must be delete → find (during bootstrap's pre-check) → add
    assert calls == ["delete", "find", "add"]


def test_reject_without_hmac_flips_record(isolated_state: Path) -> None:
    req = request_evolution_approval(
        proposal_id="p",
        target_skill_id="demo",
        rationale="r",
        artifact_dir=isolated_state,
        expected_device_fingerprint="test-device",
    )
    decision = reject_evolution_approval(
        approval_id=req.approval_id,
        decided_by="alice",
        decision_notes="no",
    )
    assert decision.outcome == "rejected"
    readback = poll_evolution_approval(approval_id=req.approval_id)
    assert readback.outcome == "rejected"
