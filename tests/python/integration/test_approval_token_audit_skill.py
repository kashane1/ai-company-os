"""Phase 3.2a — approval-token-audit wired into release-readiness.

Integration test covering the validator as called from the policy code,
rather than in isolation. Ensures the fail-closed path converts validator
errors into ``PolicyViolation("approval_audit_unavailable")`` and that a
drifted token-store adapter surfaces ``approval_audit_failed``.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from apps.api.control_plane import ControlPlaneService
from packages.db.approval_token_store import ApprovalTokenStore
from packages.policies.approval_tokens import (
    issue_token,
    record_second_factor,
    verify_and_burn_token,
)
from packages.policies.approvals import PolicyViolation
from packages.policies.release_readiness import (
    APP_STORE_SUBMISSION_APPROVAL_TYPE,
    _TokenAuditStoreAdapter,
    approve_app_store_submission,
)
from packages.schemas.approval import ApprovalStatus
from packages.schemas.release import ReleaseStatus
from tests.python.unit.test_release_readiness import (
    SECRET,
    _seed_p0_token_and_approve,
    _seed_release,
    _write_checklist,
)


def test_token_audit_validator_fails_closed_on_adapter_error(
    isolated_repo_root, monkeypatch
) -> None:
    _write_checklist(isolated_repo_root, unchecked=0)
    service = ControlPlaneService()
    approval = service.request_approval(
        summary="submit",
        subject_type="release",
        subject_id="release-catchbook-v0.1.0",
        action="submit_appstore",
        approval_type=APP_STORE_SUBMISSION_APPROVAL_TYPE,
    )
    _seed_release("release-catchbook-v0.1.0", status=ReleaseStatus.READY_FOR_REVIEW)
    _seed_p0_token_and_approve(
        approval.id, "release-catchbook-v0.1.0", service=service
    )

    class BrokenAdapter:
        def load(self, _approval_id):
            raise RuntimeError("adapter down")

    monkeypatch.setattr(
        "packages.policies.release_readiness._TokenAuditStoreAdapter",
        lambda **_: BrokenAdapter(),
    )

    with pytest.raises(PolicyViolation) as exc:
        approve_app_store_submission(
            "release-catchbook-v0.1.0",
            approval.id,
        )
    assert exc.value.code == "approval_audit_unavailable"


def test_token_audit_reports_failed_for_missing_token(isolated_repo_root) -> None:
    _write_checklist(isolated_repo_root, unchecked=0)
    service = ControlPlaneService()
    approval = service.request_approval(
        summary="submit",
        subject_type="release",
        subject_id="release-catchbook-v0.1.0",
        action="submit_appstore",
        approval_type=APP_STORE_SUBMISSION_APPROVAL_TYPE,
    )
    service.decide_approval(
        approval_id=approval.id,
        status=ApprovalStatus.APPROVED,
        decided_by="test",
    )
    _seed_release("release-catchbook-v0.1.0", status=ReleaseStatus.READY_FOR_REVIEW)
    # No token minted → adapter raises FileNotFoundError → fail-closed.

    with pytest.raises(PolicyViolation) as exc:
        approve_app_store_submission(
            "release-catchbook-v0.1.0",
            approval.id,
        )
    assert exc.value.code == "approval_audit_unavailable"


def test_token_audit_detects_subject_mismatch(isolated_repo_root) -> None:
    _write_checklist(isolated_repo_root, unchecked=0)
    service = ControlPlaneService()
    approval = service.request_approval(
        summary="submit",
        subject_type="release",
        subject_id="release-catchbook-v0.1.0",
        action="submit_appstore",
        approval_type=APP_STORE_SUBMISSION_APPROVAL_TYPE,
    )
    _seed_release("release-catchbook-v0.1.0", status=ReleaseStatus.READY_FOR_REVIEW)

    token_store = ApprovalTokenStore()
    # Mint token against the wrong subject id
    token = issue_token(
        approval_id=approval.id,
        subject_id="release-catchbook-v9.9.9",  # drift
        action="submit_appstore",
        secret=SECRET,
        store=token_store,
    )
    burned = verify_and_burn_token(
        token_id=token.token_id,
        provided_signature=token.signature,
        device_fingerprint="mac-local",
        secret=SECRET,
        store=token_store,
    )
    record_second_factor(
        token_id=token.token_id,
        provided_signature=token.signature,
        device_fingerprint="mac-local",
        secret=SECRET,
        store=token_store,
        now=datetime.fromisoformat(burned.approved_at) + timedelta(seconds=5),
    )
    service.decide_approval(
        approval_id=approval.id,
        status=ApprovalStatus.APPROVED,
        decided_by="test",
    )

    with pytest.raises(PolicyViolation) as exc:
        approve_app_store_submission(
            "release-catchbook-v0.1.0",
            approval.id,
        )
    assert exc.value.code == "approval_audit_failed"


def test_token_audit_happy_path_matches_unit(isolated_repo_root) -> None:
    """Sanity-check the adapter produces a dict the validator accepts."""
    _write_checklist(isolated_repo_root, unchecked=0)
    service = ControlPlaneService()
    approval = service.request_approval(
        summary="submit",
        subject_type="release",
        subject_id="release-catchbook-v0.1.0",
        action="submit_appstore",
        approval_type=APP_STORE_SUBMISSION_APPROVAL_TYPE,
    )
    _seed_release("release-catchbook-v0.1.0", status=ReleaseStatus.READY_FOR_REVIEW)
    _seed_p0_token_and_approve(
        approval.id, "release-catchbook-v0.1.0", service=service
    )

    release = approve_app_store_submission(
        "release-catchbook-v0.1.0",
        approval.id,
    )
    assert release.id == "release-catchbook-v0.1.0"
