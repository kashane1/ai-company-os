"""Tests for the owned-site contact harvester (fix F1).

Everything here is network-free: extraction runs on fixture HTML, and the
orchestrator :func:`harvest_site` is driven by a FAKE injected fetcher. The
overlay test proves the end-to-end payoff — a harvested ``contact_email``
override flips a teaser-lane row's email button from disabled to enabled.
"""

from __future__ import annotations

import json
from pathlib import Path

from packages.agency import outreach_actions as actions
from packages.agency.outreach_lane import refresh_client_status
from packages.agency.outreach_store import ALLOWED_OVERRIDE_FIELDS, OutreachStore
from packages.agency.teardown_teaser import TeaserProspect
from packages.prospecting.site_contact_harvest import (
    HarvestResult,
    discover_contact_links,
    extract_emails,
    extract_socials,
    harvest_site,
    has_contact_form,
)


# --------------------------------------------------------------------- emails
def test_extract_emails_mailto_and_plain_deduped_and_lowered() -> None:
    html = """
    <a href="mailto:Hello@AcmePlumbing.com?subject=Hi">email us</a>
    <p>Reach us at Hello@AcmePlumbing.com or sales@acmeplumbing.com.</p>
    """
    emails = extract_emails(html)
    # mailto target first (query stripped), plain address second, deduped+lowered.
    assert emails == ["hello@acmeplumbing.com", "sales@acmeplumbing.com"]


def test_extract_emails_filters_junk_and_image_filenames() -> None:
    html = """
    info@example.com test@test.com hi@yourdomain.com
    a1b2c3@sentry.io owner@123.wixpress.com store@shopify.com
    no-reply@acme.com noreply@acme.com
    <img src="logo.png@2x"> hero.jpg@3x banner.svg@acme.com
    real@acmeplumbing.com
    """
    emails = extract_emails(html)
    assert emails == ["real@acmeplumbing.com"]


# -------------------------------------------------------------------- socials
def test_extract_socials_canonicalizes_handles() -> None:
    html = """
    <a href="https://www.instagram.com/AcmePlumbing/">ig</a>
    <a href="https://facebook.com/AcmePlumbingCo">fb</a>
    """
    socials = extract_socials(html)
    assert socials == {"instagram": "acmeplumbing", "facebook": "acmeplumbingco"}


def test_extract_socials_skips_share_and_intent_urls() -> None:
    html = """
    <a href="https://www.facebook.com/sharer/sharer.php?u=acme.com">share</a>
    <a href="https://www.facebook.com/plugins/page.php?href=x">widget</a>
    <a href="https://instagram.com/explore/tags/plumbing">tag</a>
    <a href="https://twitter.com/intent/tweet?text=hi">tweet</a>
    """
    socials = extract_socials(html)
    assert socials == {"instagram": "", "facebook": ""}


def test_extract_socials_real_profile_wins_over_share_link() -> None:
    html = """
    <a href="https://facebook.com/sharer/sharer.php?u=acme">share</a>
    <a href="https://facebook.com/AcmePlumbingCo">profile</a>
    """
    assert extract_socials(html)["facebook"] == "acmeplumbingco"


# ----------------------------------------------------------------- contact form
def test_has_contact_form_detects_email_field() -> None:
    assert has_contact_form('<form><input type="email" name="addr"></form>')
    assert has_contact_form('<form><input name="your-email"><button>Go</button></form>')
    assert has_contact_form("<form><textarea name='msg'></textarea></form>")


def test_has_contact_form_false_for_plain_form() -> None:
    assert not has_contact_form('<form><input type="text" name="zip"></form>')
    assert not has_contact_form("<p>no form here</p>")


# ---------------------------------------------------------------- link discovery
def test_discover_contact_links_same_domain_only_capped_at_two() -> None:
    html = """
    <a href="/contact">Contact us</a>
    <a href="/about-us">About</a>
    <a href="/services">Services</a>
    <a href="https://other.com/contact">Off-site contact</a>
    <a href="https://acme.com/get-in-touch">Reach out</a>
    """
    links = discover_contact_links(html, "https://acme.com")
    assert links == ["https://acme.com/contact", "https://acme.com/about-us"]


# ------------------------------------------------------------------ harvest_site
class _FakeFetcher:
    """A network-free fetcher: serves canned HTML per URL, records the calls."""

    def __init__(self, pages: dict[str, str]) -> None:
        self.pages = pages
        self.calls: list[str] = []

    def __call__(self, url: str) -> str | None:
        self.calls.append(url)
        return self.pages.get(url)


