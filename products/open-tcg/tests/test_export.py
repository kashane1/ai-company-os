from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest
from radar import db
from radar.export import ExportError, export_observations


def _source_db(path: Path) -> sqlite3.Connection:
    connection = db.connect(path)
    db.init(connection)
    return connection


def _insert_observation(
    connection: sqlite3.Connection,
    *,
    external_id: str,
    received_at: str,
    source_time: str | None = None,
    text: str = "Pokemon restock",
) -> None:
    connection.execute(
        """
        INSERT INTO observations
            (source_id, external_id, author, text, signal, retailer, product_text,
             price, url, is_tcg, source_time, received_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            "bluesky",
            external_id,
            "@radar",
            text,
            "in_stock",
            "Target",
            "Pokemon ETB",
            49.99,
            "https://example.test/item",
            1,
            source_time,
            received_at,
        ),
    )
    connection.commit()


def test_export_observations_is_read_only_and_paginates_timestamp_ties(tmp_path: Path) -> None:
    database = tmp_path / "radar.sqlite3"
    connection = _source_db(database)
    _insert_observation(connection, external_id="one", received_at="2026-10-05T12:00:00+00:00")
    _insert_observation(connection, external_id="two", received_at="2026-10-05T12:00:00+00:00")
    connection.close()
    before = database.read_bytes()

    first_page = export_observations(database, limit=1)
    second_page = export_observations(database, after=first_page[0]["cursor"], limit=1)

    assert first_page[0]["schema_version"] == 1
    assert first_page[0]["origin"] == "open_tcg"
    assert first_page[0]["source"] == "bluesky"
    assert first_page[0]["raw_text"] == "Pokemon restock"
    assert first_page[0]["origin_key"] != second_page[0]["origin_key"]
    assert database.read_bytes() == before


def test_export_observations_rejects_missing_databases_bad_cursors_and_invalid_time(
    tmp_path: Path,
) -> None:
    missing = tmp_path / "missing.sqlite3"
    with pytest.raises(ExportError, match="does not exist"):
        export_observations(missing)
    assert not missing.exists()

    database = tmp_path / "radar.sqlite3"
    connection = _source_db(database)
    _insert_observation(connection, external_id="one", received_at="invalid")
    connection.close()
    with pytest.raises(ExportError, match="received_at"):
        export_observations(database)

    with pytest.raises(ExportError, match="cursor"):
        export_observations(database, after="not-a-cursor")


def test_export_observations_does_not_export_watch_matches_and_sanitizes_control_text(
    tmp_path: Path,
) -> None:
    database = tmp_path / "radar.sqlite3"
    connection = _source_db(database)
    _insert_observation(
        connection,
        external_id="one",
        received_at="2026-10-05T12:00:00+00:00",
        text="Pokemon\u0000restock",
    )
    connection.close()

    exported = export_observations(database)
    assert exported[0]["raw_text"] == "Pokemon restock"


@pytest.mark.parametrize("received", ["2026-10-05T12:00:00.123456+00:00", "2026-10-05T12:00:00Z"])
def test_cursor_preserves_database_sort_key_and_unknown_source_time(tmp_path, received):
    database = tmp_path / "radar.sqlite3"
    connection = _source_db(database)
    _insert_observation(connection, external_id="one", received_at=received)
    _insert_observation(connection, external_id="two", received_at=received)
    connection.close()
    first = export_observations(database, limit=1)[0]
    second = export_observations(database, after=first["cursor"], limit=1)[0]
    assert first["origin_key"] != second["origin_key"]
    assert first["observed_at"] is None
    assert export_observations(database, after=second["cursor"], limit=1) == []
