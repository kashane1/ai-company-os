"""Tests for catalog discrimination, price parsing, and the write path."""

from __future__ import annotations

import datetime as dt
import sqlite3

import pytest

from ingest import backfill, catalog, metrics
from ingest.config import SCHEMA_PATH, day_index
from ingest.tcgcsv import PriceRow, parse_price_row


@pytest.fixture()
def connection() -> sqlite3.Connection:
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    connection.executescript(SCHEMA_PATH.read_text())
    return connection


def product(name: str, *, number: str | None = "001/100", rarity: str | None = "Rare") -> dict:
    extended = []
    if number is not None:
        extended.append({"name": "Number", "value": number})
    if rarity is not None:
        extended.append({"name": "Rarity", "value": rarity})
    return {"productId": 1, "name": name, "extendedData": extended}


# ---------------------------------------------------------------------------
# Singles vs sealed
# ---------------------------------------------------------------------------


def test_cards_with_number_and_rarity_are_singles():
    assert catalog.is_single(product("Charizard ex - 006/165"))


@pytest.mark.parametrize(
    "name",
    [
        "Scarlet & Violet Booster Box",
        "Paldea Evolved Elite Trainer Box",
        "Charizard ex Premium Collection",
        "Build & Battle Box",
        "Pikachu V Blister Pack",
        "Online Code Card",
    ],
)
def test_sealed_products_are_rejected_by_name_even_with_a_rarity(name):
    """Some sealed items carry a Rarity, so the name markers are load-bearing."""
    assert not catalog.is_single(product(name))


def test_products_missing_a_collector_number_are_not_singles():
    assert not catalog.is_single(product("Mystery Item", number=None))


def test_products_missing_a_rarity_are_not_singles():
    assert not catalog.is_single(product("Mystery Item", rarity=None))


# ---------------------------------------------------------------------------
# Price row parsing
# ---------------------------------------------------------------------------


def test_valid_price_row_parses():
    row = parse_price_row(
        {
            "productId": 42,
            "subTypeName": "Holofoil",
            "marketPrice": 12.5,
            "lowPrice": 9.0,
            "highPrice": 20.0,
        }
    )

    assert row == PriceRow(42, "Holofoil", 12.5, 9.0, 20.0)


@pytest.mark.parametrize(
    "payload",
    [
        {"productId": 1, "subTypeName": "Normal", "marketPrice": None},
        {"productId": 1, "subTypeName": None, "marketPrice": 5.0},
        {"productId": None, "subTypeName": "Normal", "marketPrice": 5.0},
        {"productId": 1, "subTypeName": "Normal", "marketPrice": 0},
        {"productId": 1, "subTypeName": "Normal", "marketPrice": -3.0},
        {"productId": 1, "subTypeName": "Normal", "marketPrice": "n/a"},
    ],
)
def test_rows_without_a_usable_market_price_are_dropped(payload):
    """A missing market price means TCGplayer had no sales-derived value that
    day. Storing it as NULL would let it reach the screener as a real price."""
    assert parse_price_row(payload) is None


def test_missing_listing_bounds_become_none_without_dropping_the_row():
    row = parse_price_row({"productId": 1, "subTypeName": "Normal", "marketPrice": 4.0})

    assert row is not None
    assert row.low_price is None and row.high_price is None


# ---------------------------------------------------------------------------
# Write path
# ---------------------------------------------------------------------------


def seed_card(connection: sqlite3.Connection, product_id: int = 100) -> None:
    connection.execute("INSERT INTO sets (group_id, name, released_on) VALUES (1, 'Test Set', '2024-01-15')")
    connection.execute(
        "INSERT INTO cards (product_id, group_id, name, number, rarity) VALUES (?, 1, 'Test Card', '1/10', 'Rare')",
        (product_id,),
    )
    connection.commit()


def test_write_day_creates_variants_and_observations(connection):
    seed_card(connection)
    date = dt.date(2024, 3, 1)

    written, created = backfill._write_day(
        connection,
        date,
        [
            PriceRow(100, "Holofoil", 10.0, 8.0, 14.0),
            PriceRow(100, "Reverse Holofoil", 4.0, 3.0, 6.0),
        ],
        singles={100},
        variant_ids={},
    )

    assert (written, created) == (2, 2)
    assert connection.execute("SELECT COUNT(*) FROM card_variants").fetchone()[0] == 2
    assert connection.execute("SELECT COUNT(*) FROM price_observations").fetchone()[0] == 2


