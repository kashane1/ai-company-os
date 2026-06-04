from __future__ import annotations

from packages.prospecting.cohorts import derive_composite_cohort, priority_score
from packages.schemas.prospect import (
    GoogleSearchCheck,
    HumanVerified,
    HttpCheckClass,
    MapsWebsiteClass,
    ProspectRecord,
    ProspectStatus,
    ReviewTier,
)


def test_prospect_record_round_trips_required_fields() -> None:
    record = ProspectRecord(
        place_id="places/abc123",
        display_name="Tonic Salon",
        formatted_address="Seattle, WA",
        phone="+1 206-555-0100",
        types=["beauty_salon", "hair_care"],
        city_id="seattle",
        genre_id="beauty_salon",
        grid_cell_id="seattle:beauty_salon",
        maps_website_uri="https://facebook.com/tonic",
        maps_website_host="facebook.com",
        maps_website_class=MapsWebsiteClass.SOCIAL_ONLY,
        rating=4.7,
        user_ratings_total=26,
        http_check_class=HttpCheckClass.REDIRECT_SOCIAL,
        http_final_url="https://facebook.com/tonic",
        http_status=200,
        http_checked_at="2026-06-01T12:00:00+00:00",
        http_skip_reason="",
        google_search_check=GoogleSearchCheck.SKIPPED,
        review_tier=ReviewTier.R0,
        composite_cohort="A_gold",
        priority_score=73.4,
        human_verified=HumanVerified.TRUE,
        human_verified_at="2026-06-01T13:00:00+00:00",
        human_verify_note="operator checked GBP",
        status=ProspectStatus.HTTP_ENRICHED,
        created_at="2026-06-01T12:00:00+00:00",
        updated_at="2026-06-01T12:00:00+00:00",
    )

    assert ProspectRecord.from_dict(record.to_dict()) == record


def test_prospect_record_defaults_human_verification_to_unset() -> None:
    record = ProspectRecord.from_dict(
        {
            "place_id": "places/abc123",
            "display_name": "Tonic Salon",
            "formatted_address": "Seattle, WA",
        }
    )

    assert record.human_verified is HumanVerified.UNSET
    assert record.human_verified_at == ""
    assert record.human_verify_note == ""


def test_cohort_logic_uses_website_signal_not_genre() -> None:
    base = ProspectRecord(
        place_id="places/abc123",
        display_name="Any Local Business",
        formatted_address="Seattle, WA",
        phone="",
        types=["restaurant"],
        city_id="seattle",
        genre_id="restaurant",
        grid_cell_id="seattle:restaurant",
        maps_website_class=MapsWebsiteClass.ABSENT,
        user_ratings_total=40,
        http_check_class=HttpCheckClass.SKIPPED,
    )

    assert derive_composite_cohort(base) == "A_gold"

    low_signal = ProspectRecord.from_dict({**base.to_dict(), "user_ratings_total": 4})
    assert derive_composite_cohort(low_signal) == "D_low_signal"

    # Review-count gates split the sub-25 range: 9-or-fewer is low signal,
    # 10..24 is the plausible-client "potential signal" bucket, and the
    # bucket is gated before web-signal classification (so a no-site shop
    # with 12 reviews still lands here, not in A_gold).
    assert derive_composite_cohort(
        ProspectRecord.from_dict({**base.to_dict(), "user_ratings_total": 9})
    ) == "D_low_signal"
    assert derive_composite_cohort(
        ProspectRecord.from_dict({**base.to_dict(), "user_ratings_total": 10})
    ) == "C_potential_signal"
    assert derive_composite_cohort(
        ProspectRecord.from_dict({**base.to_dict(), "user_ratings_total": 24})
    ) == "C_potential_signal"
    assert derive_composite_cohort(
        ProspectRecord.from_dict({**base.to_dict(), "user_ratings_total": 25})
    ) == "A_gold"

    has_site = ProspectRecord.from_dict(
        {
            **base.to_dict(),
            "maps_website_uri": "https://example.com",
            "maps_website_host": "example.com",
            "maps_website_class": "present",
            "http_check_class": "ok_owned",
            "user_ratings_total": 100,
        }
    )
    assert derive_composite_cohort(has_site) == "E_has_site"

    present_unchecked = ProspectRecord.from_dict(
        {
            **base.to_dict(),
            "maps_website_uri": "https://example.com",
            "maps_website_host": "example.com",
            "maps_website_class": "present",
            "http_check_class": "skipped",
            "http_skip_reason": "present_site_not_in_deterministic_sample",
            "user_ratings_total": 100,
        }
    )
    assert derive_composite_cohort(present_unchecked) == "E_has_site"


def test_priority_score_uses_documented_cohort_weight_times_demand_factor() -> None:
    record = ProspectRecord(
        place_id="places/abc123",
        display_name="Any Local Business",
        formatted_address="Seattle, WA",
        phone="",
        types=[],
        city_id="seattle",
        genre_id="beauty_salon",
        grid_cell_id="seattle:beauty_salon",
        maps_website_class=MapsWebsiteClass.ABSENT,
        user_ratings_total=50,
        http_check_class=HttpCheckClass.SKIPPED,
    )

    assert priority_score(record, "A_gold") == 50.0
    assert priority_score(record, "Z_needs_review") == 20.0
    # Potential-signal bucket (weight 25) sits above low signal, below review.
    assert priority_score(record, "C_potential_signal") == 12.5
    # New secondary bucket weight (85) sits just below A_gold, above B_stale_maps.
    assert priority_score(record, "A2_marketplace_review") == 42.5

    high_demand = ProspectRecord.from_dict({**record.to_dict(), "user_ratings_total": 250})
    assert priority_score(high_demand, "A_gold") == 100.0


def test_marketplace_only_routes_to_secondary_review_bucket() -> None:
    base = ProspectRecord(
        place_id="places/market",
        display_name="Booking-Only Salon",
        formatted_address="Seattle, WA",
        phone="",
        types=["beauty_salon"],
        city_id="seattle",
        genre_id="beauty_salon",
        grid_cell_id="seattle:beauty_salon",
        maps_website_uri="https://www.vagaro.com/somsalon",
        maps_website_host="vagaro.com",
        maps_website_class=MapsWebsiteClass.MARKETPLACE,
        user_ratings_total=120,
        http_check_class=HttpCheckClass.REDIRECT_SOCIAL,
    )
    # Marketplace-only must NOT fold into A_gold, even with enough reviews.
    assert derive_composite_cohort(base) == "A2_marketplace_review"
    # And even if the booking page loads fine (ok_owned), it stays in the bucket.
    loads_ok = ProspectRecord.from_dict(
        {**base.to_dict(), "http_check_class": "ok_owned"}
    )
    assert derive_composite_cohort(loads_ok) == "A2_marketplace_review"
    # Absent/social are still the prime A_gold cohort.
    social = ProspectRecord.from_dict(
        {**base.to_dict(), "maps_website_class": "social_only", "http_check_class": "redirect_social"}
    )
    assert derive_composite_cohort(social) == "A_gold"
