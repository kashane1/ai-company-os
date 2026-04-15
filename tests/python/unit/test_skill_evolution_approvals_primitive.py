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


def test_submit_with_mismatched_approval_id_raises(isolated_state: Path) -> None:
    req = request_evolution_approval(
        proposal_id="p",
        target_skill_id="demo",
        rationale="r",
        artifact_dir=isolated_state,
    )
    with pytest.raises(TokenSignatureInvalid):
        submit_evolution_approval(
            approval_id="skill-evo-different",
            token_id=req.token_id,
            provided_signature=req.signature,
            device_fingerprint="test-device",
            decided_by="bob",
        )


def test_reject_without_hmac_flips_record(isolated_state: Path) -> None:
    req = request_evolution_approval(
        proposal_id="p",
        target_skill_id="demo",
        rationale="r",
        artifact_dir=isolated_state,
    )
    decision = reject_evolution_approval(
        approval_id=req.approval_id,
        decided_by="alice",
        decision_notes="no",
    )
    assert decision.outcome == "rejected"
    readback = poll_evolution_approval(approval_id=req.approval_id)
    assert readback.outcome == "rejected"
