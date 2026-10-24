"""Paths and constants. Runtime data stays inside this product's git-ignored data/."""

from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
DB_PATH = Path(os.environ.get("OPEN_TCG_DB", DATA_DIR / "radar.db"))
SCHEMA_PATH = Path(__file__).with_name("schema.sql")
WATCHLIST_PATH = ROOT / "watchlist.toml"
STORES_PATH = ROOT / "stores.toml"
MSRP_PATH = ROOT / "msrp.toml"

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

# Bluesky restock accounts (handle -> DID). Jetstream filters by DID.
BLUESKY_ACCOUNTS = {
    "pokemonrestocks.bsky.social": "did:plc:u72efgy4ojdkcbw6qxn6iegg",
    "nowinstockus.bsky.social": "did:plc:bkgtv3dj7vvsfg4yauhiecum",
}
JETSTREAM_URL = "wss://jetstream2.us-east.bsky.network/subscribe"
BLUESKY_PUBLIC_API = "https://public.api.bsky.app/xrpc"

# Independent stores (Shopify /products.json). One request per host at a time,
# at least this far apart. Full sweeps page newest-first and stop at the cap.
STORE_MIN_REQUEST_INTERVAL_S = 4.0
STORE_PAGE_SIZE = 250
STORE_FULL_SWEEP_MAX_PAGES = 40
STORE_FULL_SWEEP_EVERY_S = 24 * 3600
STORE_ROBOTS_EVERY_S = 24 * 3600
STORE_FETCH_WORKERS = 10
# Whole-catalog sweeps (stores without a validated sealed collection) per sync
# run, so new stores' baselines spread across runs instead of one long one.
STORE_MAX_CATALOG_SWEEPS_PER_RUN = 8
# Sealed-collection discovery: weekly, bounded, and validated by sampling.
STORE_COLLECTIONS_EVERY_S = 7 * 24 * 3600
STORE_COLLECTION_LIST_MAX_PAGES = 8
STORE_COLLECTION_CANDIDATES_MAX = 6
STORE_COLLECTION_MIN_SEALED_SHARE = 0.5
# A collection at least this sealed makes the store's broader (min-share)
# collections redundant: those are mostly catch-alls full of singles.
STORE_COLLECTION_STRONG_SEALED_SHARE = 0.75
