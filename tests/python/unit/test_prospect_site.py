"""Tests for the prospect -> preview-site glue (Agency layer).

Offline: site rendering needs no Node, and the Netlify deploy is exercised
through an ``httpx.MockTransport`` — no network, no token.
"""

from __future__ import annotations

from pathlib import Path

import httpx
import pytest

from packages.agency.prospect_site import (
    apply_profile,
    build_preview_for_record,
    city_label,
    deploy_named_site_dist,
    intake_from_record,
    named_site_name,
    preview_site_name,
    profile_fields_used,
    render_preview_html,
)
from packages.policies.approvals import PolicyViolation
from packages.web.deploy import DeployResult, NetlifyDeployTarget, SiteRef

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
                    "deploy_ssl_url": "https://dep_1--better-business-web-previews.netlify.app",
                    "ssl_url": "https://better-business-web-previews.netlify.app",
                },
            )
        return httpx.Response(404)

    client = httpx.Client(transport=httpx.MockTransport(handler), base_url="https://api.netlify.com/api/v1")
    target = NetlifyDeployTarget(token="test-token", client=client)

    result = build_preview_for_record(RECORD, tmp_path, target=target)
    assert result.deployed is True
    # mockup_url is the per-deploy permalink, not the site's live URL
    assert result.mockup_url == "https://dep_1--better-business-web-previews.netlify.app"
    assert result.site_id == "site_shared"
    assert result.deploy_id == "dep_1"
    # exactly the shared site name, kept short for the 63-char draft permalink
    assert created_names == [PREVIEW_SITE_NAME]
    assert len(f"dep_1--{PREVIEW_SITE_NAME}.netlify.app") <= 63
    assert any(m == "POST" and "/deploys" in p for m, p in calls)


def test_scan_dist_for_scaffold_copy_flags_jargon(tmp_path: Path) -> None:
    from packages.agency.prospect_site import scan_dist_for_scaffold_copy

    dist = tmp_path / "dist-v2"
    dist.mkdir()
    (dist / "index.html").write_text(
        "<h2>Beyond marketplace-only</h2>"
        "<p>This prospect was verified as having marketplace or directory presence. "
        "Included as a category-safe starting point.</p>"
    )
    findings = scan_dist_for_scaffold_copy(dist)
    assert any("category-safe" in f for f in findings)
    assert any("this prospect was verified" in f for f in findings)


def test_scan_dist_clean_copy_has_no_findings(tmp_path: Path) -> None:
    from packages.agency.prospect_site import scan_dist_for_scaffold_copy

    dist = tmp_path / "dist-v2"
    dist.mkdir()
    (dist / "index.html").write_text(
        "<h1>Frank's Auto Service</h1>"
        "<p>Auto repair in Washington, DC. Call us today or get directions.</p>"
    )
    assert scan_dist_for_scaffold_copy(dist) == []


def test_deploy_preview_dist_blocks_scaffold_copy(tmp_path: Path) -> None:
    """The gate fails closed BEFORE touching the deploy target — an unfinished
    page can never reach a prospect's URL."""
    from packages.agency.prospect_site import ScaffoldCopyError, deploy_preview_dist

    dist = tmp_path / "dist-v2"
    dist.mkdir()
    (dist / "index.html").write_text(
        "<h2>A direct page for the basics.</h2>"
        "<p>category-safe service framing</p>"
    )

    class _Boom:
        def ensure_site(self, *a, **k):
            raise AssertionError("must not create a site for scaffold copy")

        def deploy(self, *a, **k):
            raise AssertionError("must not deploy scaffold copy")

    with pytest.raises(ScaffoldCopyError) as excinfo:
        deploy_preview_dist({"place_id": "p1"}, dist, target=_Boom())
    assert "scaffold copy" in str(excinfo.value)