def _prospect(site_url: str = "https://acmeplumbing.com") -> TeaserProspect:
    return TeaserProspect(
        place_id="places/abc",
        business_name="Acme Plumbing",
        genre_id="plumber",
        vertical="plumber",
        city_id="los_angeles",
        city="Los Angeles",
        site_url=site_url,
        review_count=42,
    )


def test_harvest_site_walks_homepage_and_discovered_contact_page() -> None:
    home = """
    <html><body>
      <a href="/contact">Contact</a>
      <a href="https://instagram.com/acmeplumbing">ig</a>
    </body></html>
    """
    contact = """
    <html><body>
      <a href="mailto:hello@acmeplumbing.com">email</a>
      <form><textarea name="message"></textarea></form>
    </body></html>
    """
    fetcher = _FakeFetcher(
        {
            "https://acmeplumbing.com": home,
            "https://acmeplumbing.com/contact": contact,
        }
    )
    result = harvest_site(_prospect(), fetcher=fetcher)

    assert fetcher.calls == [
        "https://acmeplumbing.com",
        "https://acmeplumbing.com/contact",
    ]
    assert result.best_email == "hello@acmeplumbing.com"
    assert result.instagram == "acmeplumbing"
    assert result.has_form is True
    assert result.pages_fetched == 2


def test_harvest_site_captured_home_does_no_fetch() -> None:
    captured = "Call or email hello@acmeplumbing.com -- find us on instagram @acmeplumbing"
    fetcher = _FakeFetcher({"https://acmeplumbing.com": "<should not be fetched>"})

    result = harvest_site(_prospect(), fetcher=fetcher, captured_home=captured)

    assert fetcher.calls == []  # ZERO network on the captured path
    assert result.best_email == "hello@acmeplumbing.com"
    assert result.pages_fetched == 0


def test_harvest_site_no_url_returns_empty() -> None:
    fetcher = _FakeFetcher({})
    result = harvest_site(_prospect(site_url=""), fetcher=fetcher)
    assert fetcher.calls == []
    assert result.has_any() is False


# --------------------------------------------------------------- best_overrides
def test_best_overrides_maps_only_to_allowed_fields() -> None:
    result = HarvestResult(
        emails=["a@acme.com", "b@acme.com"],
        instagram="acme",
        facebook="acmeco",
        has_form=True,
    )
    overrides = result.best_overrides()
    assert overrides == {
        "contact_email": "a@acme.com",  # best (first) email only
        "contact_instagram": "acme",
        "contact_facebook": "acmeco",
    }
    # Every override key is a permitted store field; the form is never an override.
    assert set(overrides).issubset(set(ALLOWED_OVERRIDE_FIELDS))
    assert "has_form" not in overrides
    assert not any("form" in key for key in overrides)


def test_best_overrides_empty_when_only_form() -> None:
    assert HarvestResult(has_form=True).best_overrides() == {}


# ------------------------------------------------- teaser overlay (end-to-end)
def _teaser_record(place_id: str) -> dict[str, object]:
    """An owned-site prospect flagged into the teaser lane, no digital contact."""
    return {
        "place_id": place_id,
        "display_name": "Acme Plumbing",
        "city_id": "los_angeles",
        "genre_id": "plumber",
        "user_ratings_total": 42,
        "teaser_lane": True,
        "web_verify_verdict": "owned_site",
        "phone": "",
        "contact_email": "",
    }


def test_harvested_email_override_enables_teaser_row_email_button(tmp_path: Path) -> None:
    records_root = tmp_path / "records"
    lane_root = tmp_path / "lane"
    records_root.mkdir()
    (records_root / "acme.json").write_text(json.dumps(_teaser_record("places/acme")))
    refresh_client_status(records_root=records_root, lane_root=lane_root)
    store = OutreachStore(sqlite_path=tmp_path / "outreach.sqlite3")

    # Before the harvest: a teaser row with no email -> email button disabled.
    view = actions.build_outreach_panel(store=store, lane_root=lane_root)
    row = next(r for r in view.rows if r.place_id == "places/acme")
    assert row.facts.tags.count("teaser") == 1  # confirm it really is the teaser lane
    email_before = next(b for b in row.buttons if b.channel == "email")
    assert email_before.enabled is False

    # Harvest writes the discovered email as an override (what the CLI does).
    store.set_override("places/acme", "contact_email", "hello@acmeplumbing.com")

    # After: the same teaser row's email button is enabled off the override overlay.
    view2 = actions.build_outreach_panel(store=store, lane_root=lane_root)
    row2 = next(r for r in view2.rows if r.place_id == "places/acme")
    email_after = next(b for b in row2.buttons if b.channel == "email")
    assert email_after.enabled is True
    assert email_after.contact_value == "hello@acmeplumbing.com"
    assert "hello%40acmeplumbing.com" in email_after.url
