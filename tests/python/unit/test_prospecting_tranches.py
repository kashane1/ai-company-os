from __future__ import annotations

from packages.prospecting.config import CityConfig, GenreConfig
from packages.prospecting.tranches import (
    EXPANSION_GENRE_IDS,
    SCALE_GENRE_IDS,
    TRANCHE_1_CITY_IDS,
    build_collection_tranche,
)


def test_tranche1_is_ten_cities_by_six_scale_genres() -> None:
    plan = build_collection_tranche(
        "tranche1",
        cities=_cities(),
        genres=_genres(),
        source="fsq_os",
        candidates_per_cell=50,
    )

    assert plan.name == "tranche1"
    assert plan.source == "fsq_os"
    assert len(plan.city_ids) == 10
    assert plan.city_ids == list(TRANCHE_1_CITY_IDS)
    assert plan.genre_ids == list(SCALE_GENRE_IDS)
    assert len(plan.cells) == 60
    assert plan.candidates_per_cell == 50


def test_tranche2_expands_scale_genres_to_all_configured_cities() -> None:
    plan = build_collection_tranche(
        "tranche2",
        cities=_cities(),
        genres=_genres(),
        source="fsq_os",
        candidates_per_cell=50,
    )

    assert len(plan.city_ids) == 40
    assert plan.genre_ids == list(SCALE_GENRE_IDS)
    assert len(plan.cells) == 240


def test_tranche3_repeats_all_scale_cells_for_second_source() -> None:
    plan = build_collection_tranche(
        "tranche3",
        cities=_cities(),
        genres=_genres(),
        source="overture",
        candidates_per_cell=50,
    )

    assert plan.source == "overture"
    assert len(plan.city_ids) == 40
    assert plan.genre_ids == list(SCALE_GENRE_IDS)
    assert len(plan.cells) == 240


def test_tranche4_runs_remaining_enabled_genres_for_overture_expansion() -> None:
    plan = build_collection_tranche(
        "tranche4",
        cities=_cities(),
        genres=_genres(),
        source="overture",
        candidates_per_cell=50,
    )

    assert plan.source == "overture"
    assert len(plan.city_ids) == 40
    assert plan.genre_ids == list(EXPANSION_GENRE_IDS)
    assert len(plan.cells) == 520


def _cities() -> list[CityConfig]:
    tranche1 = [
        CityConfig(id=city_id, name=city_id.replace("_", " ").title(), lat=35.0, lng=-100.0)
        for city_id in TRANCHE_1_CITY_IDS
    ]
    extras = [
        CityConfig(id=f"city_{index}", name=f"City {index}", lat=35.0, lng=-100.0)
        for index in range(30)
    ]
    return tranche1 + extras


def _genres() -> list[GenreConfig]:
    return [
        GenreConfig(id=genre_id, label=genre_id.replace("_", " "), text_query_template="{label}")
        for genre_id in [*SCALE_GENRE_IDS, *EXPANSION_GENRE_IDS]
    ]
