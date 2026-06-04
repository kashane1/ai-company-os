"""Monthly retainer orchestration for client-site services."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class RetainerRun:
    product_id: str
    month: str
    services: list[str]
    planned_actions: list[str] = field(default_factory=list)
    blocked_approvals: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return {
            "product_id": self.product_id,
            "month": self.month,
            "services": list(self.services),
            "planned_actions": list(self.planned_actions),
            "blocked_approvals": list(self.blocked_approvals),
        }


def plan_retainer_run(record: dict[str, object], *, month: str) -> RetainerRun:
    client = dict(record.get("client") or {})
    services = [str(service) for service in list(client.get("services", []))]
    planned: list[str] = []
    blocked: list[str] = []
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
    if "reviews" in services:
        planned.append("draft_review_readiness")
        blocked.append("review_sms_activation")
    return RetainerRun(
        product_id=str(record["id"]),
        month=month,
        services=services,
        planned_actions=planned,
        blocked_approvals=blocked,
    )


def write_retainer_run(state_root: Path, run: RetainerRun) -> Path:
    path = state_root / "clients" / run.product_id / "retainer-runs" / f"{run.month}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(run.to_dict(), indent=2) + "\n", encoding="utf-8")
    return path
