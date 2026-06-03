"""Tests for the prospect -> preview-site glue (Agency layer).

Offline: site rendering needs no Node, and the Netlify deploy is exercised
through an ``httpx.MockTransport`` — no network, no token.
"""

from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest

from packages.agency.prospect_site import (
    apply_profile,
    build_preview_for_record,
    city_label,
    intake_from_record,
    preview_site_name,
    profile_fields_used,
    render_preview_html,
)
from packages.web.deploy import NetlifyDeployTarget

RECORD = {
    "place_id": "ChIJtest123",
    "display_name": "Joe's Plumbing",
    "genre_id": "plumber",
    "city_id": "oklahoma_city",
    "formatted_address": "100 Main St, Oklahoma City, OK 73119, USA",
    "phone": "+1 405-555-0100",
    "rating": 4.8,
    "user_ratings_total": 57,
    "web_verify_verdict": "none_found",
}


def test_intake_maps_record_fields() -> None:
    intake = intake_from_record(RECORD)
    assert intake.business_name == "Joe's Plumbing"
    assert intake.service_category == "plumbing"
    assert intake.city == "Oklahoma City, OK"
    assert intake.phone == "+1 405-555-0100"
    assert "57" in intake.reviews_note


def test_city_label_overrides() -> None:
    assert city_label("washington_dc") == "Washington, DC"
    assert city_label("oklahoma_city") == "Oklahoma City"


def test_render_has_no_unfilled_tokens_and_real_content() -> None:
    html = render_preview_html(RECORD)
    assert "{{" not in html
    assert "Joe's Plumbing" in html
    assert "+1 405-555-0100" in html  # phone becomes the call CTA
    assert "Oklahoma City" in html


def test_render_guard_rejects_missing_required_field() -> None:
    bad = {**RECORD, "city_id": "", "formatted_address": ""}
    with pytest.raises(ValueError):
        render_preview_html(bad)


SAMPLE_PROFILE = {
    "displayName": {"text": "Joe's Plumbing"},
    "formattedAddress": "100 Main St, Oklahoma City, OK 73119, USA",
    "nationalPhoneNumber": "(405) 555-0100",
    "primaryTypeDisplayName": {"text": "Plumber"},
    "editorialSummary": {"text": "Family-owned plumbing serving OKC since 1998."},
    "regularOpeningHours": {
        "weekdayDescriptions": ["Monday: 8 AM – 5 PM", "Tuesday: 8 AM – 5 PM"]
    },
    "rating": 4.8,
    "userRatingCount": 57,
    "googleMapsUri": "https://maps.google.com/?cid=123",
}


def test_apply_profile_overlays_real_data() -> None:
    ctx = intake_from_record(RECORD).to_site_context()
    out = apply_profile(ctx, SAMPLE_PROFILE, RECORD)
    assert out["HERO_SUBHEAD"] == "Family-owned plumbing serving OKC since 1998."
    assert "8 AM" in out["FAQ_1_A"] and out["FAQ_1_Q"] == "What are your hours?"
    assert "Oklahoma City" in out["FAQ_2_A"]
    assert "4.8" in out["TESTIMONIAL"] and "57" in out["TESTIMONIAL"]


def test_profile_fields_used_reports_contributions() -> None:
    assert set(profile_fields_used(SAMPLE_PROFILE)) == {
        "editorial_summary",
        "primary_type",
        "hours",
        "rating",
    }
    assert profile_fields_used({}) == []


def test_render_with_profile_has_real_data_no_tokens() -> None:
    html = render_preview_html(RECORD, SAMPLE_PROFILE)
    assert "{{" not in html
    assert "Family-owned plumbing serving OKC since 1998." in html
    assert "8 AM" in html


def test_site_name_is_netlify_safe() -> None:
    name = preview_site_name(RECORD)
    assert name == "preview-joes-plumbing-oklahoma-city"
    assert len(name) <= 63
    assert all(c.isalnum() or c == "-" for c in name)


def test_build_local_only_writes_dist(tmp_path: Path) -> None:
    result = build_preview_for_record(RECORD, tmp_path)
    assert result.deployed is False
    assert (result.dist_dir / "index.html").exists()
    assert result.mockup_url == ""


def test_build_draft_deploys_to_shared_site(tmp_path: Path) -> None:
    """Previews are DRAFT deploys to one shared site — never a new site or a
    production deploy per prospect (the Netlify credit/site-count saver)."""
    import json as _json

    from packages.agency.prospect_site import PREVIEW_SITE_NAME

    calls: list[tuple[str, str]] = []
    created_names: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append((request.method, request.url.path))
        if request.method == "GET" and request.url.path.endswith("/sites"):
            return httpx.Response(200, json=[])  # shared site not yet created
        if request.method == "POST" and request.url.path.endswith("/sites"):
            body = _json.loads(request.content)
            created_names.append(body.get("name", ""))
            return httpx.Response(201, json={"id": "site_shared", "name": body.get("name")})
        if request.method == "POST" and "/deploys" in request.url.path:
            # client-review preview => DRAFT deploy (never production)
            body = _json.loads(request.content)
            assert body.get("draft") is True
            return httpx.Response(
                200,
                json={
                    "id": "dep_1",
                    "state": "ready",
                    "deploy_ssl_url": "https://dep_1--bbw-previews.netlify.app",
                    "ssl_url": "https://bbw-previews.netlify.app",
                },
            )
        return httpx.Response(404)

    client = httpx.Client(transport=httpx.MockTransport(handler), base_url="https://api.netlify.com/api/v1")
    target = NetlifyDeployTarget(token="test-token", client=client)

    result = build_preview_for_record(RECORD, tmp_path, target=target)
    assert result.deployed is True
    # mockup_url is the per-deploy permalink, not the site's live URL
    assert result.mockup_url == "https://dep_1--bbw-previews.netlify.app"
    assert result.site_id == "site_shared"
    assert result.deploy_id == "dep_1"
    # exactly the shared site name, kept short for the 63-char draft permalink
    assert created_names == [PREVIEW_SITE_NAME]
    assert len(f"dep_1--{PREVIEW_SITE_NAME}.netlify.app") <= 63
    assert any(m == "POST" and "/deploys" in p for m, p in calls)
