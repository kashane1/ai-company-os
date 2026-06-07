"""Monthly retainer orchestration for client-site services.

Planning is fenced to **active billing** ([G1]/[E2]): a `past_due`, `cancelled`,
`disputed`, or `refunded` client gets an empty plan with a `skipped_reason`, so
the operator never does paid work for a client who isn't paying.

A planned action is not the same as a done one. Each run is persisted with the
set of `completed_actions`, and :func:`mark_action_complete` /
:func:`outstanding_actions` let the operator (or an executor) track a month's
work to completion instead of leaving it as an unactioned wishlist.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from packages.schemas.product import BillingStatus


@dataclass(frozen=True)
class RetainerRun:
    product_id: str
    month: str
    services: list[str]
    planned_actions: list[str] = field(default_factory=list)
    blocked_approvals: list[str] = field(default_factory=list)
    completed_actions: list[str] = field(default_factory=list)
    billing_status: str = ""
    skipped_reason: str = ""

    def outstanding_actions(self) -> list[str]:
        """Planned actions not yet marked complete (the open work for the month)."""
        done = set(self.completed_actions)
        return [action for action in self.planned_actions if action not in done]

    def is_complete(self) -> bool:
        """True once every planned action has been completed."""
        return not self.outstanding_actions()

    def to_dict(self) -> dict[str, object]:
        return {
            "product_id": self.product_id,
            "month": self.month,
            "services": list(self.services),
            "planned_actions": list(self.planned_actions),
            "blocked_approvals": list(self.blocked_approvals),
            "completed_actions": list(self.completed_actions),
            "billing_status": self.billing_status,
            "skipped_reason": self.skipped_reason,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> "RetainerRun":
        return cls(
            product_id=str(payload["product_id"]),
            month=str(payload["month"]),
            services=[str(s) for s in list(payload.get("services", []))],
            planned_actions=[str(a) for a in list(payload.get("planned_actions", []))],
            blocked_approvals=[str(a) for a in list(payload.get("blocked_approvals", []))],
            completed_actions=[str(a) for a in list(payload.get("completed_actions", []))],
            billing_status=str(payload.get("billing_status", "")),
            skipped_reason=str(payload.get("skipped_reason", "")),
        )


def plan_retainer_run(record: dict[str, object], *, month: str) -> RetainerRun:
    client = dict(record.get("client") or {})
    services = [str(service) for service in list(client.get("services", []))]

    # [G1] Fence paid work to an actively-billed client. A missing/garbage status
    # coerces to a work-stopping state, so we fail loudly-safe, never entitled.
    status = BillingStatus.coerce(client.get("billing_status", ""))
    if status is not BillingStatus.ACTIVE:
        return RetainerRun(
            product_id=str(record["id"]),
            month=month,
            services=services,
            billing_status=status.value,
            skipped_reason=f"client billing is {status.value}, not active — no paid work planned",
        )

    planned: list[str] = []
    blocked: list[str] = []
    if "hosting" in services:
        # The $49/mo plan promises "contact-form monitoring": confirm each client
        # site's lead pipeline is still capturing + delivering (see lead_health.py).
        planned.append("check_lead_health")
    if "local_seo" in services:
        planned.append("run_local_seo")
        blocked.append("client_site_deploy")
    if "monthly_reporting" in services:
        planned.append("run_monthly_report")
    if "gbp" in services:
        planned.append("draft_gbp_changeset")
    if "google_ads" in services:
        planned.append("draft_google_ads")
        blocked.append("ad_campaign_go_live")
    if "meta_ads" in services:
        planned.append("draft_meta_ads")
        # Same go-live gate as Google Ads; don't double-list it.
        if "ad_campaign_go_live" not in blocked:
            blocked.append("ad_campaign_go_live")
    if "reviews" in services:
        planned.append("draft_review_readiness")
        blocked.append("review_sms_activation")
    if "booking_native" in services or "booking_management" in services:
        # Managed booking: process up to ~2 change requests, glance at no-shows,
        # check the booking link + calendar sync still work (see client-sla.md).
        planned.append("manage_booking")
    if "follow_up_automation" in services:
        # Recurring: review/tune the email follow-up sequences + task reminders.
        planned.append("review_follow_up")
    return RetainerRun(
        product_id=str(record["id"]),
        month=month,
        services=services,
        planned_actions=planned,
        blocked_approvals=blocked,
        billing_status=status.value,
    )


def retainer_run_path(state_root: Path, product_id: str, month: str) -> Path:
    return state_root / "clients" / product_id / "retainer-runs" / f"{month}.json"


def write_retainer_run(state_root: Path, run: RetainerRun) -> Path:
    path = retainer_run_path(state_root, run.product_id, run.month)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(run.to_dict(), indent=2) + "\n", encoding="utf-8")
    return path


def read_retainer_run(state_root: Path, product_id: str, month: str) -> RetainerRun:
    path = retainer_run_path(state_root, product_id, month)
    return RetainerRun.from_dict(json.loads(path.read_text(encoding="utf-8")))


def mark_action_complete(
    state_root: Path, product_id: str, month: str, action: str
) -> RetainerRun:
    """Record one planned action as done and persist the updated run.

    Raises ``ValueError`` if ``action`` was never planned for this run (so a typo
    can't silently mark a non-existent task complete). Idempotent for an action
    already completed.
    """
    run = read_retainer_run(state_root, product_id, month)
    if action not in run.planned_actions:
        raise ValueError(
            f"{action!r} is not a planned action for {product_id} {month}: "
            f"{run.planned_actions}"
        )
    if action not in run.completed_actions:
        run = RetainerRun(
            product_id=run.product_id,
            month=run.month,
            services=run.services,
            planned_actions=run.planned_actions,
            blocked_approvals=run.blocked_approvals,
            completed_actions=[*run.completed_actions, action],
            billing_status=run.billing_status,
            skipped_reason=run.skipped_reason,
        )
        write_retainer_run(state_root, run)
    return run


def outstanding_actions(state_root: Path, product_id: str, month: str) -> list[str]:
    """The planned actions still open for a persisted run (its SLA backlog)."""
    return read_retainer_run(state_root, product_id, month).outstanding_actions()
