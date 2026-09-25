"""Controlled HomeFromWorking Etsy experiment contract."""

from __future__ import annotations

from copy import deepcopy


_PAIR_INPUTS = (
    ("lightning-sun", "science-humor-20260903/lightning-sun-1", "science-humor-20260903/lightning-sun-2"),
    ("breathing-manually", "science-humor-20260903/breathing-manually-1", "science-humor-20260903/breathing-manually-2"),
    ("snacks-raccoon", "snacks-kittens-20260902/snacks-1", "snacks-kittens-20260902/snacks-2"),
    ("wombat-poop", "mouth-wombat-20260903/wombat-poop-2", "mouth-wombat-20260903/wombat-poop-3"),
    ("boo-sheet", "boo-sheet-20260902/boo-sheet-1", "boo-sheet-20260902/boo-sheet-3"),
    ("venus-day", "witch-venus-steak-20260902/venus-day-1", "witch-venus-steak-20260902/venus-day-2"),
)


def build_pilot_contract() -> dict[str, object]:
    pairs = [
        {
            "pair_id": pair_id,
            "control": {"catalog_key": control, "format": "shirt_only"},
            "treatment": {
                "catalog_key": treatment,
                "format": "shirt_hoodie_crewneck",
            },
            "eligibility": "pending_live_etsy_reconciliation",
            "match_basis": "shared concept theme and buyer intent",
            "comparability_status": "pending_live_reconciliation",
            "pending_comparability_checks": [
                "artwork_direction",
                "listing_age",
                "live_etsy_status",
                "price_and_shipping",
                "title_and_tags",
                "visibility_and_search_baseline",
            ],
        }
        for pair_id, control, treatment in _PAIR_INPUTS
    ]
    return {
        "schema_version": 1,
        "status": "proposed_not_live",
        "experiment": {
            "design": "matched_pair_quasi_experiment",
            "hypothesis": "Compare whether the three-garment format is associated with useful business outcomes while documenting non-format differences between paired listings.",
            "primary_tested_variable": "listing_product_format",
            "design_variation_handling": "matched_pair_blocking",
            "planned_standardization": [
                "title_policy",
                "discount_status",
                "fulfillment_speed",
                "hero_image_standard",
                "observation_window",
            ],
            "residual_confounders": [
                "artwork direction",
                "listing age",
                "historical engagement and listing quality",
                "search placement and audience mix",
                "unmeasured product-specific fulfillment differences",
            ],
        },
        "pairs": pairs,
        "review_thresholds": {
            "aggregate_listing_visits": 100,
            "aggregate_search_impressions": 1000,
            "cadence_days": 14,
            "threshold_rule": "either",
        },
        "metrics": [
            "search_impressions",
            "visits",
            "favorites",
            "orders",
            "revenue",
            "contribution",
            "average_order_value",
            "messages",
            "cancellations",
            "fulfillment_exceptions",
        ],
        "title_test": {
            "separate_cohort": True,
            "status": "pending_marketplace_insights_and_csv_backup",
            "major_variable": "title_policy",
        },
        "publication": {
            "approved": False,
            "requires_separate_founder_approval": True,
            "approval_must_bind_final_revision": True,
        },
    }


def validate_pilot_contract(value: dict[str, object]) -> None:
    experiment = value.get("experiment")
    if not isinstance(experiment, dict):
        raise ValueError("pilot requires experiment metadata")
    if experiment.get("design") != "matched_pair_quasi_experiment":
        raise ValueError("pilot must be a matched-pair quasi-experiment")
    if experiment.get("primary_tested_variable") != "listing_product_format":
        raise ValueError("pilot must name listing format as the primary tested variable")
    if experiment.get("design_variation_handling") != "matched_pair_blocking":
        raise ValueError("pilot must describe matched-pair blocking")
    confounders = experiment.get("residual_confounders")
    if not isinstance(confounders, list) or not {"artwork direction", "listing age"}.issubset(
        confounders
    ):
        raise ValueError("pilot requires residual confounders including artwork direction and listing age")
    pairs = value.get("pairs")
    if not isinstance(pairs, list) or len(pairs) != 6:
        raise ValueError("pilot requires exactly six matched pairs")
    pair_ids: set[str] = set()
    listing_keys: set[str] = set()
    for pair in pairs:
        if not isinstance(pair, dict):
            raise ValueError("each pair must be an object")
        pair_id = str(pair.get("pair_id", ""))
        if not pair_id or pair_id in pair_ids:
            raise ValueError("pair IDs must be present and unique")
        pair_ids.add(pair_id)
        control = pair.get("control")
        treatment = pair.get("treatment")
        if not isinstance(control, dict) or control.get("format") != "shirt_only":
            raise ValueError("control format must be shirt_only")
        if not isinstance(treatment, dict) or treatment.get("format") != "shirt_hoodie_crewneck":
            raise ValueError("treatment format must be shirt_hoodie_crewneck")
        if pair.get("match_basis") != "shared concept theme and buyer intent":
            raise ValueError("each pair requires a stated match basis")
        if pair.get("comparability_status") != "pending_live_reconciliation":
            raise ValueError("each pair must await live reconciliation")
        checks = pair.get("pending_comparability_checks")
        if not isinstance(checks, list) or not {"artwork_direction", "listing_age"}.issubset(checks):
            raise ValueError("each pair requires pending artwork and listing-age comparability checks")
        for arm in (control, treatment):
            key = str(arm.get("catalog_key", ""))
            if not key or key in listing_keys:
                raise ValueError("catalog keys must be present and unique")
            listing_keys.add(key)
    publication = value.get("publication")
    if not isinstance(publication, dict) or publication.get("approved") is not False:
        raise ValueError("pilot contract cannot grant publication approval")


def copy_pilot_contract() -> dict[str, object]:
    """Return a defensive copy for callers that customize derived metadata."""

    return deepcopy(build_pilot_contract())
