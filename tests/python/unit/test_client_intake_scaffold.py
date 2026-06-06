"""Agency layer Phase 4 — client intake + scaffold."""

from __future__ import annotations

from pathlib import Path

import pytest

from packages.agency.catalog import default_catalog
from packages.agency.intake import ClientIntake, render_brief
from packages.agency.templates import render_offer
from packages.web.scaffold import scaffold_site, unfilled_tokens


def _intake() -> ClientIntake:
    return ClientIntake(
        business_name="Joe's Plumbing",
        service_category="plumbing",
        city="Seattle",
        services=["Drain cleaning", "Water heater repair", "Leak detection"],
        phone="206-555-0100",
        hours="Mon-Fri 8-6",
        ideal_customer="Homeowners with urgent repairs",
        competitors=["Acme Plumbing"],
        service_area_cities=["Seattle", "Shoreline"],
        travel_radius_miles=15,
        service_area_notes="No jobs east of Bellevue.",
    )


def test_intake_validates_required_fields() -> None:
    with pytest.raises(ValueError):
        ClientIntake(business_name="", service_category="plumbing", city="Seattle").validate()


def test_brief_renders_intake_fields() -> None:
    brief = render_brief(_intake())
    assert "Joe's Plumbing" in brief
    assert "Drain cleaning" in brief
    assert "Seattle" in brief
    assert "15 miles" in brief
    assert "Shoreline" in brief


def test_site_context_is_localized() -> None:
    ctx = _intake().to_site_context()
    assert "Seattle" in ctx["HERO_SUBHEAD"]
    assert "plumbing" in ctx["HERO_SUBHEAD"].lower()
    assert ctx["PRIMARY_CTA"] == "Call 206-555-0100"


def test_scaffold_renders_with_intake_context(tmp_path: Path) -> None:
    ctx = _intake().to_site_context()
    written = scaffold_site(tmp_path / "site", ctx)
    assert written
    # No unfilled {{TOKENS}} left in the rendered Astro pages.
    for path in written:
        if path.suffix in {".astro", ".html"}:
            assert unfilled_tokens(path.read_text()) == [], path


def test_offer_renders_from_bundle() -> None:
    offer = render_offer(default_catalog(), "package_a", client_name="Joe's Plumbing")
    assert "Package A" in offer
    assert "Professional Website" in offer


def test_intake_round_trips() -> None:
    intake = _intake()
    assert ClientIntake.from_dict(intake.to_dict()).to_dict() == intake.to_dict()


def test_intake_rejects_negative_radius() -> None:
    with pytest.raises(ValueError):
        ClientIntake(
            business_name="Joe's Plumbing",
            service_category="plumbing",
            city="Seattle",
            travel_radius_miles=-1,
        ).validate()


def test_access_block_and_approver_round_trip_and_render() -> None:
    """The access block + named approver (onboarding's #1 back-and-forth lever)
    must persist through to_dict/from_dict and appear in the brief."""
    from packages.agency.intake import ClientIntake, render_brief

    intake = ClientIntake(
        business_name="Joe's Plumbing", service_category="plumbing", city="Austin",
        domain_registrar="GoDaddy", dns_access="delegated to us",
        gbp_access="Manager granted", existing_logins=["wix:admin", "GA4"],
        approver_name="Joe Smith", approver_email="joe@example.com",
    )
    intake.validate()
    assert ClientIntake.from_dict(intake.to_dict()).to_dict() == intake.to_dict()
    brief = render_brief(intake)
    assert "## Access & Approver" in brief
    assert "GoDaddy" in brief and "joe@example.com" in brief


def test_invalid_approver_email_is_rejected() -> None:
    from packages.agency.intake import ClientIntake
    import pytest

    bad = ClientIntake(business_name="x", service_category="y", city="z",
                       approver_email="not-an-email")
    with pytest.raises(ValueError):
        bad.validate()
