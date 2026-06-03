"""Agency layer Phase 5 — launch checklist (fail-closed delivery gate)."""

from __future__ import annotations

from pathlib import Path

from packages.agency.launch import run_launch_checklist
from packages.web.scaffold import local_business_context, render_landing_html

GBP = "https://maps.google.com/?cid=12345"
ANALYTICS = "plausible-joes-plumbing"


def _build_dist(tmp_path: Path, *, gbp: str = GBP, analytics: str = ANALYTICS) -> Path:
    ctx = local_business_context(
        "Joe's Plumbing",
        service_category="plumbing",
        city="Seattle",
        services=["Drain cleaning"],
        phone="206-555-0100",
    )
    html = render_landing_html(ctx)
    # Inject the GBP link + analytics tag a launched site would carry.
    extra = ""
    if gbp:
        extra += f'\n<a href="{gbp}">Find us on Google</a>'
    if analytics:
        extra += f'\n<script data-domain="{analytics}"></script>'
    html = html.replace("</body>", f"{extra}\n</body>") if "</body>" in html else html + extra
    dist = tmp_path / "dist"
    dist.mkdir()
    (dist / "index.html").write_text(html)
    return dist


def test_fully_ready_site_passes(tmp_path: Path) -> None:
    dist = _build_dist(tmp_path)
    report = run_launch_checklist(
        dist,
        gbp_url=GBP,
        analytics_id=ANALYTICS,
        deploy_approved=True,
        dns_approved=True,
    )
    assert report.ready, report.to_dict()


def test_missing_approvals_fail_closed(tmp_path: Path) -> None:
    dist = _build_dist(tmp_path)
    report = run_launch_checklist(
        dist, gbp_url=GBP, analytics_id=ANALYTICS, deploy_approved=False, dns_approved=False
    )
    assert not report.ready
    failed = {i.name for i in report.failures()}
    assert {"deploy_approved", "dns_approved"} <= failed


def test_missing_gbp_and_analytics_fail_closed(tmp_path: Path) -> None:
    dist = _build_dist(tmp_path, gbp="", analytics="")
    report = run_launch_checklist(
        dist, gbp_url="", analytics_id="", deploy_approved=True, dns_approved=True
    )
    assert not report.ready
    failed = {i.name for i in report.failures()}
    assert "gbp_link" in failed
    assert "analytics" in failed


def test_first_party_relaxes_gbp_analytics_dns(tmp_path: Path) -> None:
    # The agency's own site: no GBP, no analytics, no custom domain (subdomain).
    dist = _build_dist(tmp_path, gbp="", analytics="")
    report = run_launch_checklist(
        dist,
        gbp_url="",
        analytics_id="",
        deploy_approved=True,
        dns_approved=False,
        first_party=True,
    )
    assert report.ready, report.to_dict()
    relaxed = {i.name: i.detail for i in report.items if "relaxed" in i.detail}
    assert {"gbp_link", "analytics", "dns_approved"} <= set(relaxed)


def test_first_party_still_requires_deploy_approval(tmp_path: Path) -> None:
    dist = _build_dist(tmp_path, gbp="", analytics="")
    report = run_launch_checklist(
        dist, gbp_url="", analytics_id="", deploy_approved=False, first_party=True
    )
    assert not report.ready
    assert "deploy_approved" in {i.name for i in report.failures()}


def test_empty_dist_fails_ux(tmp_path: Path) -> None:
    dist = tmp_path / "dist"
    dist.mkdir()
    (dist / "index.html").write_text("<html><body>nothing</body></html>")
    report = run_launch_checklist(dist, deploy_approved=True, dns_approved=True)
    assert not report.ready
    assert any(i.name == "ux_audit" and not i.passed for i in report.items)