def test_write_day_ignores_products_outside_the_singles_catalog(connection):
    """Sealed products share the price feed; they must not become screener rows."""
    seed_card(connection)

    written, _ = backfill._write_day(
        connection,
        dt.date(2024, 3, 1),
        [PriceRow(100, "Holofoil", 10.0, 8.0, 14.0), PriceRow(999, "Normal", 90.0, 80.0, 99.0)],
        singles={100},
        variant_ids={},
    )

    assert written == 1


def test_reingesting_a_day_updates_rather_than_duplicating(connection):
    seed_card(connection)
    date = dt.date(2024, 3, 1)

    backfill._write_day(connection, date, [PriceRow(100, "Holofoil", 10.0, 8.0, 14.0)], {100}, {})
    backfill._write_day(connection, date, [PriceRow(100, "Holofoil", 11.5, 9.0, 15.0)], {100}, {})

    rows = connection.execute("SELECT market_price FROM price_observations").fetchall()
    assert [row["market_price"] for row in rows] == [11.5]


def test_ingested_days_lets_backfill_resume(connection):
    seed_card(connection)
    backfill._write_day(
        connection, dt.date(2024, 3, 1), [PriceRow(100, "Holofoil", 10.0, None, None)], {100}, {}
    )

    remaining = backfill.missing_dates(
        connection, start=dt.date(2024, 3, 1), end=dt.date(2024, 3, 3)
    )

    assert remaining == [dt.date(2024, 3, 2), dt.date(2024, 3, 3)]


def test_prune_removes_variants_that_never_had_a_price(connection):
    seed_card(connection)
    catalog.ensure_variants(connection, {(100, "Holofoil"), (100, "1st Edition")})
    variant_ids = catalog.variant_id_map(connection)
    connection.execute(
        "INSERT INTO price_observations (variant_id, day, market_price) VALUES (?, 60, 10.0)",
        (variant_ids[(100, "Holofoil")],),
    )
    connection.commit()

    removed = catalog.prune_variants_without_prices(connection)

    assert removed == 1
    assert connection.execute("SELECT COUNT(*) FROM card_variants").fetchone()[0] == 1


# ---------------------------------------------------------------------------
# Ingest → metrics → screener view, end to end on a tiny dataset
# ---------------------------------------------------------------------------


def test_pipeline_produces_a_screener_row(connection):
    """Proves the schema, write path, metrics rebuild and view agree."""
    seed_card(connection)

    # 200 days of history: a peak of $100 early, drifting down to $25.
    start = dt.date(2024, 3, 1)
    for offset in range(200):
        price = 100.0 - (75.0 * offset / 199.0)
        backfill._write_day(
            connection,
            start + dt.timedelta(days=offset),
            [PriceRow(100, "Holofoil", round(price, 2), round(price * 0.9, 2), round(price * 1.1, 2))],
            {100},
            {},
        )

    written = metrics.rebuild_metrics(connection)
    assert written == 1

    row = connection.execute("SELECT * FROM screener_rows").fetchone()
    assert row["card_name"] == "Test Card"
    assert row["sub_type"] == "Holofoil"
    assert row["current_price"] == pytest.approx(25.0, abs=0.5)
    assert row["peak_price"] == pytest.approx(100.0)
    assert row["discount_from_peak_pct"] == pytest.approx(75.0, abs=0.5)
    assert row["observation_count"] == 200
    assert row["history_days"] == 200
    # The peak is the first observation, and the set released before it.
    assert row["peak_is_first_observation"] == 1
    assert row["as_of_day"] == day_index(start + dt.timedelta(days=199))


def test_metrics_rebuild_is_idempotent(connection):
    seed_card(connection)
    for offset in range(60):
        backfill._write_day(
            connection,
            dt.date(2024, 3, 1) + dt.timedelta(days=offset),
            [PriceRow(100, "Holofoil", 20.0 - offset * 0.1, None, None)],
            {100},
            {},
        )

    first = metrics.rebuild_metrics(connection)
    second = metrics.rebuild_metrics(connection)

    assert first == second == 1
    assert connection.execute("SELECT COUNT(*) FROM card_metrics").fetchone()[0] == 1


def test_metrics_rebuild_without_observations_is_an_error(connection):
    with pytest.raises(RuntimeError, match="no price observations"):
        metrics.rebuild_metrics(connection)
