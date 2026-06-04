from pathlib import Path

import pytest

from packages.agency.approvals import (
    pending_retainer_approvals,
    request_retainer_approval,
)
from packages.db.approval_store import ApprovalStore
from packages.policies.agency_gates import assert_retainer_approval_granted
from packages.policies.agency_gates import assert_review_sms_allowed
from packages.policies.approvals import PolicyViolation
from packages.schemas.approval import ApprovalRecord, ApprovalStatus


class _Requester:
    def __init__(self) -> None:
        self.approvals: list[ApprovalRecord] = []

    def request_approval(self, **kwargs) -> ApprovalRecord:
        approval = ApprovalRecord(
            id=kwargs.get("approval_id") or "approval-1",
            status=ApprovalStatus.PENDING,
            summary=kwargs["summary"],
            created_at="2026-06-03T00:00:00+00:00",
            approval_type=kwargs["approval_type"],
            subject_type=kwargs["subject_type"],
            subject_id=kwargs["subject_id"],
            action=kwargs["action"],
            review_artifact_path=kwargs.get("review_artifact_path"),
        )
        self.approvals.append(approval)
        return approval


def test_request_retainer_approval_uses_contract_fields(tmp_path: Path) -> None:
    requester = _Requester()
    artifact = tmp_path / "ads.md"

    approval = request_retainer_approval(
        product_id="joes-plumbing-site",
        approval_type="ad_campaign_go_live",
        summary="Launch ads",
        review_artifact_path=artifact,
        approval_id="approval-ads",
        service=requester,
    )

    assert approval.id == "approval-ads"
    assert approval.approval_type == "ad_campaign_go_live"
    assert approval.action == "launch_google_ads_campaign"
    assert approval.subject_type == "client_site"
    assert approval.subject_id == "joes-plumbing-site"
    assert approval.review_artifact_path == str(artifact)


def test_retainer_gate_rejects_wrong_type(isolated_repo_root, tmp_path: Path) -> None:
    artifact = tmp_path / "artifact.md"
    artifact.write_text("ok", encoding="utf-8")
    store = ApprovalStore()
    store.save(
        ApprovalRecord(
            id="approval-1",
            status=ApprovalStatus.APPROVED,
            summary="Wrong type",
            created_at="2026-06-03T00:00:00+00:00",
            approval_type="client_site_deploy",
            subject_type="client_site",
            subject_id="joes-plumbing-site",
            action="publish_client_site_change",
            review_artifact_path=str(artifact),
        )
    )

    with pytest.raises(PolicyViolation) as exc:
        assert_retainer_approval_granted(
            "approval-1",
            product_id="joes-plumbing-site",
            approval_type="ad_campaign_go_live",
            store=store,
        )
    assert exc.value.code == "retainer_approval_not_granted"


def test_retainer_gate_rejects_wrong_client(isolated_repo_root, tmp_path: Path) -> None:
    artifact = tmp_path / "artifact.md"
    artifact.write_text("ok", encoding="utf-8")
    store = ApprovalStore()
    store.save(
        ApprovalRecord(
            id="approval-1",
            status=ApprovalStatus.APPROVED,
            summary="Launch ads",
            created_at="2026-06-03T00:00:00+00:00",
            approval_type="ad_campaign_go_live",
            subject_type="client_site",
            subject_id="other-client-site",
            action="launch_google_ads_campaign",
            review_artifact_path=str(artifact),
        )
    )

    with pytest.raises(PolicyViolation):
        assert_retainer_approval_granted(
            "approval-1",
            product_id="joes-plumbing-site",
            approval_type="ad_campaign_go_live",
            store=store,
        )


