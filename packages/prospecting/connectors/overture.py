"""Overture Maps Places connector for prospect source collection."""

from __future__ import annotations

import math
from typing import Any

from packages.prospecting.config import CityConfig, GenreConfig
from packages.prospecting.identity import ProspectCandidate

DEFAULT_OVERTURE_RELEASE = "2026-05-20.0"
OVERTURE_S3_ROOT = "s3://overturemaps-us-west-2/release"

OVERTURE_GENRE_CATEGORIES: dict[str, tuple[str, ...]] = {
    "auto_repair": (
        "automotive_repair",
        "automotive_services_and_repair",
        "auto_body_shop",
        "tire_dealer_and_repair",
        "truck_repair",
        "brake_service_and_repair",
        "oil_change_station",
    ),
    "barber_shop": ("barber",),
    "nail_salon": ("nail_salon",),
    "beauty_salon": ("beauty_salon", "hair_salon", "beauty_service"),
    "massage_therapy": ("massage", "massage_therapy"),
    "notary": ("notary_public",),
    "restaurant": (
        "restaurant",
        "mexican_restaurant",
        "pizza_restaurant",
        "american_restaurant",
        "chinese_restaurant",
        "japanese_restaurant",
        "italian_restaurant",
        "indian_restaurant",
        "taco_restaurant",
        "mediterranean_restaurant",
        "breakfast_and_brunch_restaurant",
        "barbecue_restaurant",
        "sushi_restaurant",
    ),
    "coffee_shop": ("coffee_shop", "coffee_roastery", "cafe"),
    "bakery": ("bakery", "donut_shop", "cupcake_shop"),
    "plumber": ("plumbing",),
    "electrician": ("electrician",),
    "roofer": ("roofing",),
    "landscaper": ("landscaping", "gardener"),
    "house_cleaning": ("home_cleaning", "office_cleaning", "cleaning_service"),
    "dog_groomer": ("pet_groomer",),
    "yoga_studio": ("yoga_studio",),
    "music_lessons": ("music_school",),
    "tutoring": ("tutoring_center", "private_tutor", "tutoring_service"),
    "accountant": ("accountant", "tax_service"),
}

WEBSITE_KEEP_HOST_FRAGMENTS = (
    "acuityscheduling.com",
    "booksy.com",
    "facebook.com",
    "fresha.com",
    "instagram.com",
    "mindbodyonline.com",
    "mytime.com",
    "opentable.com",
    "schedulicity.com",
    "setmore.com",
    "square.site",
    "toasttab.com",
    "vagaro.com",
    "yelp.com",
)


class OverturePlacesConnector:
    source = "overture"

    def __init__(
        self,
        *,
        release: str = DEFAULT_OVERTURE_RELEASE,
        confidence_floor: float = 0.45,
        connection: Any | None = None,
    ) -> None:
        self.release = release
        self.confidence_floor = confidence_floor
        self._connection = connection
        self.connector_version = f"overture-{release}-v1"

    def query_for(self, city: CityConfig, genre: GenreConfig) -> str:
        categories = ",".join(OVERTURE_GENRE_CATEGORIES.get(genre.id, (genre.id,)))
        bbox = _bbox_for_city(city)
        return (
            f"release={self.release} categories={categories} "
            f"bbox={bbox[0]:.5f},{bbox[1]:.5f},{bbox[2]:.5f},{bbox[3]:.5f} "
            f"confidence>={self.confidence_floor}"
        )

    def fetch_candidates(
        self, city: CityConfig, genre: GenreConfig, *, limit: int
    ) -> list[ProspectCandidate]:
        query = build_overture_query(
            city=city,
            genre=genre,
            release=self.release,
            limit=limit,
            confidence_floor=self.confidence_floor,
        )
        connection = self._connection or _duckdb_connection()
        result = connection.execute(query)
        columns = [column[0] for column in result.description]
        return [
            overture_row_to_candidate(dict(zip(columns, row, strict=True)), city=city, genre=genre)
            for row in result.fetchall()
        ]


