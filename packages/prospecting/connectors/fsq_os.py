"""Foursquare OS Places local-file connector for prospect source collection."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from packages.config.settings import load_dotenv
from packages.prospecting.config import CityConfig, GenreConfig
from packages.prospecting.identity import ProspectCandidate

FSQ_OS_PLACES_PATH_ENV_VAR = "FSQ_OS_PLACES_PATH"

FSQ_OS_GENRE_LABELS: dict[str, tuple[str, ...]] = {
    "auto_repair": ("Automotive Repair", "Auto Garage"),
    "barber_shop": ("Barber", "Barbershop"),
    "nail_salon": ("Nail Salon",),
    "beauty_salon": ("Beauty Salon", "Hair Salon"),
    "massage_therapy": ("Massage Clinic", "Massage Therapist", "Massage"),
    "notary": ("Notary", "Notary Public"),
}


class FSQOSPlacesConnector:
    source = "fsq_os"
    connector_version = "fsq-os-local-v1"

    def __init__(
        self,
        *,
        source_path: str | Path | None = None,
        connection: Any | None = None,
    ) -> None:
        load_dotenv()
        self.source_path = str(
            source_path or os.environ.get(FSQ_OS_PLACES_PATH_ENV_VAR, "")
        ).strip()
        if not self.source_path:
            raise FSQOSConfigError(
                f"set ${FSQ_OS_PLACES_PATH_ENV_VAR} or pass --fsq-path to collect FSQ OS data"
            )
        self._connection = connection

    def query_for(self, city: CityConfig, genre: GenreConfig) -> str:
        labels = ",".join(FSQ_OS_GENRE_LABELS.get(genre.id, (genre.label.title(),)))
        return f"path={self.source_path} locality={city.name} labels={labels}"

    def fetch_candidates(
        self, city: CityConfig, genre: GenreConfig, *, limit: int
    ) -> list[ProspectCandidate]:
        query = build_fsq_os_query(
            source_path=self.source_path,
            city=city,
            genre=genre,
            limit=limit,
        )
        connection = self._connection or _duckdb_connection()
        result = connection.execute(query)
        columns = [column[0] for column in result.description]
        return [
            fsq_os_row_to_candidate(dict(zip(columns, row, strict=True)), city=city, genre=genre)
            for row in result.fetchall()
        ]


class FSQOSConfigError(RuntimeError):
    """Raised when FSQ OS source data is not available locally."""


def build_fsq_os_query(
    *,
    source_path: str,
    city: CityConfig,
    genre: GenreConfig,
    limit: int,
) -> str:
    labels = FSQ_OS_GENRE_LABELS.get(genre.id, (genre.label.title(),))
    label_filter = " OR ".join(
        f"CAST(fsq_category_labels AS VARCHAR) ILIKE {_sql_like(label)}" for label in labels
    )
    reader = _reader_for_path(source_path)
    city_name = city.name.split(",", 1)[0]
    return f"""
SELECT
  fsq_place_id,
  name,
  address,
  locality,
  region,
  postcode,
  tel,
  website,
  email,
  facebook_id,
  instagram,
  twitter,
  fsq_category_labels
FROM {reader}
WHERE (date_closed IS NULL OR CAST(date_closed AS VARCHAR) = '')
  AND ({label_filter})
  AND (
    locality ILIKE {_sql_like(city_name)}
    OR (
      latitude BETWEEN {city.lat - 0.25:.8f} AND {city.lat + 0.25:.8f}
      AND longitude BETWEEN {city.lng - 0.25:.8f} AND {city.lng + 0.25:.8f}
    )
  )
ORDER BY name
LIMIT {max(limit, 0)}
""".strip()


def fsq_os_row_to_candidate(
    row: dict[str, object], *, city: CityConfig, genre: GenreConfig
) -> ProspectCandidate:
    social_urls = _fsq_social_urls(row)
    return ProspectCandidate(
        source="fsq_os",
        source_id=str(row.get("fsq_place_id", "")),
        display_name=str(row.get("name", "")).strip(),
        formatted_address=_format_fsq_address(row),
        phone=str(row.get("tel", "") or "").strip(),
        city_id=city.id,
        genre_id=genre.id,
        website_uri=str(row.get("website", "") or "").strip(),
        social_urls=social_urls,
        marketplace_urls=[],
        source_confidence=0.0,
    )


def _duckdb_connection() -> Any:
    import duckdb  # type: ignore

    return duckdb.connect()


def _reader_for_path(source_path: str) -> str:
    quoted = "'" + source_path.replace("'", "''") + "'"
    if source_path.lower().endswith(".csv"):
        return f"read_csv_auto({quoted}, union_by_name=true)"
    return f"read_parquet({quoted}, union_by_name=true)"


def _format_fsq_address(row: dict[str, object]) -> str:
    parts = [
        str(row.get("address", "") or "").strip(),
        str(row.get("locality", "") or "").strip(),
        " ".join(
            part
            for part in [
                str(row.get("region", "") or "").strip(),
                str(row.get("postcode", "") or "").strip(),
            ]
            if part
        ),
    ]
    return ", ".join(part for part in parts if part)


def _fsq_social_urls(row: dict[str, object]) -> list[str]:
    urls: list[str] = []
    instagram = str(row.get("instagram", "") or "").strip()
    facebook = str(row.get("facebook_id", "") or "").strip()
    twitter = str(row.get("twitter", "") or "").strip()
    if instagram:
        urls.append(_social_url("https://instagram.com/", instagram))
    if facebook:
        urls.append(_social_url("https://facebook.com/", facebook))
    if twitter:
        urls.append(_social_url("https://twitter.com/", twitter))
    return urls


def _social_url(prefix: str, value: str) -> str:
    if value.startswith(("http://", "https://")):
        return value
    return prefix + value.lstrip("@/")


def _sql_like(value: str) -> str:
    return "'%" + value.replace("'", "''") + "%'"
