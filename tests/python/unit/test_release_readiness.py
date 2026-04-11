"""Phase 3.2 — release-readiness policy unit tests."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest

from apps.api.control_plane import ControlPlaneService
from packages.db.approval_store import ApprovalStore
from packages.db.approval_token_store import ApprovalTokenStore
from packages.db.release_store import ReleaseStore
from packages.policies.approval_tokens import issue_token, verify_and_burn_token, record_second_factor
from packages.policies.approvals import (
    PolicyViolation,
    is_approval_granted,
)
from packages.policies.release_readiness import (
    APP_STORE_SUBMISSION_APPROVAL_TYPE,
    approve_app_store_submission,
)
from packages.schemas.approval import ApprovalStatus
from packages.schemas.release import (
    BuildCandidate,
    BuildStatus,
    MetadataDraft,
    MetadataStatus,
    ReleaseRecord,
    ReleaseStatus,
    ScreenshotSet,
    ScreenshotStatus,
    StoreChannelStatus,
)


SECRET = b"test-release-readiness-secret"


def _write_checklist(isolated_repo_root: Path, *, unchecked: int) -> None:
    docs = isolated_repo_root / "docs" / "products" / "catchbook"
    docs.mkdir(parents=True, exist_ok=True)
    lines = ["# submission-checklist", ""]
    lines += [f"- [x] done item {i}" for i in range(3)]
    lines += [f"- [ ] todo item {i}" for i in range(unchecked)]
    (docs / "submission-checklist.md").write_text("\n".join(lines) + "\n")


def _seed_release(release_id: str, *, status: ReleaseStatus) -> None:
    now = datetime.now(timezone.utc).isoformat()
    store = ReleaseStore()
    bc = BuildCandidate(
        id=f"build-{release_id}",
        product_id="catchbook",
        repo_id="catchbook-ios",
        source_task_run_id="run-x",
        version="0.1.0",
        build_number="1",
        artifact_paths=[],
        status=BuildStatus.READY,
        created_at=now,
    )
    md = MetadataDraft(
        id=f"metadata-{release_id}",
        product_id="catchbook",
        locale="en-US",
        path="docs/products/catchbook/app-store-positioning.md",
        status=MetadataStatus.READY,
        created_at=now,
    )
    ss = ScreenshotSet(
        id=f"screenshots-{release_id}",
        product_id="catchbook",
        locale="en-US",
        device_family="iphone",
        asset_paths=[],
        status=ScreenshotStatus.READY,
        created_at=now,
    )
    rec = ReleaseRecord(
        id=release_id,
        product_id="catchbook",
        build_candidate_id=bc.id,
        metadata_draft_id=md.id,
        screenshot_set_id=ss.id,
        testflight_status=StoreChannelStatus.NOT_STARTED,
        appstore_status=StoreChannelStatus.NOT_STARTED,
        status=status,
        created_at=now,
        updated_at=now,
    )
    store.save_build_candidate(bc)
    store.save_metadata_draft(md)
    store.save_screenshot_set(ss)
    store.save_release_record(rec)


def _seed_p0_token_and_approve(
    approval_id: str,
    subject_id: str,
    *,
    service: ControlPlaneService,
) -> None:
    token_store = ApprovalTokenStore()
    token = issue_token(
        approval_id=approval_id,
        subject_id=subject_id,
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
    # P0 → second factor within window
    from datetime import timedelta
    record_second_factor(
        token_id=token.token_id,
        provided_signature=token.signature,
        device_fingerprint="mac-local",
        secret=SECRET,
        store=token_store,
        now=datetime.fromisoformat(burned.approved_at) + timedelta(seconds=5),
    )
    service.decide_approval(
        approval_id=approval_id,
        status=ApprovalStatus.APPROVED,
        decided_by="magic-link-p0:mac-local",
    )


def test_is_approval_granted_returns_false_for_missing(isolated_repo_root) -> None:
    assert is_approval_granted("nope", "x") is False


def test_is_approval_granted_type_mismatch(isolated_repo_root) -> None:
    service = ControlPlaneService()
    approval = service.request_approval(
        summary="x",
        subject_type="release",
        subject_id="release-x",
        action="submit_appstore",
        approval_type="some_other_type",
    )
    service.decide_approval(
        approval_id=approval.id,
        status=ApprovalStatus.APPROVED,
        decided_by="test",
    )
    assert is_approval_granted(approval.id, APP_STORE_SUBMISSION_APPROVAL_TYPE) is False


def test_missing_checklist_raises(isolated_repo_root) -> None:
    with pytest.raises(PolicyViolation) as exc:
        approve_app_store_submission(
            "release-catchbook-v0.1.0",
            "approval-x",
        )
    assert exc.value.code == "submission_checklist_missing"


def test_unchecked_items_raise(isolated_repo_root) -> None:
    _write_checklist(isolated_repo_root, unchecked=2)
    with pytest.raises(PolicyViolation) as exc:
        approve_app_store_submission(
            "release-catchbook-v0.1.0",
            "approval-x",
        )
    assert exc.value.code == "submission_checklist_incomplete"


def test_approval_not_granted_raises(isolated_repo_root) -> None:
    _write_checklist(isolated_repo_root, unchecked=0)
    with pytest.raises(PolicyViolation) as exc:
        approve_app_store_submission(
            "release-catchbook-v0.1.0",
            "approval-missing",
        )
    assert exc.value.code == "approval_not_granted"


def test_release_not_ready_raises(isolated_repo_root) -> None:
    _write_checklist(isolated_repo_root, unchecked=0)
    service = ControlPlaneService()
    approval = service.request_approval(
        summary="submit",
        subject_type="release",
        subject_id="release-catchbook-v0.1.0",
        action="submit_appstore",
        approval_type=APP_STORE_SUBMISSION_APPROVAL_TYPE,
    )
    _seed_release("release-catchbook-v0.1.0", status=ReleaseStatus.DRAFT)
    _seed_p0_token_and_approve(
        approval.id, "release-catchbook-v0.1.0", service=service
    )

    with pytest.raises(PolicyViolation) as exc:
        approve_app_store_submission(
            "release-catchbook-v0.1.0",
            approval.id,
        )
    assert exc.value.code == "release_not_ready"


def test_happy_path_passes(isolated_repo_root) -> None:
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
    assert release.status is ReleaseStatus.READY_FOR_REVIEW
