from __future__ import annotations

import json
from pathlib import Path

import pytest

from packages.agency.conversion_personas import load_audience_panel, smallest_panel
from packages.agency.outreach_actions import build_outreach_panel
from packages.agency.outreach_lane import build_client_rows, write_client_status
from packages.agency.outreach_store import KNOWN_VARIANTS, OutreachStore
from packages.agency.teardown_teaser import (
    FindingValidationError,
    TeaserFinding,
    build_teaser_data,
    load_offer,
    prepare_prompts,
    prospect_from_record,
    render_teaser_card_html,
    render_teaser_markdown,
    render_teaser_outreach_markdown,
    resolve_vertical,
    select_cohort,
    validate_findings,
)
from packages.schemas.conversion_lab import PersonaReview


def _owned(place_id: str, name: str, reviews: int, **extra) -> dict:
    base = {
        "place_id": place_id,
        "display_name": name,
        "genre_id": "restaurant",
        "city_id": "austin",
        "user_ratings_total": reviews,
        "web_verify_verdict": "owned_site",
        "web_verify_url": f"https://{place_id}.example.com",
    }
    base.update(extra)
    return base


def _reviews() -> list[PersonaReview]:
    return [
        PersonaReview(
            persona_id="urgent-problem-solver",
            likely_action="I would leave and call a competitor.",
            objections=["There is no phone number visible above the fold"],
            trust_gaps=["No recent reviews are shown"],
        ),
        PersonaReview(
            persona_id="skeptical-researcher",
            likely_action="I would hesitate.",
            objections=["I cannot tell what they actually specialize in"],
        ),
    ]


def _good_findings() -> list[TeaserFinding]:
    return [
        TeaserFinding(
            "No visible phone above the fold",
            "There is no phone number visible above the fold",
            "urgent-problem-solver",
            "Add a tap-to-call button in the header",
        ),
        TeaserFinding(
            "Unclear specialty",
            "I cannot tell what they actually specialize in",
            "skeptical-researcher",
        ),
    ]


# ----------------------------------------------------------------- selection
def test_resolve_vertical_maps_genre_directly():
    assert resolve_vertical("auto_repair") == "auto_repair"
    assert resolve_vertical("definitely_not_a_genre") is None
    assert resolve_vertical("") is None


def test_select_cohort_filters_and_orders_by_reviews():
    records = [
        _owned("p1", "Low", 10),
        _owned("p2", "High", 9000),
        {"place_id": "p3", "display_name": "NoSite", "web_verify_verdict": "none_found"},
        _owned("p4", "NoUrl", 500, web_verify_url="", contact_owned_website=""),
        _owned("p5", "NoVertical", 800, genre_id="quantum_widgets"),
    ]
    cohort = select_cohort(records, limit=10, min_reviews=1)
    names = [p.business_name for p in cohort]
    assert names == ["High", "Low"]  # site+vertical only, review-count desc


def test_prospect_from_record_rejects_non_owned():
    assert prospect_from_record({"web_verify_verdict": "none_found"}) is None


def test_select_cohort_respects_limit_and_min_reviews():
    records = [_owned(f"p{i}", f"B{i}", i * 100) for i in range(1, 6)]
    assert [p.review_count for p in select_cohort(records, limit=2)] == [500, 400]
    assert all(p.review_count >= 300 for p in select_cohort(records, min_reviews=300))


def test_select_cohort_dedupes_by_site_url_keeping_highest_reviews():
    # Two records share one homepage (modulo scheme/www/trailing slash); only the
    # higher-review one should survive, plus the one distinct site.
    records = [
        _owned("dup_lo", "Chain Low", 200, web_verify_url="http://www.shared.com/"),
        _owned("dup_hi", "Chain High", 5000, web_verify_url="https://shared.com"),
        _owned("solo", "Other", 1000, web_verify_url="https://other.com"),
    ]
    cohort = select_cohort(records, min_reviews=1)
    names = [p.business_name for p in cohort]
    assert names == ["Chain High", "Other"]  # dup collapsed to the 5000-review record
    assert sorted(p.site_url for p in cohort) == ["https://other.com", "https://shared.com"]


# ------------------------------------------------------------------- prompts
def test_prepare_prompts_uses_smallest_panel():
    prospect = select_cohort([_owned("p1", "Casa", 6000)])[0]
    payload, prompts_md, persona_ids = prepare_prompts(prospect, "Call us. Open 9-5.", panel_size=3)
    assert len(persona_ids) == 3
    assert prompts_md.count("## Prompt") == 3
    assert payload.vertical == "restaurant"
    panel = smallest_panel(load_audience_panel("restaurant"), n=3)
    assert persona_ids == [p.persona_id for p in panel.personas]


# ------------------------------------------------------------------ guardrail
def test_validate_findings_accepts_grounded():
    validate_findings(_good_findings(), _reviews())  # no raise


def test_validate_findings_rejects_invented_quote():
    bad = [TeaserFinding("Made up", "Your prices are too high", "urgent-problem-solver")]
    with pytest.raises(FindingValidationError):
        validate_findings(bad, _reviews())


