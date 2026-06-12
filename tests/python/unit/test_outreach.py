"""Tests for per-prospect outreach copy generation (Agency layer)."""

from __future__ import annotations

from packages.agency.outreach import (
    context_for,
    gap_ref_for,
    parse_snippets,
    recommended_channel,
    render_template,
    sanitize_outreach_copy,
    search_phrase,
    unfilled_placeholders,
)

SNIPPETS_MD = """# Genre Snippets

## auto_repair
- **observed_gap:** "no website where a customer can see your hours."
- **hook:** "{business_name} stood out with {review_count} reviews and no website."

## marketplace_only  (only a booking page)
- **observed_gap:** "your only web presence is a booking-platform page."
- **hook:** "found {business_name} through your booking page."

## generic  (fallback)
- **observed_gap:** "there's no website where a customer can reach you."
- **hook:** "{business_name} stood out in {city}."
"""

AUTO = {
    "place_id": "p1", "display_name": "Motor City Auto", "genre_id": "auto_repair",
    "city_id": "dallas", "phone": "+1 214-555-0100", "user_ratings_total": 836,
    "web_verify_verdict": "none_found", "mockup_url": "https://preview-motor-city-auto-dallas.netlify.app",
}
MKT = {
    "place_id": "p2", "display_name": "Skyline Nails", "genre_id": "nail_salon",
    "city_id": "fort_worth", "phone": "+1 817-555-0100", "user_ratings_total": 1306,
    "web_verify_verdict": "marketplace_only", "mockup_url": "https://preview-skyline-nails-fort-worth.netlify.app",
}


def test_gap_ref_marketplace_beats_genre() -> None:
    # a marketplace_only nail salon uses the marketplace gap, not the salon gap
    assert gap_ref_for(MKT) == "marketplace_only"
    # a none_found auto shop uses its genre gap
    assert gap_ref_for(AUTO) == "auto_repair"
    # unknown genre, none_found -> generic
    assert gap_ref_for({"genre_id": "tutoring", "web_verify_verdict": "none_found"}) == "generic"


def test_parse_snippets_sections() -> None:
    snips = parse_snippets(SNIPPETS_MD)
    assert set(snips) == {"auto_repair", "marketplace_only", "generic"}
    assert "hours" in snips["auto_repair"]["observed_gap"]


def test_parse_snippets_joins_multiline_and_strips_emphasis() -> None:
    md = (
        "## marketplace_only\n"
        '- **observed_gap:** "your only web presence is a booking page, which\n'
        "  works for appointments but isn't really *yours*, a real site\n"
        '  fixes that and still links to your booking."\n'
        '- **hook:** "found {business_name} through your booking page."\n'
    )
    gap = parse_snippets(md)["marketplace_only"]["observed_gap"]
    assert gap.endswith("still links to your booking.")  # full multi-line captured
    assert "*" not in gap  # markdown emphasis stripped
    assert "\n" not in gap


def test_context_resolves_snippet_placeholders() -> None:
    snips = parse_snippets(SNIPPETS_MD)
    ctx = context_for(AUTO, snips)
    # hook in the snippet had {business_name}/{review_count}, so it must be resolved
    assert "Motor City Auto" in ctx.hook
    assert "836" in ctx.hook
    assert "{" not in ctx.hook
    assert ctx.mockup_url.endswith("netlify.app")
    assert ctx.observed_gap_short  # SMS-friendly gap present


def test_render_leaves_only_sender_placeholders() -> None:
    snips = parse_snippets(SNIPPETS_MD)
    ctx = context_for(MKT, snips)
    body = "Hi {business_name} in {city}. {observed_gap_short}. See {mockup_url}. {sender_name}"
    out = render_template(body, ctx)
    assert "Skyline Nails" in out and "Fort Worth" in out
    assert unfilled_placeholders(out) == []  # no {curly} placeholders left
    assert "Kashane Sakhakorn" in out


def test_recommended_channel_is_phone_when_present() -> None:
    assert recommended_channel(AUTO) == "sms_or_call"
    assert recommended_channel({"display_name": "x"}) == "needs_contact"


def test_recommended_channel_prefers_found_contacts() -> None:
    assert recommended_channel({**AUTO, "contact_email": "a@b.com"}) == "email"
    assert recommended_channel({**AUTO, "contact_instagram": "@x"}) == "instagram_dm"
    assert recommended_channel({**AUTO, "contact_facebook": "fb.com/x"}) == "facebook_dm"
    # a confirmed owned site overrides everything → recheck, don't pitch "no website"
    assert recommended_channel(
        {**AUTO, "contact_email": "a@b.com", "contact_owned_website": "x.com"}
    ) == "recheck_has_site"


def test_context_carries_found_contacts() -> None:
    snips = parse_snippets(SNIPPETS_MD)
    ctx = context_for({**MKT, "contact_facebook": "https://fb.com/skyline",
                       "contact_booking_url": "https://fresha.com/x"}, snips)
    assert ctx.facebook == "https://fb.com/skyline"
    assert ctx.booking_url == "https://fresha.com/x"


def test_search_phrase_is_human_for_genre() -> None:
    assert search_phrase({"genre_id": "bakery"}) == "bakeries"
    assert search_phrase({"genre_id": "auto_repair"}) == "auto shops"
    assert search_phrase({"genre_id": "nail_salon"}) == "nail salons"


def test_render_template_strips_forbidden_em_dash() -> None:
    snips = parse_snippets(SNIPPETS_MD)
    ctx = context_for(MKT, snips)
    out = render_template("Hi {business_name} — see {mockup_url}.", ctx)
    assert "—" not in out


def test_sanitize_outreach_copy_removes_em_dash() -> None:
    assert sanitize_outreach_copy("human copy — not machine copy") == "human copy, not machine copy"
