"""Paths and constants. Runtime data stays inside this product's git-ignored data/."""

from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
DB_PATH = Path(os.environ.get("OPEN_TCG_DB", DATA_DIR / "radar.db"))
SCHEMA_PATH = Path(__file__).with_name("schema.sql")
WATCHLIST_PATH = ROOT / "watchlist.toml"

# Every request identifies itself; tcgcsv asks for an identifiable User-Agent.
USER_AGENT = "open-tcg-radar/0.1 (+personal, non-commercial)"
REQUEST_TIMEOUT_S = 30.0

TCGCSV_BASE = "https://tcgcsv.com"
POKEMON_CATEGORY_ID = 3
# tcgcsv's FAQ asks for roughly a quarter second between requests.
TCGCSV_DELAY_S = 0.25
# Groups published within this many days (or in the future) are "current".
CATALOG_WINDOW_DAYS = 120

SOUTHERN_HOBBY_URL = "https://www.southernhobby.com/ccg-s/pokemon/c13_259/"
SOUTHERN_HOBBY_MAX_PAGES = 3
POKEBEACH_RSS_URL = "https://www.pokebeach.com/forums/forum/front-page-news.18/index.rss"
