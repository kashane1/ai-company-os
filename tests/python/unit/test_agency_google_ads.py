"""Tests for the Google Ads draft (G8) + the budget-cap go-live gate ([D7])."""

from __future__ import annotations

from pathlib import Path

import pytest

from packages.agency.google_ads import draft_google_ads, emit_ads_draft
from packages.agency.intake import ClientIntake
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


def test_draft_builds_ad_groups_per_service() -> None:
    draft = draft_google_ads(_intake(), daily_budget=25, monthly_budget=600)
    assert [g.name for g in draft.ad_groups] == ["Drain Cleaning", "Water Heaters"]
    assert any("drain cleaning austin, tx" in k.lower() for k in draft.ad_groups[0].keywords)
    assert draft.geo_targets == ("Austin", "Round Rock")
    assert "free" in draft.negative_keywords


def test_rsa_limits_respected() -> None:
    draft = draft_google_ads(
        _intake(business_name="A Very Very Long Business Name That Exceeds Limits")
    )
    assert all(len(h) <= 30 for h in draft.headlines)
    assert all(len(d) <= 90 for d in draft.descriptions)


def test_markdown_has_sections_and_budget() -> None:
    md = draft_google_ads(_intake(), daily_budget=25, monthly_budget=600).to_markdown()
    for section in ("Geo targeting", "Ad groups", "Negative keywords", "Responsive Search"):
        assert section in md
    assert "$25/day · $600/mo" in md
    assert "[D7]" in md


def test_markdown_can_include_conversion_lab_preflight() -> None:
    md = draft_google_ads(
        _intake(),
        daily_budget=25,
        monthly_budget=600,
        preflight_summary="Lead with emergency trust and price clarity.",
        conversion_lab_report_path="state/clients/joes/conversion_lab/run/REPORT.md",
    ).to_markdown()

    assert "## Conversion Lab Preflight" in md
    assert "Lead with emergency trust and price clarity." in md
    assert "state/clients/joes/conversion_lab/run/REPORT.md" in md


def test_emit_writes_ads_md(tmp_path: Path) -> None:
    path = emit_ads_draft(_intake(), tmp_path / "joes-site", daily_budget=25, monthly_budget=600)
    assert path == tmp_path / "joes-site" / "ADS.md"
    assert "Google Ads Draft — Joe's Plumbing" in path.read_text(encoding="utf-8")


# --- the [D7] go-live gate ---

def test_go_live_refused_without_budget_cap() -> None:
    for daily, monthly in [(None, None), (0, 600), (25, 0), (-5, 600)]:
        with pytest.raises(PolicyViolation) as exc:
            assert_ad_campaign_go_live(
                "appr-1", product_id="joes-plumbing-site",
                daily_budget=daily, monthly_budget=monthly,
            )
        assert exc.value.code == "ad_budget_cap_missing"


def test_go_live_with_budget_but_no_approval_is_refused(isolated_repo_root) -> None:
    from packages.db.approval_store import ApprovalStore

    with pytest.raises(PolicyViolation) as exc:
        assert_ad_campaign_go_live(
            "missing", product_id="joes-plumbing-site",
            daily_budget=25, monthly_budget=600, store=ApprovalStore(),
        )
    assert exc.value.code == "retainer_approval_not_granted"
