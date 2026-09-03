"""Client for tcgcsv.com — the only free source of daily TCGplayer history.

Two surfaces are used:

* Live JSON endpoints (`/tcgplayer/{category}/{group}/prices`) for today.
* Daily archives (`/archive/tcgplayer/prices-YYYY-MM-DD.ppmd.7z`) for history.
  Each archive is a 7z of every category's price files for that day, laid out
  as `YYYY-MM-DD/{categoryId}/{groupId}/prices`. Pokemon is ~217 of the ~4,600
  entries, so we extract selectively.

Archives are cached on disk because the backfill is long enough that you will
want to re-run parts of it without re-downloading ~2.5GB.
"""

from __future__ import annotations

import datetime as dt
import json
import re
import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

import httpx
import py7zr

from .config import ARCHIVE_CACHE_DIR, POKEMON_CATEGORY_ID, TCGCSV_BASE

REQUEST_TIMEOUT = httpx.Timeout(60.0, connect=15.0)


class TcgCsvError(RuntimeError):
    pass


@dataclass(frozen=True)
class PriceRow:
    """One (product, finish) price observation for a single day."""

    product_id: int
    sub_type: str
    market_price: float | None
    low_price: float | None
    high_price: float | None


def _client() -> httpx.Client:
    return httpx.Client(
        base_url=TCGCSV_BASE,
        timeout=REQUEST_TIMEOUT,
        follow_redirects=True,
        headers={"User-Agent": "pokemon-tcg-search/0.1 (+local screener)"},
    )


def _unwrap(payload: dict) -> list[dict]:
    if not payload.get("success", True):
        raise TcgCsvError(f"tcgcsv reported failure: {payload.get('errors')}")
    return payload.get("results") or []


# ---------------------------------------------------------------------------
# Live catalog + prices
# ---------------------------------------------------------------------------


def fetch_groups(client: httpx.Client | None = None) -> list[dict]:
    """All Pokemon sets (TCGplayer 'groups')."""
    owns_client = client is None
    client = client or _client()
    try:
        response = client.get(f"/tcgplayer/{POKEMON_CATEGORY_ID}/groups")
        response.raise_for_status()
        return _unwrap(response.json())
    finally:
        if owns_client:
            client.close()


def fetch_products(group_id: int, client: httpx.Client | None = None) -> list[dict]:
    """All products in one set, singles and sealed alike."""
    owns_client = client is None
    client = client or _client()
    try:
        response = client.get(f"/tcgplayer/{POKEMON_CATEGORY_ID}/{group_id}/products")
        response.raise_for_status()
        return _unwrap(response.json())
    finally:
        if owns_client:
            client.close()


def fetch_group_prices(group_id: int, client: httpx.Client | None = None) -> list[PriceRow]:
    """Today's prices for one set."""
    owns_client = client is None
    client = client or _client()
    try:
        response = client.get(f"/tcgplayer/{POKEMON_CATEGORY_ID}/{group_id}/prices")
        response.raise_for_status()
        return [row for row in map(parse_price_row, _unwrap(response.json())) if row]
    finally:
        if owns_client:
            client.close()


def parse_price_row(raw: dict) -> PriceRow | None:
    """Normalise one raw price record, dropping unusable ones.

    A row with no market price carries no signal for the screener — it means
    TCGplayer had no sales-derived value that day — so it is skipped rather
    than stored as NULL and filtered later.
    """
    product_id = raw.get("productId")
    sub_type = raw.get("subTypeName")
    market = raw.get("marketPrice")
    if product_id is None or not sub_type or market is None:
        return None
    try:
        market_price = float(market)
    except (TypeError, ValueError):
        return None
    if market_price <= 0:
        return None

    def optional_float(value: object) -> float | None:
        try:
            return float(value)  # type: ignore[arg-type]
        except (TypeError, ValueError):
            return None

    return PriceRow(
        product_id=int(product_id),
        sub_type=str(sub_type),
        market_price=market_price,
        low_price=optional_float(raw.get("lowPrice")),
        high_price=optional_float(raw.get("highPrice")),
    )


# ---------------------------------------------------------------------------
# Daily archives
# ---------------------------------------------------------------------------


def archive_url(date: dt.date) -> str:
    return f"{TCGCSV_BASE}/archive/tcgplayer/prices-{date.isoformat()}.ppmd.7z"


def archive_cache_path(date: dt.date) -> Path:
    return ARCHIVE_CACHE_DIR / f"prices-{date.isoformat()}.ppmd.7z"


def download_archive(
    date: dt.date,
    client: httpx.Client | None = None,
    *,
    keep_cache: bool = True,
) -> Path | None:
    """Fetch one daily archive, returning None when the day was not published.

    tcgcsv has gaps (missed publishing runs). A 404 is expected and benign, so
    it is reported as an absence rather than raised.
    """
    cached = archive_cache_path(date)
    if cached.exists() and cached.stat().st_size > 0:
        return cached

    owns_client = client is None
    client = client or _client()
    try:
        response = client.get(archive_url(date))
        if response.status_code == 404:
            return None
        response.raise_for_status()
        body = response.content
    finally:
        if owns_client:
            client.close()

    if keep_cache:
        cached.parent.mkdir(parents=True, exist_ok=True)
        temporary = cached.with_suffix(".part")
        temporary.write_bytes(body)
        temporary.replace(cached)
        return cached

    handle = tempfile.NamedTemporaryFile(suffix=".7z", delete=False)
    handle.write(body)
    handle.close()
    return Path(handle.name)


_POKEMON_ENTRY = re.compile(rf"^\d{{4}}-\d{{2}}-\d{{2}}/{POKEMON_CATEGORY_ID}/(\d+)/prices$")


def read_pokemon_prices_from_archive(archive_path: Path) -> Iterator[PriceRow]:
    """Yield every Pokemon price row inside a daily archive."""
    scratch = Path(tempfile.mkdtemp(prefix="tcgcsv-"))
    try:
        with py7zr.SevenZipFile(archive_path, "r") as archive:
            targets = [name for name in archive.getnames() if _POKEMON_ENTRY.match(name)]
            if not targets:
                return
            archive.extract(path=scratch, targets=targets)

        for name in targets:
            extracted = scratch / name
            if not extracted.exists():
                continue
            try:
                payload = json.loads(extracted.read_text())
            except (OSError, json.JSONDecodeError):
                continue
            for raw in payload.get("results") or []:
                row = parse_price_row(raw)
                if row:
                    yield row
    finally:
        shutil.rmtree(scratch, ignore_errors=True)
