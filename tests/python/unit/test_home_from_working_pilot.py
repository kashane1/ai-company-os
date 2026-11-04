import pytest

from packages.home_from_working.pilot import build_pilot_contract, validate_pilot_contract


def test_pilot_has_six_matched_pairs_and_only_three_product_treatment():
    pilot = build_pilot_contract()
    assert len(pilot["pairs"]) == 6
    assert len({pair["pair_id"] for pair in pilot["pairs"]}) == 6
    assert {pair["control"]["format"] for pair in pilot["pairs"]} == {"shirt_only"}
    assert {pair["treatment"]["format"] for pair in pilot["pairs"]} == {
        "shirt_hoodie_crewneck"
    }
    validate_pilot_contract(pilot)


def test_pilot_is_not_publication_approval_and_waits_for_live_reconciliation():
    pilot = build_pilot_contract()
    assert pilot["publication"]["approved"] is False
    assert pilot["publication"]["requires_separate_founder_approval"] is True
    assert all(pair["eligibility"] == "pending_live_etsy_reconciliation" for pair in pilot["pairs"])


def test_pilot_is_an_honest_matched_pair_quasi_experiment():
    pilot = build_pilot_contract()
    experiment = pilot["experiment"]
    assert experiment["design"] == "matched_pair_quasi_experiment"
    assert experiment["primary_tested_variable"] == "listing_product_format"
    assert "major_variable" not in experiment
    assert experiment["design_variation_handling"] == "matched_pair_blocking"
    assert "artwork direction" in experiment["residual_confounders"]
    assert "listing age" in experiment["residual_confounders"]
    assert pilot["review_thresholds"] == {
        "aggregate_listing_visits": 100,
        "aggregate_search_impressions": 1000,
        "cadence_days": 14,
        "threshold_rule": "either",
    }


def test_each_pair_records_match_basis_and_pending_comparability_checks():
    pilot = build_pilot_contract()

    for pair in pilot["pairs"]:
        assert pair["match_basis"] == "shared concept theme and buyer intent"
        assert pair["comparability_status"] == "pending_live_reconciliation"
        assert "artwork_direction" in pair["pending_comparability_checks"]
        assert "listing_age" in pair["pending_comparability_checks"]


def test_title_test_is_separate_from_product_format_pilot():
    pilot = build_pilot_contract()
    assert pilot["title_test"]["separate_cohort"] is True
    assert pilot["title_test"]["status"] == "pending_marketplace_insights_and_csv_backup"


def test_validator_rejects_broad_mixed_product_treatment():
    pilot = build_pilot_contract()
    pilot["pairs"][0]["treatment"]["format"] = "twelve_product_mix"
    with pytest.raises(ValueError, match="treatment format"):
        validate_pilot_contract(pilot)


def test_validator_requires_honest_quasi_experiment_metadata():
    pilot = build_pilot_contract()
    del pilot["experiment"]["residual_confounders"]
    with pytest.raises(ValueError, match="residual confounders"):
        validate_pilot_contract(pilot)