# --------------------------------------------------------------- named site
def test_named_site_name_is_clean_and_deduped() -> None:
    # <business>-<city>, sanitized to a single DNS label.
    assert named_site_name(RECORD) == "joes-plumbing-oklahoma-city"
    name = named_site_name(RECORD)
    assert len(name) <= 63 and all(c.isalnum() or c == "-" for c in name)
    # City already in the business name → not repeated.
    assert (
        named_site_name({"display_name": "Fort Worth Nails", "city_id": "fort_worth"})
        == "fort-worth-nails"
    )


class _RecordingTarget:
    """Minimal DeployTarget double recording ensure_site/deploy calls."""

    def __init__(self) -> None:
        self.ensured: list[str] = []
        self.deploys: list[tuple[str, bool]] = []

    def ensure_site(self, name, *, account=None) -> SiteRef:
        self.ensured.append(name)
        return SiteRef(site_id=f"site_{name}", name=name, url=f"https://{name}.netlify.app")

    def deploy(self, site, dist_dir, *, production=False) -> DeployResult:
        self.deploys.append((site.name, production))
        return DeployResult(
            site=site,
            deploy_id=f"dep_{site.name}",
            url=f"https://{site.name}.netlify.app",
            production=production,
            state="ready",
        )


def _clean_dist(tmp_path: Path) -> Path:
    dist = tmp_path / "dist-v2"
    dist.mkdir()
    (dist / "index.html").write_text("<h1>Joe's Plumbing</h1><p>Plumbing in OKC.</p>")
    return dist


def test_named_site_production_deploy_when_approved(tmp_path: Path) -> None:
    """A clean root-subdomain URL needs a PRODUCTION deploy to a per-business
    named site — and the approval gate must be satisfied."""
    dist = _clean_dist(tmp_path)
    target = _RecordingTarget()

    result = deploy_named_site_dist(RECORD, dist, target=target, approval_granted=True)

    assert target.ensured == ["joes-plumbing-oklahoma-city"]  # named site created
    assert target.deploys == [("joes-plumbing-oklahoma-city", True)]  # PRODUCTION
    assert result.deployed is True
    assert result.mockup_url == "https://joes-plumbing-oklahoma-city.netlify.app"
    assert result.site_id == "site_joes-plumbing-oklahoma-city"
    assert result.deploy_id == "dep_joes-plumbing-oklahoma-city"


def test_named_site_blocks_when_approval_not_granted(tmp_path: Path) -> None:
    """The production gate fails closed BEFORE the deploy target is touched."""
    dist = _clean_dist(tmp_path)

    class _Boom:
        def ensure_site(self, *a, **k):
            raise AssertionError("must not create a site without approval")

        def deploy(self, *a, **k):
            raise AssertionError("must not deploy without approval")

    with pytest.raises(PolicyViolation) as excinfo:
        deploy_named_site_dist(RECORD, dist, target=_Boom(), approval_granted=False)
    assert excinfo.value.code == "deploy_approval_not_granted"


def test_named_site_keeps_scaffold_and_secret_gates(tmp_path: Path) -> None:
    """Scaffold-copy and secret-leak gates still run on the named path, before
    the deploy target or the approval gate."""
    from packages.agency.prospect_site import ScaffoldCopyError
    from packages.web.deploy import SecretLeakError

    target = _RecordingTarget()

    scaffold = tmp_path / "scaffold" / "dist-v2"
    scaffold.mkdir(parents=True)
    (scaffold / "index.html").write_text("<p>category-safe starting point</p>")
    with pytest.raises(ScaffoldCopyError):
        deploy_named_site_dist(RECORD, scaffold, target=target, approval_granted=True)

    leaky = tmp_path / "leaky" / "dist-v2"
    leaky.mkdir(parents=True)
    (leaky / "index.html").write_text("<script>const k='sk_live_abcdEFGH1234'</script>")
    with pytest.raises(SecretLeakError):
        deploy_named_site_dist(RECORD, leaky, target=target, approval_granted=True)

    assert target.ensured == [] and target.deploys == []  # never reached the target
