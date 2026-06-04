"""Agency Phases 3–5 — client lifecycle orchestration."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from packages.agency.client_lifecycle import (
    LaunchNotReadyError,
    apply_client_intake,
    intake_from_prospect,
    mark_client_live,
    scaffold_client_product,
)
from packages.agency.intake import ClientIntake
from packages.agency.promotion import promote_prospect_to_client
from packages.schemas.product import ProductPhase
from packages.schemas.prospect import HumanVerified, ProspectRecord


def _prospect() -> ProspectRecord:
    return ProspectRecord(
        place_id="places/joe123",
        display_name="Joe's Plumbing",
        formatted_address="1 Main St, Seattle, WA",
        phone="206-555-0100",
        types=["plumber"],
        city_id="seattle",
        genre_id="plumber",
        grid_cell_id="seattle:plumber",
        human_verified=HumanVerified.TRUE,
    )


def _paths(tmp_path: Path) -> dict:
    registry = tmp_path / "products.json"
    registry.write_text("[]", encoding="utf-8")
    return {
        "registry_path": registry,
        "docs_root_parent": tmp_path / "docs" / "products",
        "repo_root": tmp_path,
    }


def test_intake_from_prospect_uses_genre_defaults() -> None:
    intake = intake_from_prospect(_prospect())
    assert intake.business_name == "Joe's Plumbing"
    assert intake.service_category == "plumbing"
    assert "206-555-0100" in intake.phone


def test_apply_client_intake_writes_brief_and_copy(tmp_path: Path) -> None:
    docs = tmp_path / "joes-plumbing-site"
    intake = ClientIntake(
        business_name="Joe's Plumbing",
        service_category="plumbing",
        city="Seattle",
        services=["Drain cleaning"],
        phone="206-555-0100",
        service_area_cities=["Seattle", "Shoreline"],
        travel_radius_miles=15,
        service_area_notes="No jobs east of Bellevue.",
    )
    apply_client_intake(docs, intake, bundle_id="package_a", from_prospect="places/joe123")
    brief = (docs / "CLIENT_BRIEF.md").read_text()
    copy = (docs / "COPY.md").read_text()
    local_seo = (docs / "LOCAL_SEO.md").read_text()
    assert "Drain cleaning" in brief
    assert "206-555-0100" in copy
    assert 'service_area_cities: ["Seattle", "Shoreline"]' in local_seo
    assert "matrix_approved: false" in local_seo
    assert "| Drain cleaning | Shoreline | |" in local_seo


def test_scaffold_client_product_materializes_astro(tmp_path: Path) -> None:
    intake = ClientIntake(
        business_name="Joe's Plumbing",
        service_category="plumbing",
        city="Seattle",
        services=["Drain cleaning"],
        phone="206-555-0100",
    )
    product_dir = scaffold_client_product("joes-plumbing-site", intake, repo_root=tmp_path)
    assert (product_dir / "src" / "pages" / "index.astro").exists()


def test_promote_intake_launch_end_to_end(tmp_path: Path) -> None:
    p = _paths(tmp_path)
    prospect = _prospect()
    reg = promote_prospect_to_client(
        prospect, "package_a", approval_granted=True, mark_onboarded=False, **p
    )
    product_id = str(reg["id"])
    intake = intake_from_prospect(prospect)
    docs_root = p["docs_root_parent"] / product_id
    apply_client_intake(docs_root, intake, bundle_id="package_a", from_prospect=prospect.place_id)

    from packages.web.scaffold import render_landing_html

    dist = tmp_path / "dist"
    dist.mkdir()
    gbp = "https://maps.google.com/?cid=999"
    analytics = "plausible-joes"
    html = render_landing_html(intake.to_site_context())
    html = html.replace("</body>", f'<a href="{gbp}">GBP</a>\n<script data-domain="{analytics}"></script>\n</body>')
    (dist / "index.html").write_text(html)

    report = mark_client_live(
        product_id,
        dist,
        gbp_url=gbp,
        analytics_id=analytics,
        deploy_approved=True,
        dns_approved=True,
        registry_path=p["registry_path"],
    )
    assert report.ready
    updated = json.loads(p["registry_path"].read_text())
    record = next(r for r in updated if r["id"] == product_id)
    assert record["phase"] == ProductPhase.LIVE.value


def test_mark_live_fails_without_approvals(tmp_path: Path) -> None:
    p = _paths(tmp_path)
    reg = promote_prospect_to_client(
        _prospect(), "package_a", approval_granted=True, mark_onboarded=False, **p
    )
    product_id = str(reg["id"])
    dist = tmp_path / "dist"
    dist.mkdir()
    (dist / "index.html").write_text("<html><head><title>x</title></head><body><form></form></body></html>")
    with pytest.raises(LaunchNotReadyError):
        mark_client_live(product_id, dist, registry_path=p["registry_path"])
