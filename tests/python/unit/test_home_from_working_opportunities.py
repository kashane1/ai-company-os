import io

import pytest

from packages.home_from_working.opportunities import (
    HardGates,
    classify_listing,
    marketplace_factor_scores,
    parse_marketplace_insights,
    score_candidate,
)


def test_marketplace_insights_import_requires_expected_columns():
    with pytest.raises(ValueError, match="missing columns"):
        parse_marketplace_insights(io.StringIO("query,searches_30d\nremote work shirt,10\n"))


def test_marketplace_insights_requires_observation_and_visual_context_columns():
    old_schema = io.StringIO(
        "query,searches_30d,competing_listings,related_queries,trend,buyer_occasion,notes\n"
        "remote work shirt,10,100,related,rising,self purchase,manual\n"
    )

    with pytest.raises(ValueError, match="observed_at"):
        parse_marketplace_insights(old_schema)


def test_marketplace_insights_import_preserves_unknown_numbers():
    text = io.StringIO(
        "query,observed_at,searches_30d,competing_listings,related_queries,trend,dominant_visual_pattern,price_band_usd,buyer_occasion,notes\n"
        "remote work shirt,,,,,,,,self purchase,run manually in Etsy\n"
    )
    [row] = parse_marketplace_insights(text)
    assert row.query == "remote work shirt"
    assert row.searches_30d is None
    assert row.competing_listings is None


def test_marketplace_evidence_maps_specific_query_and_scores_observed_values():
    rows = parse_marketplace_insights(
        io.StringIO(
            "query,observed_at,searches_30d,competing_listings,related_queries,trend,dominant_visual_pattern,price_band_usd,buyer_occasion,notes\n"
            "breathing manually shirt,2026-09-06,1000,10000,manual breathing tee;science joke,rising,bold text,$20-$30,self purchase,observed in Etsy\n"
            "funny work from home shirt,2026-09-06,50,50000,,flat,text only,$15-$25,coworker gift,observed in Etsy\n"
        )
    )

    result = marketplace_factor_scores(
        rows,
        candidate_text="You Are Now Breathing Manually",
        section="workday_absurdity",
    )

    assert result["matched_queries"] == ["breathing manually shirt"]
    assert result["buyer_demand"] == pytest.approx(85.0)
    assert result["competitive_room"] == pytest.approx(25.0)
    assert result["evidence_complete"] is True


def test_marketplace_evidence_stays_unknown_when_observed_values_are_blank():
    rows = parse_marketplace_insights(
        io.StringIO(
            "query,observed_at,searches_30d,competing_listings,related_queries,trend,dominant_visual_pattern,price_band_usd,buyer_occasion,notes\n"
            "encouragement shirt,,,,,,,,self purchase,not collected yet\n"
        )
    )

    result = marketplace_factor_scores(
        rows,
        candidate_text="Hold On Tight",
        section="tiny_morale_boosts",
    )

    assert result["matched_queries"] == ["encouragement shirt"]
    assert result["buyer_demand"] is None
    assert result["competitive_room"] is None
    assert result["evidence_complete"] is False


def test_marketplace_evidence_does_not_match_partial_words_or_phrases():
    rows = parse_marketplace_insights(
        io.StringIO(
            "query,observed_at,searches_30d,competing_listings,related_queries,trend,dominant_visual_pattern,price_band_usd,buyer_occasion,notes\n"
            "funny cat shirt,2026-09-06,3200,208400,,falling,text,$15-$25,gift,manual\n"
            "halloween work shirt,2026-09-06,157,17200,,falling,text,$15-$25,gift,manual\n"
        )
    )

    caterpillar = marketplace_factor_scores(
        rows,
        candidate_text="Turn Over a New Leaf Retro Caterpillar",
        section="tiny_morale_boosts",
    )
    storybook = marketplace_factor_scores(
        rows,
        candidate_text="Go With The Flow Storybook Otter",
        section="tiny_morale_boosts",
    )

    assert caterpillar["matched_queries"] == []
    assert storybook["matched_queries"] == []


