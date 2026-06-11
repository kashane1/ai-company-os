from __future__ import annotations

from pathlib import Path

from packages.prospecting.source_runs import SourceRunRecord, SourceRunStore


def test_source_run_key_is_stable_for_equivalent_queries() -> None:
    first = SourceRunRecord(
        source="overture",
        city_id="seattle",
        genre_id="auto_repair",
        query=" category = Automotive Repair ",
        connector_version="v1",
        status="completed",
    )
    second = SourceRunRecord(
        source="overture",
        city_id="seattle",
        genre_id="auto_repair",
        query="category = Automotive Repair",
        connector_version="v1",
        status="completed",
    )

    assert first.run_key == second.run_key


def test_source_run_store_detects_completed_source_query(tmp_path: Path) -> None:
    store = SourceRunStore(tmp_path / "source-runs")
    run = SourceRunRecord(
        source="fsq_os",
        city_id="seattle",
        genre_id="barber_shop",
        query="category_id=11064",
        connector_version="2026-06",
        status="completed",
        candidates_seen=100,
        records_created=12,
        records_updated=8,
        duplicates_skipped=80,
    )

    store.save(run)

    assert store.has_completed(
        source="fsq_os",
        city_id="seattle",
        genre_id="barber_shop",
        query="category_id=11064",
        connector_version="2026-06",
    )
    assert store.latest_for_cell("fsq_os", "seattle", "barber_shop") == run

