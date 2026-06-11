from __future__ import annotations

from packages.prospecting.identity import IdentityIndex, ProspectCandidate, normalize_phone
from packages.schemas.prospect import MapsWebsiteClass, ProspectRecord


def _record() -> ProspectRecord:
    return ProspectRecord(
        place_id="places/abc123",
        display_name="Tonic Salon LLC",
        formatted_address="1420 Pine St, Seattle, WA 98101",
        phone="+1 (206) 555-0100",
        types=["beauty_salon"],
        city_id="seattle",
        genre_id="beauty_salon",
        grid_cell_id="seattle:beauty_salon",
        maps_website_uri="https://www.instagram.com/tonicsalon/",
        maps_website_host="instagram.com",
        maps_website_class=MapsWebsiteClass.SOCIAL_ONLY,
        user_ratings_total=42,
    )


def test_normalize_phone_extracts_us_numbers() -> None:
    assert normalize_phone("+1 (206) 555-0100") == "12065550100"
    assert normalize_phone("206.555.0100") == "12065550100"
    assert normalize_phone("") == ""


def test_identity_index_matches_candidate_by_phone_before_name_address() -> None:
    index = IdentityIndex.from_records([_record()])

    match = index.match(
        ProspectCandidate(
            source="overture",
            source_id="overture:1",
            display_name="Different Trade Name",
            formatted_address="999 Other Ave, Seattle, WA",
            phone="206-555-0100",
            city_id="seattle",
            genre_id="beauty_salon",
        )
    )

    assert match is not None
    assert match.place_id == "places/abc123"
    assert match.match_type == "phone"
    assert match.confidence == 0.98


def test_identity_index_matches_candidate_by_normalized_name_and_address() -> None:
    index = IdentityIndex.from_records([_record()])

    match = index.match(
        ProspectCandidate(
            source="fsq_os",
            source_id="fsq:1",
            display_name="Tonic Salon",
            formatted_address="1420 Pine Street, Seattle, WA 98101",
            phone="",
            city_id="seattle",
            genre_id="beauty_salon",
        )
    )

    assert match is not None
    assert match.place_id == "places/abc123"
    assert match.match_type == "name_address"
    assert match.confidence == 0.9


def test_identity_index_returns_none_for_new_candidate() -> None:
    index = IdentityIndex.from_records([_record()])

    assert (
        index.match(
            ProspectCandidate(
                source="osm",
                source_id="node/1",
                display_name="Fresh Bakery",
                formatted_address="500 Market St, Seattle, WA",
                phone="+1 206-555-0199",
                city_id="seattle",
                genre_id="bakery",
            )
        )
        is None
    )

