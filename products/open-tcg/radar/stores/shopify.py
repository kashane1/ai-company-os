"""Read a Shopify store's public /products.json, politely.

Network only: nothing here touches the database, so stores can be fetched on
worker threads while the caller writes results on its own thread.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Callable
from urllib.parse import quote, urlsplit
from urllib.robotparser import RobotFileParser

import httpx

from ..config import STORE_MIN_REQUEST_INTERVAL_S, STORE_PAGE_SIZE, USER_AGENT
from .registry import Store

PRODUCTS_PATH = "/products.json"
COLLECTIONS_PATH = "/collections.json"


def collection_products_path(handle: str) -> str:
    return f"/collections/{quote(handle, safe='-_')}/products.json"


class StoreFetchError(Exception):
    """A fetch failed. The store's listings are unknown, never "sold out"."""


@dataclass
class FetchResult:
    products: list[dict] = field(default_factory=list)
    pages_fetched: int = 0
    is_truncated: bool = False


def _same_site(url: httpx.URL | str, domain: str) -> bool:
    host = (urlsplit(str(url)).hostname or "").lower()
    return host.removeprefix("www.") == domain.removeprefix("www.")


class StoreReader:
    """One store's requests, spaced at least `min_interval_s` apart."""

    def __init__(
        self,
        store: Store,
        client: httpx.Client,
        *,
        min_interval_s: float = STORE_MIN_REQUEST_INTERVAL_S,
        sleep: Callable[[float], None] = time.sleep,
        clock: Callable[[], float] = time.monotonic,
    ):
        self.store = store
        self.client = client
        self.min_interval_s = min_interval_s
        self.sleep = sleep
        self.clock = clock
        self._last_request_at: float | None = None

    def _get(self, path: str, params: dict | None = None) -> httpx.Response:
        if self._last_request_at is not None:
            wait = self.min_interval_s - (self.clock() - self._last_request_at)
            if wait > 0:
                self.sleep(wait)
        self._last_request_at = self.clock()
        try:
            response = self.client.get(self.store.base_url + path, params=params)
        except httpx.HTTPError as exc:
            raise StoreFetchError(f"{type(exc).__name__}: {exc}") from exc
        if not _same_site(response.url, self.store.domain):
            raise StoreFetchError(f"redirected off {self.store.domain} to {response.url.host}")
        return response

    def robots_allows(self, path: str) -> bool:
        response = self._get("/robots.txt")
        if response.status_code in (404, 410):
            return True
        if response.status_code != 200:
            raise StoreFetchError(f"robots.txt HTTP {response.status_code}")
        parser = RobotFileParser()
        parser.parse(response.text.splitlines())
        return parser.can_fetch(USER_AGENT, path)

    def robots_allows_products(self) -> bool:
        return self.robots_allows(PRODUCTS_PATH)

    def _json_list(self, path: str, key: str, page: int) -> list[dict]:
        response = self._get(path, {"limit": STORE_PAGE_SIZE, "page": page})
        label = f"{path} page {page}"
        if response.status_code != 200:
            raise StoreFetchError(f"{label} HTTP {response.status_code}")
        try:
            items = response.json()[key]
        except (ValueError, KeyError, TypeError) as exc:
            raise StoreFetchError(f"{label} is not Shopify {key} JSON") from exc
        if not isinstance(items, list):
            raise StoreFetchError(f"{label} has no {key} list")
        return items

    def products_page(self, page: int, collection: str | None = None) -> list[dict]:
        path = collection_products_path(collection) if collection else PRODUCTS_PATH
        return self._json_list(path, "products", page)

    def collections(self, *, max_pages: int) -> list[dict]:
        found: list[dict] = []
        for page in range(1, max_pages + 1):
            items = self._json_list(COLLECTIONS_PATH, "collections", page)
            found.extend(items)
            if len(items) < STORE_PAGE_SIZE:
                break
        return found

    def fetch(self, *, max_pages: int, collection: str | None = None) -> FetchResult:
        """Newest-first pages (of the catalog or one collection) until a short page or `max_pages`."""
        result = FetchResult()
        for page in range(1, max_pages + 1):
            products = self.products_page(page, collection)
            result.products.extend(products)
            result.pages_fetched = page
            if len(products) < STORE_PAGE_SIZE:
                return result
        result.is_truncated = True
        return result
