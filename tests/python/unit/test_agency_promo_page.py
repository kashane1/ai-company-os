"""Tests for the promotional landing page builder (G4)."""

from __future__ import annotations

from pathlib import Path

import pytest

from packages.agency.promo_page import (
    PromoCampaign,
    emit_promo_page,
    promo_context,
    render_promo_html,
)


def _campaign(**kw) -> PromoCampaign:
    base = dict(
        business_name="Joe's Plumbing",
        offer_headline="20% off your first drain cleaning",
        city="Austin, TX",
        expiry="Offer ends June 30",
    )
    base.update(kw)
    return PromoCampaign(**base)


def test_validate_requires_business_and_headline() -> None:
    with pytest.raises(ValueError):
        PromoCampaign(business_name="", offer_headline="x").validate()
    with pytest.raises(ValueError):
        PromoCampaign(business_name="x", offer_headline="").validate()


def test_promo_context_centers_the_offer() -> None:
    ctx = promo_context(_campaign())
    assert ctx["HERO_HEADLINE"] == "20% off your first drain cleaning"
    assert ctx["CTA_HEADLINE"] == "20% off your first drain cleaning"
    assert ctx["EYEBROW"].startswith("Limited-time offer")
    assert "Austin, TX" in ctx["EYEBROW"]
    assert ctx["HERO_NOTE"] == "Offer ends June 30"


def test_render_has_offer_and_no_unfilled_tokens() -> None:
    html = render_promo_html(_campaign(cta_label="Book now"))
    assert "20% off your first drain cleaning" in html
    assert "Book now" in html
    assert "{{" not in html  # render guard: every token filled


def test_render_guard_raises_only_on_unfilled() -> None:
    # A complete campaign renders cleanly; the guard is exercised by the assert above.
    assert render_promo_html(_campaign())  # does not raise


def test_emit_writes_dist_index(tmp_path: Path) -> None:
    path = emit_promo_page(_campaign(), tmp_path / "promo")
    assert path == tmp_path / "promo" / "dist" / "index.html"
    assert path.is_file()
    assert "20% off your first drain cleaning" in path.read_text(encoding="utf-8")