def build_overture_query(
    *,
    city: CityConfig,
    genre: GenreConfig,
    release: str,
    limit: int,
    confidence_floor: float = 0.45,
) -> str:
    path = f"{OVERTURE_S3_ROOT}/{release}/theme=places/type=place/*"
    min_lng, max_lng, min_lat, max_lat = _bbox_for_city(city)
    category_values = OVERTURE_GENRE_CATEGORIES.get(genre.id, (genre.id,))
    category_sql = ", ".join(_sql_quote(value) for value in category_values)
    return f"""
SELECT
  id,
  names,
  addresses,
  phones,
  websites,
  socials,
  categories,
  taxonomy,
  confidence,
  operating_status,
  bbox
FROM read_parquet('{path}', filename=true, hive_partitioning=1)
WHERE bbox.xmin BETWEEN {min_lng:.8f} AND {max_lng:.8f}
  AND bbox.ymin BETWEEN {min_lat:.8f} AND {max_lat:.8f}
  AND names.primary IS NOT NULL
  AND (operating_status IS NULL OR operating_status != 'permanently_closed')
  AND (confidence IS NULL OR confidence >= {confidence_floor:.2f})
  AND (
    categories.primary IN ({category_sql})
    OR taxonomy.primary IN ({category_sql})
    OR basic_category IN ({category_sql})
  )
  AND (
    websites IS NULL
    OR len(websites)=0
    OR {_websites_all_allowed_filter()}
  )
ORDER BY confidence DESC NULLS LAST, names.primary
LIMIT {max(limit, 0)}
""".strip()


def overture_row_to_candidate(
    row: dict[str, object], *, city: CityConfig, genre: GenreConfig
) -> ProspectCandidate:
    names = _mapping(row.get("names"))
    social_urls = _list(row.get("socials"))
    return ProspectCandidate(
        source="overture",
        source_id=str(row.get("id", "")),
        display_name=str(names.get("primary", "")).strip(),
        formatted_address=_format_overture_address(row.get("addresses")),
        phone=_first(_list(row.get("phones"))),
        city_id=city.id,
        genre_id=genre.id,
        website_uri=_first(_list(row.get("websites"))),
        social_urls=social_urls,
        marketplace_urls=[],
        source_confidence=_float(row.get("confidence")),
    )


def _duckdb_connection() -> Any:
    import duckdb  # type: ignore

    connection = duckdb.connect()
    connection.execute("LOAD httpfs;")
    connection.execute("SET s3_region='us-west-2';")
    return connection


def _bbox_for_city(city: CityConfig) -> tuple[float, float, float, float]:
    lat_degrees = city.radius_m / 111_320
    lng_degrees = city.radius_m / (
        111_320 * max(math.cos(math.radians(city.lat)), 0.1)
    )
    return (
        city.lng - lng_degrees,
        city.lng + lng_degrees,
        city.lat - lat_degrees,
        city.lat + lat_degrees,
    )


def _format_overture_address(value: object) -> str:
    addresses = _list(value)
    first = addresses[0] if addresses else {}
    mapping = _mapping(first)
    parts = [
        str(mapping.get("freeform", "")).strip(),
        str(mapping.get("locality", "")).strip(),
        " ".join(
            part
            for part in [
                str(mapping.get("region", "")).strip(),
                str(mapping.get("postcode", "")).strip(),
            ]
            if part
        ),
    ]
    return ", ".join(part for part in parts if part)


def _mapping(value: object) -> dict[str, object]:
    return dict(value) if isinstance(value, dict) else {}


def _list(value: object) -> list[object]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    return [value]


def _first(values: list[object]) -> str:
    return str(values[0]).strip() if values else ""


def _float(value: object) -> float:
    if value is None or value == "":
        return 0.0
    return float(value)  # type: ignore[arg-type]


def _sql_quote(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def _websites_all_allowed_filter() -> str:
    allowed = " OR ".join(
        f"contains(lower(x), '{fragment}')" for fragment in WEBSITE_KEEP_HOST_FRAGMENTS
    )
    return f"len(list_filter(websites, x -> NOT ({allowed}))) = 0"
