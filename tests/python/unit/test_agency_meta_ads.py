"""Tests for the Meta Ads draft (`meta_ads`) + reuse of the [D7] go-live gate."""

from __future__ import annotations

from pathlib import Path

import pytest

from packages.agency.intake import ClientIntake
from packages.agency.meta_ads import draft_meta_ads, emit_meta_ads_draft
from packages.agency.retainer_ops import plan_retainer_run
from packages.policies.agency_gates import assert_ad_campaign_go_live
from packages.policies.approvals import PolicyViolation


def _intake(**kw) -> ClientIntake:
    base = dict(
        business_name="Joe's Plumbing",
        service_category="plumbing",
        city="Austin, TX",
        services=["Drain cleaning", "Water heaters"],
        service_area_cities=["Austin", "Round Rock"],
    )
    base.update(kw)
    return ClientIntake(**base)


def test_draft_builds_audiences_and_geo() -> None:
    draft = draft_meta_ads(_intake(), daily_budget=25, monthly_budget=600)
    names = [a.name for a in draft.audiences]
    assert "Local prospecting" in names and "Lookalike" in names and "Retargeting" in names
    assert draft.geo_targets == ("Austin", "Round Rock")
    assert draft.objective == "Leads"


def test_creative_limits_respected() -> None:
    draft = draft_meta_ads(
        _intake(business_name="A Very Very Long Business Name That Exceeds The Headline Limit")
    )
    assert all(len(p) <= 125 for p in draft.primary_texts)
    assert all(len(h) <= 40 for h in draft.headlines)
    assert all(len(d) <= 30 for d in draft.descriptions)


def test_markdown_has_sections_and_budget() -> None:
    md = draft_meta_ads(_intake(), daily_budget=25, monthly_budget=600).to_markdown()
    for section in ("Geo targeting", "Audiences", "Placements", "Creative"):
        assert section in md
    assert "$25/day · $600/mo" in md
    assert "[D7]" in md


def test_markdown_can_include_conversion_lab_preflight() -> None:
    md = draft_meta_ads(
        _intake(),
        daily_budget=25,
        monthly_budget=600,
        preflight_summary="Use family safety and fast response as the main angle.",
        conversion_lab_report_path="state/clients/joes/conversion_lab/run/REPORT.md",
    ).to_markdown()

    assert "## Conversion Lab Preflight" in md
    assert "Use family safety and fast response as the main angle." in md
    assert "state/clients/joes/conversion_lab/run/REPORT.md" in md


def test_emit_writes_meta_ads_md(tmp_path: Path) -> None:
    path = emit_meta_ads_draft(_intake(), tmp_path / "joes-site", daily_budget=25, monthly_budget=600)
    assert path == tmp_path / "joes-site" / "META_ADS.md"
    assert "Meta Ads Draft — Joe's Plumbing" in path.read_text(encoding="utf-8")


def test_meta_ads_reuses_the_budget_cap_gate() -> None:
    with pytest.raises(PolicyViolation) as exc:
        assert_ad_campaign_go_live(
            "appr-1", product_id="joes-plumbing-site", daily_budget=None, monthly_budget=600
        )
    assert exc.value.code == "ad_budget_cap_missing"


def test_retainer_plans_meta_ads_without_duplicating_gate() -> None:
    client = {"billing_status": "active", "services": ["google_ads", "meta_ads"]}
    record = {"id": "acme-site", "client": client}
    run = plan_retainer_run(record, month="2026-06")
    assert "draft_meta_ads" in run.planned_actions
    assert "draft_google_ads" in run.planned_actions
    # Both ads services share one go-live gate — listed once, not twice.
    assert run.blocked_approvals.count("ad_campaign_go_live") == 1
