"""Client for tcgcsv.com, a free daily mirror of the TCGplayer catalog and prices."""

from __future__ import annotations

import time

import httpx

from ..config import POKEMON_CATEGORY_ID, TCGCSV_BASE, TCGCSV_DELAY_S
from ..http import make_client


class TcgCsvError(RuntimeError):
    pass


class TcgCsvClient:
    """Polite client: one request at a time, spaced as tcgcsv's FAQ asks."""

    def __init__(self, client: httpx.Client | None = None, delay_s: float = TCGCSV_DELAY_S) -> None:
        self._client = client or make_client()
        self._delay_s = delay_s
        self._last_request_at = 0.0

    def close(self) -> None:
        self._client.close()

    def _get(self, path: str) -> list[dict]:
        wait = self._last_request_at + self._delay_s - time.monotonic()
        if wait > 0:
            time.sleep(wait)
        self._last_request_at = time.monotonic()
        response = self._client.get(f"{TCGCSV_BASE}{path}")
        response.raise_for_status()
        payload = response.json()
        if not payload.get("success", True):
            raise TcgCsvError(f"tcgcsv reported failure: {payload.get('errors')}")
        return payload.get("results") or []

    def fetch_groups(self) -> list[dict]:
        return self._get(f"/tcgplayer/{POKEMON_CATEGORY_ID}/groups")

    def fetch_products(self, group_id: int) -> list[dict]:
        return self._get(f"/tcgplayer/{POKEMON_CATEGORY_ID}/{group_id}/products")

    def fetch_prices(self, group_id: int) -> list[dict]:
        return self._get(f"/tcgplayer/{POKEMON_CATEGORY_ID}/{group_id}/prices")
