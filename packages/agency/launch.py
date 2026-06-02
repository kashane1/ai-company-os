"""Client-site launch checklist (Agency layer, Phase 5).

A repeatable, fail-closed pre-launch gate. It composes the pure web-lane
callables — ``packages.web.ux_audit.audit_dist`` for site quality and
``packages.policies.deploy_readiness`` for the deploy/DNS approvals — rather than
the agentic ``web-ux-audit`` skill (which is blocked from autonomous load). A
client site cannot be marked live until every item passes.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from packages.policies.approvals import PolicyViolation
from packages.policies.deploy_readiness import (
    assert_custom_domain_allowed,
    assert_deploy_ready,
)
from packages.web.ux_audit import audit_dist


@dataclass(frozen=True)
class ChecklistItem:
    name: str
    passed: bool
    detail: str = ""

    def to_dict(self) -> dict[str, object]:
        return {"name": self.name, "passed": self.passed, "detail": self.detail}


@dataclass(frozen=True)
class LaunchChecklistReport:
    items: list[ChecklistItem]

    @property
    def ready(self) -> bool:
        """Fail closed: ready only when every item passes."""
        return all(item.passed for item in self.items)

    def failures(self) -> list[ChecklistItem]:
        return [item for item in self.items if not item.passed]

    def to_dict(self) -> dict[str, object]:
        return {"ready": self.ready, "items": [i.to_dict() for i in self.items]}


def run_launch_checklist(
    dist_dir: Path,
    *,
    gbp_url: str = "",
    analytics_id: str = "",
    deploy_approved: bool = False,
    dns_approved: bool = False,
    pass_threshold: int = 70,
) -> LaunchChecklistReport:
    """Evaluate a built ``dist/`` for launch readiness. Never raises."""
    html = _concat_html(dist_dir)
    items: list[ChecklistItem] = []

    # Site quality — compose the UX audit (responsive / a11y / perf / SEO).
    report = audit_dist(dist_dir, pass_threshold=pass_threshold)
    items.append(
        ChecklistItem(
            "ux_audit",
            report.passed,
            f"overall {report.overall}; {report.scores}",
        )
    )

    # Content presence checks (fail closed on missing essentials).
    items.append(
        ChecklistItem("contact_form", "<form" in html.lower(), "a contact form is present")
    )
    items.append(ChecklistItem("seo_title", "<title" in html.lower(), "page has a <title>"))
    items.append(
        ChecklistItem(
            "gbp_link",
            bool(gbp_url) and gbp_url in html,
            "Google Business Profile link present" if gbp_url else "no gbp_url supplied",
        )
    )
    items.append(
        ChecklistItem(
            "analytics",
            bool(analytics_id) and analytics_id in html,
            "analytics tag present" if analytics_id else "no analytics_id supplied",
        )
    )

    # Deploy approvals — compose the deploy-readiness policy gates.
    items.append(_gate_item("deploy_approved", lambda: assert_deploy_ready(
        production=True,
        gate_passed=report.passed,
        preview_reviewed=True,
        approval_granted=deploy_approved,
    )))
    items.append(_gate_item("dns_approved", lambda: assert_custom_domain_allowed(
        approval_granted=dns_approved,
    )))

    return LaunchChecklistReport(items=items)


def _gate_item(name: str, gate) -> ChecklistItem:
    try:
        gate()
        return ChecklistItem(name, True, "approval granted")
    except PolicyViolation as exc:
        return ChecklistItem(name, False, f"[{exc.code}] {exc}")


def _concat_html(dist_dir: Path) -> str:
    if not dist_dir.is_dir():
        return ""
    return "\n".join(
        p.read_text(encoding="utf-8", errors="ignore")
        for p in sorted(dist_dir.rglob("*.html"))
        if p.is_file()
    )
