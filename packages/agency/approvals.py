"""Retainer approval contracts for agency operations."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from packages.schemas.approval import ApprovalRecord, ApprovalStatus


CLIENT_SITE_SUBJECT_TYPE = "client_site"


@dataclass(frozen=True)
class RetainerApprovalSpec:
    approval_type: str
    action: str
    subject_type: str
    requires_artifact: bool = False


class RetainerApprovalRequester(Protocol):
    def request_approval(
        self,
        *,
        summary: str,
        subject_type: str,
        subject_id: str,
        action: str,
        approval_type: str,
        task_id: str | None = None,
        task_run_id: str | None = None,
        review_artifact_path: str | None = None,
        approval_id: str | None = None,
    ) -> ApprovalRecord: ...


RETAINER_APPROVALS: dict[str, RetainerApprovalSpec] = {
    "client_site_deploy": RetainerApprovalSpec(
        approval_type="client_site_deploy",
        action="publish_client_site_change",
        subject_type=CLIENT_SITE_SUBJECT_TYPE,
        requires_artifact=True,
    ),
    "client_dns_change": RetainerApprovalSpec(
        approval_type="client_dns_change",
        action="update_client_dns",
        subject_type=CLIENT_SITE_SUBJECT_TYPE,
        requires_artifact=True,
    ),
    "review_sms_activation": RetainerApprovalSpec(
        approval_type="review_sms_activation",
        action="activate_review_sms",
        subject_type=CLIENT_SITE_SUBJECT_TYPE,
        requires_artifact=True,
    ),
    "review_sms_template_change": RetainerApprovalSpec(
        approval_type="review_sms_template_change",
        action="change_review_sms_template",
        subject_type=CLIENT_SITE_SUBJECT_TYPE,
        requires_artifact=True,
    ),
    "ad_campaign_go_live": RetainerApprovalSpec(
        approval_type="ad_campaign_go_live",
        action="launch_google_ads_campaign",
        subject_type=CLIENT_SITE_SUBJECT_TYPE,
        requires_artifact=True,
    ),
    "ad_budget_change": RetainerApprovalSpec(
        approval_type="ad_budget_change",
        action="change_ad_budget",
        subject_type=CLIENT_SITE_SUBJECT_TYPE,
        requires_artifact=True,
    ),
    "stripe_live_subscription": RetainerApprovalSpec(
        approval_type="stripe_live_subscription",
        action="create_live_stripe_subscription",
        subject_type=CLIENT_SITE_SUBJECT_TYPE,
        requires_artifact=True,
    ),
    "analytics_overage_pass_through": RetainerApprovalSpec(
        approval_type="analytics_overage_pass_through",
        action="invoice_analytics_overage",
        subject_type=CLIENT_SITE_SUBJECT_TYPE,
        requires_artifact=True,
    ),
}


def retainer_approval_spec(approval_type: str) -> RetainerApprovalSpec:
    try:
        return RETAINER_APPROVALS[approval_type]
    except KeyError as exc:
        raise ValueError(f"unknown retainer approval type: {approval_type}") from exc


def request_retainer_approval(
    *,
    product_id: str,
    approval_type: str,
    summary: str,
    service: RetainerApprovalRequester,
    review_artifact_path: str | Path | None = None,
    approval_id: str | None = None,
) -> ApprovalRecord:
    """Create a canonical approval record for one client-site retainer action."""
    spec = retainer_approval_spec(approval_type)
    artifact = str(review_artifact_path) if review_artifact_path else None
    return service.request_approval(
        approval_id=approval_id,
        approval_type=spec.approval_type,
        action=spec.action,
        subject_type=spec.subject_type,
        subject_id=product_id,
        summary=summary,
        review_artifact_path=artifact,
    )


def pending_retainer_approvals(
    approvals: list[ApprovalRecord],
) -> list[ApprovalRecord]:
    """Filter pending approval records to the retainer approval contract."""
    known = set(RETAINER_APPROVALS)
    return [
        approval
        for approval in approvals
        if approval.status is ApprovalStatus.PENDING
        and approval.approval_type in known
        and approval.subject_type == CLIENT_SITE_SUBJECT_TYPE
    ]
