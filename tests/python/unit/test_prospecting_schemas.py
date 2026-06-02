from __future__ import annotations

from packages.prospecting.cohorts import derive_composite_cohort
from packages.schemas.prospect import (
    GoogleSearchCheck,
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
        status=ProspectStatus.HTTP_ENRICHED,
        created_at="2026-06-01T12:00:00+00:00",
        updated_at="2026-06-01T12:00:00+00:00",
    )

    assert ProspectRecord.from_dict(record.to_dict()) == record


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