def test_validate_findings_rejects_wrong_persona_attribution():
    # The quote is real, but it belongs to urgent-problem-solver, not skeptical.
    bad = [TeaserFinding("Misattributed", "No recent reviews are shown", "skeptical-researcher")]
    with pytest.raises(FindingValidationError):
        validate_findings(bad, _reviews())


def test_validate_findings_rejects_unknown_persona():
    bad = [TeaserFinding("Ghost", "anything", "persona-not-in-panel")]
    with pytest.raises(FindingValidationError):
        validate_findings(bad, _reviews())


def test_validate_findings_is_whitespace_insensitive():
    finding = [
        TeaserFinding(
            "ok", "There is   no phone number\nvisible above the fold", "urgent-problem-solver"
        )
    ]
    validate_findings(finding, _reviews())  # normalized match, no raise


# ------------------------------------------------------------------ artifacts
def test_teaser_markdown_has_methodology_and_audit_cta_no_revenue_claims():
    prospect = select_cohort([_owned("p1", "Casa", 6000)])[0]
    md = render_teaser_markdown(prospect, _good_findings(), load_offer())
    assert "synthetic" in md.lower()  # methodology disclosed
    assert "$250" in md  # audit CTA
    assert "no rebuild" in md.lower() or "advisory" in md.lower()
    for banned in ("guarantee", "revenue", "% more", "double your"):
        assert banned not in md.lower()


def test_teaser_card_html_references_homepage_image():
    prospect = select_cohort([_owned("p1", "Casa", 6000)])[0]
    card = render_teaser_card_html(prospect, _good_findings(), homepage_image="teaser/homepage.png")
    assert "teaser/homepage.png" in card and "Casa" in card


def test_teaser_data_sidecar_records_provenance():
    prospect = select_cohort([_owned("p1", "Casa", 6000)])[0]
    data = build_teaser_data(prospect, _good_findings(), load_offer(), persona_ids=["a", "b"])
    assert data["findings"][0]["persona_id"] == "urgent-problem-solver"
    assert data["offer"]["audit_fee"] == 250
    assert "synthetic" in data["methodology"].lower()


def test_outreach_draft_pitches_paid_audit():
    prospect = select_cohort([_owned("p1", "Casa", 6000)])[0]
    draft = render_teaser_outreach_markdown(prospect, _good_findings(), load_offer())
    assert "Conversion Audit" in draft and "$250" in draft
    assert "preview" not in draft.lower()  # not the demo-link pitch


# ---------------------------------------------------------------- dashboard
def test_teaser_variant_registered():
    assert "teaser" in KNOWN_VARIANTS


def test_teaser_row_surfaces_in_dashboard_with_audit_copy(tmp_path: Path):
    pid = "TEASER_DASH_1"
    lane = tmp_path / "state" / "prospects" / "outreach-lane"
    lane.mkdir(parents=True)
    site_dir = tmp_path / "state" / "prospects" / "sites" / pid
    site_dir.mkdir(parents=True)
    (site_dir / "outreach-teaser.md").write_text("# draft")
    (site_dir / "teaser.json").write_text(
        json.dumps(
            {
                "place_id": pid,
                "business_name": "Casa",
                "city": "Austin",
                "site_url": "https://casa.example.com",
                "findings": [
                    {"title": "No visible phone", "evidence_quote": "x", "persona_id": "u"}
                ],
                "offer": {
                    "snapshot_name": "Conversion Snapshot",
                    "snapshot_fee": 100,
                    "audit_name": "Conversion Audit",
                    "audit_fee": 250,
                },
            }
        )
    )
    record = _owned(pid, "Casa", 6000, phone="512-555-1212", contact_email="hi@casa.com")
    record["teaser_lane"] = True

    rows = build_client_rows([record], repo_root=tmp_path, include_undeployed=True)
    assert len(rows) == 1 and rows[0].lane == "teaser"
    assert rows[0].status.value == "ready_to_send"
    assert rows[0].draft_path.endswith("outreach-teaser.md")
    write_client_status(rows, lane_root=lane)

    store = OutreachStore(sqlite_path=tmp_path / "store.sqlite3")
    view = build_outreach_panel(store=store, lane_root=lane)
    assert len(view.rows) == 1
    row = view.rows[0]
    assert "teaser" in row.facts.tags
    assert any(f.key == "teaser" and f.count == 1 for f in view.facets)
    email = next(b for b in row.buttons if b.channel == "email")
    assert "Conversion Audit" in email.copy and "$250" in email.copy
    assert "preview" not in email.copy.lower()


def test_non_teaser_owned_site_record_excluded_until_flagged(tmp_path: Path):
    record = _owned("p_unflagged", "Casa", 6000)  # owned_site but not teaser_lane
    rows = build_client_rows([record], repo_root=tmp_path, include_undeployed=True)
    assert rows == []  # not A_gold and not flagged → not in the ledger