def test_retainer_gate_requires_artifact(isolated_repo_root) -> None:
    store = ApprovalStore()
    store.save(
        ApprovalRecord(
            id="approval-1",
            status=ApprovalStatus.APPROVED,
            summary="Launch ads",
            created_at="2026-06-03T00:00:00+00:00",
            approval_type="ad_campaign_go_live",
            subject_type="client_site",
            subject_id="joes-plumbing-site",
            action="launch_google_ads_campaign",
        )
    )

    with pytest.raises(PolicyViolation) as exc:
        assert_retainer_approval_granted(
            "approval-1",
            product_id="joes-plumbing-site",
            approval_type="ad_campaign_go_live",
            store=store,
        )
    assert exc.value.code == "retainer_approval_artifact_missing"


def test_retainer_gate_accepts_matching_approval(isolated_repo_root, tmp_path: Path) -> None:
    artifact = tmp_path / "artifact.md"
    artifact.write_text("ok", encoding="utf-8")
    store = ApprovalStore()
    store.save(
        ApprovalRecord(
            id="approval-1",
            status=ApprovalStatus.APPROVED,
            summary="Launch ads",
            created_at="2026-06-03T00:00:00+00:00",
            approval_type="ad_campaign_go_live",
            subject_type="client_site",
            subject_id="joes-plumbing-site",
            action="launch_google_ads_campaign",
            review_artifact_path=str(artifact),
        )
    )

    assert_retainer_approval_granted(
        "approval-1",
        product_id="joes-plumbing-site",
        approval_type="ad_campaign_go_live",
        store=store,
    )


def test_pending_retainer_approvals_filters_contract_records() -> None:
    approvals = [
        ApprovalRecord(
            id="retainer",
            status=ApprovalStatus.PENDING,
            summary="Launch ads",
            created_at="2026-06-03T00:00:00+00:00",
            approval_type="ad_campaign_go_live",
            subject_type="client_site",
            subject_id="joes-plumbing-site",
            action="launch_google_ads_campaign",
        ),
        ApprovalRecord(
            id="done",
            status=ApprovalStatus.APPROVED,
            summary="Approved",
            created_at="2026-06-03T00:00:00+00:00",
            approval_type="ad_campaign_go_live",
            subject_type="client_site",
            subject_id="joes-plumbing-site",
            action="launch_google_ads_campaign",
        ),
        ApprovalRecord(
            id="other",
            status=ApprovalStatus.PENDING,
            summary="Other",
            created_at="2026-06-03T00:00:00+00:00",
            approval_type="app_store_submission",
            subject_type="release",
            subject_id="release-1",
            action="submit_appstore",
        ),
    ]

    assert [a.id for a in pending_retainer_approvals(approvals)] == ["retainer"]


def test_review_sms_gate_requires_signed_addendum(isolated_repo_root, tmp_path: Path) -> None:
    with pytest.raises(PolicyViolation) as exc:
        assert_review_sms_allowed(
            docs_root=tmp_path,
            product_id="joes-plumbing-site",
            approval_id="approval-1",
            template_approved=True,
            store=ApprovalStore(),
        )
    assert exc.value.code == "review_sms_compliance_missing"


def test_review_sms_gate_accepts_compliant_approval(isolated_repo_root, tmp_path: Path) -> None:
    signed = tmp_path / "compliance" / "review-sms-consent-signed.pdf"
    signed.parent.mkdir()
    signed.write_text("signed", encoding="utf-8")
    artifact = tmp_path / "review-template.md"
    artifact.write_text("template", encoding="utf-8")
    store = ApprovalStore()
    store.save(
        ApprovalRecord(
            id="approval-1",
            status=ApprovalStatus.APPROVED,
            summary="Activate reviews",
            created_at="2026-06-03T00:00:00+00:00",
            approval_type="review_sms_activation",
            subject_type="client_site",
            subject_id="joes-plumbing-site",
            action="activate_review_sms",
            review_artifact_path=str(artifact),
        )
    )

    assert_review_sms_allowed(
        docs_root=tmp_path,
        product_id="joes-plumbing-site",
        approval_id="approval-1",
        template_approved=True,
        store=store,
    )
