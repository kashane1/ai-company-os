"""Agency-layer approval gates (Phase 3).

Promoting a prospect into a paying client and sending a proposal are
irreversible, externally-visible commitments. Like the web-deploy lane
(``deploy_readiness``) and App Store releases (``release_readiness``), policy is
owned here — not by the promotion code or a CLI — and a refusal raises
:class:`~packages.policies.approvals.PolicyViolation` with a machine-readable
code.

Irreversible agency actions use stored approval records bound to the requested
action, subject, and reviewed revision. A caller-provided boolean is not
authorization.
"""

from __future__ import annotations

from pathlib import Path

from packages.agency.approvals import retainer_approval_spec
from packages.db.approval_store import ApprovalStore
from packages.policies.approval_bindings import (
    PROMOTION_ACTION,
    PROMOTION_APPROVAL_TYPE,
    PROMOTION_SUBJECT_TYPE,
    assert_approval_binding,
)
from packages.policies.approvals import PolicyViolation, PolicyViolationCode
from packages.schemas.approval import ApprovalStatus
from packages.schemas.product import BillingStatus


def assert_billing_active(billing_status: BillingStatus | str, *, product_id: str = "") -> None:
    """Refuse paid client work unless the client is actively billed.

    Read the **ledger** status ([X-SOT]) and call this before any retainer/
    fulfilment work. ``past_due``/``cancelled``/``disputed``/``refunded`` all
    stop work — this is what closes the "disputed client keeps getting paid
    work" loop (G1 + retainer [E2]).
    """
    status = BillingStatus.coerce(billing_status)
    if status is not BillingStatus.ACTIVE:
        raise PolicyViolation(
            PolicyViolationCode.RETAINER_CLIENT_NOT_ACTIVE,
            f"client {product_id or '?'} is {status.value}, not active — refusing paid work",
        )


def assert_promotion_allowed(
    *,
    human_verified: bool,
    approval_id: str | None,
    prospect_id: str,
    reviewed_revision: str,
    store: ApprovalStore | None = None,
) -> None:
    """Authorize promoting a prospect into a client engagement, or raise.

    Two preconditions, both surfaced as ``CLIENT_PROMOTION_NOT_APPROVED`` with a
    distinguishing detail:

    * the prospect must be human-verified (the no-owned-website signal still
      holds) — promotion off an unverified prospect is refused;
    * a stored founder approval must exactly bind this commercial commitment.
    """
    if not human_verified:
        raise PolicyViolation(
            PolicyViolationCode.CLIENT_PROMOTION_NOT_APPROVED,
            "prospect is not human-verified; refuse to promote until the "
            "no-owned-website signal is confirmed",
        )
    assert_approval_binding(
        approval_id,
        approval_type=PROMOTION_APPROVAL_TYPE,
        subject_type=PROMOTION_SUBJECT_TYPE,
        subject_id=prospect_id,
        action=PROMOTION_ACTION,
        reviewed_revision=reviewed_revision,
        violation_code=PolicyViolationCode.CLIENT_PROMOTION_NOT_APPROVED,
        store=store,
    )


def assert_proposal_send_allowed(*, approval_granted: bool) -> None:
    """Sending a proposal to a prospect always requires approval."""
    if not approval_granted:
        raise PolicyViolation(
            PolicyViolationCode.PROPOSAL_SEND_NOT_APPROVED,
            "sending a proposal requires a granted approval",
        )


def assert_retainer_approval_granted(
    approval_id: str,
    *,
    product_id: str,
    approval_type: str,
    store: ApprovalStore | None = None,
) -> None:
    """Authorize one client retainer action with a correctly scoped approval.

    Approval records are not interchangeable: the type, action, subject type,
    subject id, and required artifact must match the requested retainer action.
    """
    spec = retainer_approval_spec(approval_type)
    approvals = store or ApprovalStore()
    try:
        record = approvals.load(approval_id)
    except FileNotFoundError as exc:
        raise PolicyViolation(
            PolicyViolationCode.RETAINER_APPROVAL_NOT_GRANTED,
            f"approval {approval_id!r} not found",
        ) from exc

    if record.status is not ApprovalStatus.APPROVED:
        raise PolicyViolation(
            PolicyViolationCode.RETAINER_APPROVAL_NOT_GRANTED,
            f"approval {approval_id!r} is {record.status.value}, not approved",
        )
    if (
        record.approval_type != spec.approval_type
        or record.action != spec.action
        or record.subject_type != spec.subject_type
        or record.subject_id != product_id
    ):
        raise PolicyViolation(
            PolicyViolationCode.RETAINER_APPROVAL_NOT_GRANTED,
            "approval does not match requested retainer action/client",
        )
    if spec.requires_artifact:
        artifact = record.review_artifact_path
        if not artifact or not Path(artifact).exists():
            raise PolicyViolation(
                PolicyViolationCode.RETAINER_APPROVAL_ARTIFACT_MISSING,
                f"approval {approval_id!r} is missing required review artifact",
            )


def assert_ad_campaign_go_live(
    approval_id: str,
    *,
    product_id: str,
    daily_budget: float | None,
    monthly_budget: float | None,
    store: ApprovalStore | None = None,
) -> None:
    """Authorize taking a Google Ads campaign live.

    Live ads spend the client's money continuously, so [D7] requires a positive
    daily AND monthly budget cap (a denial-of-wallet guard) on top of the granted
    ``ad_campaign_go_live`` approval. Spend ownership stays with the client.
    """
    if not (daily_budget and daily_budget > 0) or not (monthly_budget and monthly_budget > 0):
        raise PolicyViolation(
            PolicyViolationCode.AD_BUDGET_CAP_MISSING,
            "ad campaign go-live requires positive daily AND monthly budget caps",
        )
    assert_retainer_approval_granted(
        approval_id,
        product_id=product_id,
        approval_type="ad_campaign_go_live",
        store=store,
    )


def assert_review_sms_allowed(
    *,
    docs_root: Path,
    product_id: str,
    approval_id: str,
    template_approved: bool,
    quiet_hours_configured: bool = True,
    frequency_cap_days: int = 90,
    store: ApprovalStore | None = None,
) -> None:
    """Authorize live review SMS only after compliance and approval gates."""
    signed = docs_root / "compliance" / "review-sms-consent-signed.pdf"
    if not signed.exists():
        raise PolicyViolation(
            PolicyViolationCode.REVIEW_SMS_COMPLIANCE_MISSING,
            f"signed review SMS addendum not found at {signed}",
        )
    if not template_approved:
        raise PolicyViolation(
            PolicyViolationCode.REVIEW_SMS_TEMPLATE_NOT_APPROVED,
            "review SMS template must be approved before live sends",
        )
    if not quiet_hours_configured or frequency_cap_days <= 0:
        raise PolicyViolation(
            PolicyViolationCode.REVIEW_SMS_CADENCE_INVALID,
            "review SMS quiet hours and positive frequency cap are required",
        )
    assert_retainer_approval_granted(
        approval_id,
        product_id=product_id,
        approval_type="review_sms_activation",
        store=store,
    )
