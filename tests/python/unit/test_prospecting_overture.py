from __future__ import annotations

from packages.prospecting.config import CityConfig, GenreConfig
from packages.prospecting.connectors.overture import (
    OVERTURE_GENRE_CATEGORIES,
    build_overture_query,
    overture_row_to_candidate,
)


def test_overture_genre_mapping_uses_current_taxonomy_names() -> None:
    assert "automotive_repair" in OVERTURE_GENRE_CATEGORIES["auto_repair"]
    assert "barber" in OVERTURE_GENRE_CATEGORIES["barber_shop"]
    assert "massage_therapy" in OVERTURE_GENRE_CATEGORIES["massage_therapy"]
    assert "notary_public" in OVERTURE_GENRE_CATEGORIES["notary"]
    assert "restaurant" in OVERTURE_GENRE_CATEGORIES["restaurant"]
    assert "plumbing" in OVERTURE_GENRE_CATEGORIES["plumber"]
    assert "electrician" in OVERTURE_GENRE_CATEGORIES["electrician"]
    assert "pet_groomer" in OVERTURE_GENRE_CATEGORIES["dog_groomer"]
    assert "tutoring_center" in OVERTURE_GENRE_CATEGORIES["tutoring"]


def test_build_overture_query_filters_by_bbox_status_and_categories() -> None:
    query = build_overture_query(
        city=CityConfig(id="fresno", name="Fresno", lat=36.7378, lng=-119.7871),
        genre=GenreConfig(id="nail_salon", label="nail salon", text_query_template="{label}"),
        release="2026-05-20.0",
        limit=50,
    )

    assert "s3://overturemaps-us-west-2/release/2026-05-20.0/theme=places/type=place/*" in query
    assert "operating_status != 'permanently_closed'" in query
    assert "nail_salon" in query
    assert "len(websites)=0" in query
    assert "list_filter(websites" in query
    assert "x -> NOT" in query
    assert "LIMIT 50" in query


def test_overture_row_to_candidate_handles_nested_fields() -> None:
    candidate = overture_row_to_candidate(
        {
            "id": "08f123",
            "names": {"primary": "Tonic Nails"},
            "addresses": [
                {
                    "freeform": "100 Pine St",
                    "locality": "Fresno",
                    "region": "CA",
                    "postcode": "93721",
                }
            ],
            "phones": ["+1 559-555-0100"],
            "websites": [],
            "socials": ["https://instagram.com/tonicnails"],
            "categories": {"primary": "nail_salon"},
            "taxonomy": {"primary": "nail_salon"},
            "confidence": 0.87,
        },
        city=CityConfig(id="fresno", name="Fresno", lat=36.7378, lng=-119.7871),
        genre=GenreConfig(id="nail_salon", label="nail salon", text_query_template="{label}"),
    )

    assert candidate.source == "overture"
    assert candidate.source_id == "08f123"
    assert candidate.display_name == "Tonic Nails"
    assert candidate.formatted_address == "100 Pine St, Fresno, CA 93721"
    assert candidate.phone == "+1 559-555-0100"
    assert candidate.website_uri == ""
    assert candidate.social_urls == ["https://instagram.com/tonicnails"]