def test_marketplace_evidence_requires_all_matched_queries_and_reports_errors():
    rows = parse_marketplace_insights(
        io.StringIO(
            "query,observed_at,searches_30d,competing_listings,related_queries,trend,dominant_visual_pattern,price_band_usd,buyer_occasion,notes\n"
            "motivational animal shirt,2026-09-06,,,,flat,,,,Etsy displayed Error\n"
            "encouragement shirt,2026-09-06,56,51100,,falling,text,$15-$25,gift,manual\n"
        )
    )

    result = marketplace_factor_scores(
        rows,
        candidate_text="Hold On Tight Koala",
        section="tiny_morale_boosts",
    )

    assert result["matched_queries"] == ["motivational animal shirt", "encouragement shirt"]
    assert result["missing_metric_queries"] == ["motivational animal shirt"]
    assert result["errored_queries"] == ["motivational animal shirt"]
    assert result["evidence_complete"] is False


@pytest.mark.parametrize(
    ("title", "key", "primary", "secondary"),
    [
        ("You Are Now Breathing Manually Heavy Cotton T-Shirt", "science/breathing-manually-1", "workday_absurdity", None),
        ("Hold On Tight Koala T-Shirt", "animal/hold-on-tight-1", "tiny_morale_boosts", None),
        ("Wombat Poop Science Fact T-Shirt", "facts/wombat-poop-2", "useful_useless_facts", None),
        ("Resting Witch Face Halloween T-Shirt", "seasonal/resting-witch-face-2", "seasonal_work_breaks", "workday_absurdity"),
        ("Chicken Fried This Steak T-Shirt", "witch-venus-steak-20260902/chicken-fried-steak-1", "exception", None),
    ],
)
def test_four_section_classification_has_explicit_exception(title, key, primary, secondary):
    result = classify_listing(title=title, key=key)
    assert result.primary == primary
    assert result.secondary == secondary
    assert result.rationale
    assert result.confidence in {"high", "medium", "low"}


def test_hard_gate_failure_cannot_be_outscored():
    result = score_candidate(
        candidate_id="unsafe",
        gates=HardGates(ip=False, production=True, economics=True, policy=True),
        factor_scores={
            "buyer_demand": 100,
            "competitive_room": 100,
            "buyer_clarity": 100,
            "brand_fit": 100,
            "visual_differentiation": 100,
            "product_fit": 100,
        },
    )
    assert result.eligible is False
    assert result.status == "failed_hard_gate"
    assert result.weighted_score is None


def test_unknown_hard_gate_blocks_candidate_until_evidence_exists():
    result = score_candidate(
        candidate_id="unknown",
        gates=HardGates(ip=None, production=True, economics=True, policy=True),
        factor_scores={
            "buyer_demand": 100,
            "competitive_room": 100,
            "buyer_clarity": 100,
            "brand_fit": 100,
            "visual_differentiation": 100,
            "product_fit": 100,
        },
    )
    assert result.eligible is False
    assert result.status == "blocked_unknown_hard_gate"
    assert result.weighted_score is None
    assert result.unknown_gates == ("ip",)


def test_missing_evidence_is_provisional_and_reports_coverage():
    result = score_candidate(
        candidate_id="candidate",
        gates=HardGates(ip=True, production=True, economics=True, policy=True),
        factor_scores={
            "buyer_demand": None,
            "competitive_room": None,
            "buyer_clarity": 80,
            "brand_fit": 90,
            "visual_differentiation": 70,
            "product_fit": 60,
        },
    )
    assert result.eligible is True
    assert result.status == "provisional_missing_evidence"
    assert result.weighted_score is None
    assert result.available_points == pytest.approx(42.5)
    assert result.evidence_coverage == pytest.approx(0.55)


def test_complete_score_is_stable_and_bounded():
    scores = {name: 80 for name in (
        "buyer_demand", "competitive_room", "buyer_clarity", "brand_fit",
        "visual_differentiation", "product_fit",
    )}
    result = score_candidate("complete", HardGates(True, True, True, True), scores)
    assert result.status == "scored"
    assert result.weighted_score == pytest.approx(80.0)
    assert result.evidence_coverage == 1.0
