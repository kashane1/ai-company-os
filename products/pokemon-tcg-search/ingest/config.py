"""Shared constants and paths for the Pokemon TCG price screener."""

from __future__ import annotations

import datetime as dt
import os
from pathlib import Path

PRODUCT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = Path(os.environ.get("POKETCG_DATA_DIR", PRODUCT_ROOT / "data"))
ARCHIVE_CACHE_DIR = DATA_DIR / "archives"
DATABASE_PATH = Path(os.environ.get("POKETCG_DB", DATA_DIR / "pokemon.db"))
SCHEMA_PATH = Path(__file__).resolve().parent / "schema.sql"

TCGCSV_BASE = "https://tcgcsv.com"

# TCGplayer category id for English Pokemon.
POKEMON_CATEGORY_ID = 3

# Earliest daily archive tcgcsv.com publishes. Verified by probing:
# 2024-02-07 and earlier return 404, 2024-02-08 returns 200.
ARCHIVE_START_DATE = dt.date(2024, 2, 8)

# `day` columns store an integer offset from this date. Chosen to sit just
# before ARCHIVE_START_DATE so every stored day is a small positive integer.
DAY_EPOCH = dt.date(2024, 1, 1)

# Finishes TCGplayer reports for Pokemon singles, in rough desirability order.
KNOWN_SUB_TYPES = (
    "Normal",
    "Holofoil",
    "Reverse Holofoil",
    "1st Edition",
    "1st Edition Holofoil",
    "Unlimited",
    "Unlimited Holofoil",
)


def day_index(date: dt.date) -> int:
    """Convert a calendar date to the integer `day` used in the database."""
    return (date - DAY_EPOCH).days


def date_from_day_index(day: int) -> dt.date:
    """Inverse of :func:`day_index`."""
    return DAY_EPOCH + dt.timedelta(days=day)


def iso_from_day_index(day: int) -> str:
    return date_from_day_index(day).isoformat()
