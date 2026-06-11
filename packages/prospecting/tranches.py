"""Deterministic source-collection tranche plans."""

from __future__ import annotations

from dataclasses import dataclass

from packages.prospecting.config import CityConfig, GenreConfig

TRANCHE_1_CITY_IDS = (
    "fresno",
    "baltimore",
    "detroit",
    "phoenix",
    "jacksonville",
    "san_antonio",
    "fort_worth",
    "louisville",
    "albuquerque",
    "las_vegas",
)

SCALE_GENRE_IDS = (
    "auto_repair",
    "barber_shop",
    "nail_salon",
    "beauty_salon",
    "massage_therapy",
    "notary",
)

EXPANSION_GENRE_IDS = (
    "restaurant",
    "coffee_shop",
    "bakery",
    "plumber",
    "electrician",
    "roofer",
    "landscaper",
    "house_cleaning",
    "dog_groomer",
    "yoga_studio",
    "music_lessons",
    "tutoring",
    "accountant",
)


@dataclass(frozen=True)
class TrancheCell:
    city: CityConfig
    genre: GenreConfig

    @property
    def id(self) -> str:
        return f"{self.city.id}:{self.genre.id}"


@dataclass(frozen=True)
class CollectionTranche:
    name: str
    source: str
    cities: list[CityConfig]
    genres: list[GenreConfig]
    candidates_per_cell: int

    @property
    def city_ids(self) -> list[str]:
        return [city.id for city in self.cities]

    @property
    def genre_ids(self) -> list[str]:
        return [genre.id for genre in self.genres]

    @property
    def cells(self) -> list[TrancheCell]:
        return [TrancheCell(city, genre) for city in self.cities for genre in self.genres]


def build_collection_tranche(
    name: str,
    *,
    cities: list[CityConfig],
    genres: list[GenreConfig],
    source: str,
    candidates_per_cell: int,
) -> CollectionTranche:
    enabled_genres = [genre for genre in genres if genre.enabled]
    genre_index = {genre.id: genre for genre in enabled_genres}
    selected_genres = _require_ordered(genre_index, SCALE_GENRE_IDS, kind="genre")

    city_index = {city.id: city for city in cities}
    if name == "tranche1":
        selected_cities = _require_ordered(city_index, TRANCHE_1_CITY_IDS, kind="city")
    elif name in {"tranche2", "tranche3"}:
        selected_cities = cities
    elif name == "tranche4":
        selected_cities = cities
        selected_genres = _require_ordered(
            genre_index, EXPANSION_GENRE_IDS, kind="genre"
        )
    else:
        raise ValueError(f"unknown prospect collection tranche: {name}")

    return CollectionTranche(
        name=name,
        source=source,
        cities=selected_cities,
        genres=selected_genres,
        candidates_per_cell=candidates_per_cell,
    )


def default_source_for_tranche(name: str) -> str:
    if name in {"tranche1", "tranche2"}:
        return "fsq_os"
    if name == "tranche3":
        return "overture"
    if name == "tranche4":
        return "overture"
    raise ValueError(f"unknown prospect collection tranche: {name}")


def _require_ordered(
    index: dict[str, CityConfig] | dict[str, GenreConfig],
    ids: tuple[str, ...],
    *,
    kind: str,
) -> list[CityConfig] | list[GenreConfig]:
    missing = [item_id for item_id in ids if item_id not in index]
    if missing:
        raise ValueError(f"missing {kind} config ids for tranche: {', '.join(missing)}")
    return [index[item_id] for item_id in ids]
