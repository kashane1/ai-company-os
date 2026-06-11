from __future__ import annotations

from packages.prospecting.config import CityConfig, GenreConfig
from packages.prospecting.connectors.fsq_os import (
    FSQ_OS_GENRE_LABELS,
    build_fsq_os_query,
    fsq_os_row_to_candidate,
)


def test_fsq_os_genre_mapping_uses_schema_category_labels() -> None:
    assert "Beauty Salon" in FSQ_OS_GENRE_LABELS["beauty_salon"]
    assert "Nail Salon" in FSQ_OS_GENRE_LABELS["nail_salon"]
    assert "Notary" in FSQ_OS_GENRE_LABELS["notary"]


def test_build_fsq_os_query_filters_locality_region_and_category_labels() -> None:
    query = build_fsq_os_query(
        source_path="/tmp/fsq-os.parquet",
        city=CityConfig(id="fresno", name="Fresno", lat=36.7378, lng=-119.7871),
        genre=GenreConfig(id="notary", label="notary public", text_query_template="{label}"),
        limit=50,
    )

    assert "read_parquet('/tmp/fsq-os.parquet'" in query
    assert "date_closed IS NULL" in query
    assert "Notary" in query
    assert "LIMIT 50" in query


def test_fsq_os_row_to_candidate_handles_contact_and_social_fields() -> None:
    candidate = fsq_os_row_to_candidate(
        {
            "fsq_place_id": "abc123",
            "name": "Tonic Barber",
            "address": "100 Pine St",
            "locality": "Fresno",
            "region": "CA",
            "postcode": "93721",
            "tel": "+1 559-555-0100",
            "website": "",
            "instagram": "tonicbarber",
            "facebook_id": "",
            "fsq_category_labels": ["Business and Professional Services", "Barber"],
        },
        city=CityConfig(id="fresno", name="Fresno", lat=36.7378, lng=-119.7871),
        genre=GenreConfig(id="barber_shop", label="barber shop", text_query_template="{label}"),
    )

    assert candidate.source == "fsq_os"
    assert candidate.source_id == "abc123"
    assert candidate.display_name == "Tonic Barber"
    assert candidate.formatted_address == "100 Pine St, Fresno, CA 93721"
    assert candidate.phone == "+1 559-555-0100"
    assert candidate.website_uri == ""
    assert candidate.social_urls == ["https://instagram.com/tonicbarber"]
