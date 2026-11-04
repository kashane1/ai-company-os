"""Shared fixtures.

The intake path needs a catalog attached, but depending on the real one would
tie the suite to a 1.5 GB sibling database that may not exist on a fresh
checkout. `fake_catalog` builds a few-row stand-in with the same shape, so
these tests stay fast and self-contained.
"""

from __future__ import annotations

import sqlite3

import pytest
from inventory import db

# Mirrors the subset of pokemon-tcg-search's schema that inventory reads.
_CATALOG_DDL = """
CREATE TABLE sets (
    group_id INTEGER PRIMARY KEY, name TEXT, abbreviation TEXT, released_on TEXT
);
CREATE TABLE cards (
    product_id INTEGER PRIMARY KEY, group_id INTEGER, name TEXT, number TEXT,
    rarity TEXT, image_url TEXT, tcgplayer_url TEXT
);
CREATE TABLE card_variants (
    variant_id INTEGER PRIMARY KEY, product_id INTEGER, sub_type TEXT
);
CREATE TABLE card_metrics (
    variant_id INTEGER PRIMARY KEY,
    current_price REAL,
    days_since_price_change INTEGER,
    distinct_prices_90d INTEGER,
    current_vs_median_90d_pct REAL,
    observation_count_30d INTEGER,
    peak_is_first_observation INTEGER DEFAULT 0,
    peak_within_30d_of_release INTEGER DEFAULT 0
);
CREATE VIEW screener_rows AS
SELECT v.variant_id, c.product_id, c.name AS card_name, c.number AS card_number,
       c.rarity, v.sub_type, s.name AS set_name, s.abbreviation AS set_abbreviation,
       s.released_on, m.current_price, c.image_url, c.tcgplayer_url
  FROM card_variants v
  JOIN cards c ON c.product_id = v.product_id
  JOIN sets s ON s.group_id = c.group_id
  LEFT JOIN card_metrics m ON m.variant_id = v.variant_id;
"""

# variant_id, product_id, name, number, rarity, sub_type, price, health signals.
# The two Iono rows are the real 150x finish spread, which is what makes variant
# disambiguation matter at intake.
_CATALOG_ROWS = [
    (1, 101, "Iono", "269/193", "Special Illustration Rare", "Holofoil", 47.05, 1, 46, -2.0, 30),
    (2, 102, "Iono", "185/193", "Uncommon", "Normal", 0.30, 3, 12, -1.0, 28),
    (3, 103, "Charizard ex", "199/165", "Special Illustration Rare", "Holofoil", 300.29, 2, 51, -4.0, 30),
    (4, 104, "Togetic", "14/109", "Rare", "Holofoil", 49.99, 654, 1, -3.0, 7),
    (5, 105, "Pidgey", "16/64", "Common", "Normal", 0.25, 40, 3, -1.0, 9),
]


@pytest.fixture
def fake_catalog(tmp_path):
    path = tmp_path / "catalog.db"
    cat = sqlite3.connect(path)
    cat.executescript(_CATALOG_DDL)
    cat.execute("INSERT INTO sets VALUES (1, 'Paldea Evolved', 'PAL', '2023-06-09')")
    for (
        variant_id, product_id, name, number, rarity, sub_type,
        price, stale_days, distinct_90d, vs_median, obs_30d,
    ) in _CATALOG_ROWS:
        cat.execute(
            "INSERT INTO cards VALUES (?, 1, ?, ?, ?, NULL, NULL)",
            (product_id, name, number, rarity),
        )
        cat.execute(
            "INSERT INTO card_variants VALUES (?, ?, ?)", (variant_id, product_id, sub_type)
        )
        cat.execute(
            "INSERT INTO card_metrics VALUES (?, ?, ?, ?, ?, ?, 0, 0)",
            (variant_id, price, stale_days, distinct_90d, vs_median, obs_30d),
        )
    cat.commit()
    cat.close()
    return path


@pytest.fixture
def conn(tmp_path, fake_catalog):
    connection = db.connect(
        tmp_path / "inventory.db", catalog_path=fake_catalog, with_catalog=True
    )
    db.initialize(connection)
    yield connection
    connection.close()


@pytest.fixture
def bare_conn(tmp_path):
    """No catalog attached, for logic that doesn't need one."""
    connection = db.connect(tmp_path / "inventory.db", with_catalog=False)
    db.initialize(connection)
    yield connection
    connection.close()
