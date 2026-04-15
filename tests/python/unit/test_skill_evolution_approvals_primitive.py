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
    ensure_runtime_directories()

    paths = load_runtime_paths()
    key_path = paths.platform_state_root / "approval_signing_key"
    key_path.parent.mkdir(parents=True, exist_ok=True)
    key_path.write_bytes(b"\x00" * 32)
    _os.chmod(key_path, 0o644)  # group/world readable

    with pytest.raises(RuntimeError, match="group/world permissions"):
        _load_signing_secret()


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
