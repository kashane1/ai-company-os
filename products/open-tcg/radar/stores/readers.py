"""Store readers for platforms other than Shopify JSON (plan phase P5).

Every reader offers what the collector needs from `StoreReader`:
`robots_allows_products()` and a newest-first `fetch(max_pages=...)`. Each
returns Shopify-shaped product dicts (`id`, `title`, `handle`, `vendor`,
`product_type`, `tags`, `variants`), plus `url`, so matching, snapshots, MSRP
classes and alerts work unchanged. Collection discovery stays Shopify-only.

- `WooCommerceReader` reads the public WooCommerce Store API
  (`/wp-json/wc/store/v1/products`), newest first.
- `SitemapReader` reads a product sitemap and then the schema.org `Product`
  data (JSON-LD) on the Pokémon-looking product pages. That's Wix and
  custom sites that publish both. A discovery read fetches the most recently
  modified pages; a full sweep fetches every Pokémon-looking page.

Network only, like `StoreReader`: nothing here touches the database.
"""

from __future__ import annotations

import hashlib
import html
import json
import re
from typing import Iterable
from urllib.parse import urlsplit

import httpx

from .registry import Store
from .shopify import FetchResult, StoreFetchError, StoreReader

WOO_PRODUCTS_PATH = "/wp-json/wc/store/v1/products"
WOO_PAGE_SIZE = 100
SITEMAP_PATH = "/sitemap.xml"
# Product pages per read: a discovery read checks the newest ones only.
SITEMAP_DISCOVERY_PAGES = 8
SITEMAP_SWEEP_PAGES = 150
SITEMAP_MAX_CHILDREN = 6
_IN_STOCK = frozenset({"instock", "preorder", "presale", "limitedavailability", "onlineonly", "instoreonly"})
_LD_JSON = re.compile(r"<script[^>]*application/ld\+json[^>]*>(.*?)</script>", re.IGNORECASE | re.DOTALL)
_URL_ENTRY = re.compile(r"<url>(.*?)</url>", re.DOTALL)
_SITEMAP_ENTRY = re.compile(r"<sitemap>(.*?)</sitemap>", re.DOTALL)
_LOC = re.compile(r"<loc>\s*([^<\s]+)\s*</loc>")
_LASTMOD = re.compile(r"<lastmod>\s*([^<\s]+)\s*</lastmod>")


def stable_id(text: str) -> int:
    """A positive 60-bit integer id from a URL, for stores without numeric variant ids."""
    return int(hashlib.sha1(text.encode()).hexdigest()[:15], 16)


def _text(value: object) -> str:
    return html.unescape(re.sub(r"<[^>]+>", "", str(value or ""))).strip()


class WooCommerceReader(StoreReader):
    def robots_allows_products(self) -> bool:
        return self.robots_allows(WOO_PRODUCTS_PATH)

    def products_page(self, page: int, collection: str | None = None) -> list[dict]:
        response = self._get(
            WOO_PRODUCTS_PATH, {"per_page": WOO_PAGE_SIZE, "page": page, "orderby": "date", "order": "desc"}
        )
        if response.status_code == 400 and page > 1:
            return []  # WooCommerce answers 400 past the last page
        if response.status_code != 200:
            raise StoreFetchError(f"{WOO_PRODUCTS_PATH} page {page} HTTP {response.status_code}")
        try:
            items = response.json()
        except ValueError as exc:
            raise StoreFetchError(f"{WOO_PRODUCTS_PATH} page {page} is not JSON") from exc
        if not isinstance(items, list):
            raise StoreFetchError(f"{WOO_PRODUCTS_PATH} page {page} has no product list")
        return [product for product in (woo_product(item) for item in items) if product]

    def fetch(self, *, max_pages: int, collection: str | None = None) -> FetchResult:
        result = FetchResult()
        for page in range(1, max_pages + 1):
            products = self.products_page(page)
            result.products.extend(products)
            result.pages_fetched = page
            if len(products) < WOO_PAGE_SIZE:
                return result
        result.is_truncated = True
        return result


def woo_product(item: dict) -> dict | None:
    """A Store API product as a Shopify-shaped product with one variant."""
    if not isinstance(item, dict) or not isinstance(item.get("id"), int):
        return None
    prices = item.get("prices") or {}
    price = None
    try:
        minor = int(prices.get("currency_minor_unit", 2))
        if prices.get("price") not in (None, ""):
            price = f"{int(prices['price']) / 10 ** minor:.2f}"
    except (TypeError, ValueError):
        price = None
    categories = [_text(c.get("name")) for c in item.get("categories") or [] if isinstance(c, dict)]
    tags = [_text(t.get("name")) for t in item.get("tags") or [] if isinstance(t, dict)]
    brands = [_text(b.get("name")) for b in item.get("brands") or [] if isinstance(b, dict)]
    is_available = bool(item.get("is_in_stock")) and item.get("is_purchasable", True) is not False
    return {
        "id": item["id"],
        "title": _text(item.get("name")),
        "handle": item.get("slug") or str(item["id"]),
        "vendor": ", ".join(brands),
        "product_type": ", ".join(categories),
        "tags": categories + tags,
        "created_at": None,
        "url": item.get("permalink"),
        "variants": [{"id": item["id"], "title": "Default Title", "price": price, "available": is_available}],
    }


class SitemapReader(StoreReader):
    """Product sitemap plus schema.org Product data on each product page."""

    def __init__(self, store: Store, client: httpx.Client, *, match_words: Iterable[str] = (), **kwargs):
        super().__init__(store, client, **kwargs)
        # Slug words that make a product page worth reading ("pokemon", set names).
        self.match_words = tuple(sorted({"pokemon", *match_words}, key=len, reverse=True))
        self.product_path = store.product_path or "/product"

    def robots_allows_products(self) -> bool:
        return self.robots_allows(SITEMAP_PATH) and self.robots_allows(self.product_path + "/")

    def _sitemap(self, path: str) -> str:
        response = self._get(path)
        if response.status_code != 200:
            raise StoreFetchError(f"{path} HTTP {response.status_code}")
        return response.text

    def product_urls(self) -> list[tuple[str, str]]:
        """(url, lastmod) for every product page in the sitemap(s), newest first."""
        text = self._sitemap(SITEMAP_PATH)
        children = [_LOC.search(entry) for entry in _SITEMAP_ENTRY.findall(text)]
        child_urls = [match.group(1) for match in children if match]
        if child_urls:
            product_maps = [url for url in child_urls if "product" in url.lower()] or child_urls
            text = "".join(self._sitemap(_path(url)) for url in product_maps[:SITEMAP_MAX_CHILDREN])
        entries = []
        for entry in _URL_ENTRY.findall(text):
            loc = _LOC.search(entry)
            if not loc or self.product_path not in urlsplit(loc.group(1)).path:
                continue
            lastmod = _LASTMOD.search(entry)
            entries.append((html.unescape(loc.group(1)), lastmod.group(1) if lastmod else ""))
        return sorted(entries, key=lambda e: e[1], reverse=True)

    def is_candidate(self, url: str) -> bool:
        slug = urlsplit(url).path.lower().replace("-", " ").replace("_", " ")
        return any(word in slug for word in self.match_words)

    def fetch(self, *, max_pages: int, collection: str | None = None) -> FetchResult:
        limit = SITEMAP_DISCOVERY_PAGES if max_pages <= 1 else SITEMAP_SWEEP_PAGES
        candidates = [url for url, _ in self.product_urls() if self.is_candidate(url)]
        result = FetchResult(is_truncated=len(candidates) > limit)
        for url in candidates[:limit]:
            response = self._get(_path(url))
            result.pages_fetched += 1
            if response.status_code in (404, 410):
                continue  # removed since the sitemap was written
            if response.status_code != 200:
                raise StoreFetchError(f"{_path(url)} HTTP {response.status_code}")
            product = ld_product(response.text, url)
            if product:
                result.products.append(product)
        return result


def _lowest(prices: list[str]) -> str | None:
    numbers = []
    for price in prices:
        try:
            numbers.append(float(price.replace("$", "").replace(",", "")))
        except ValueError:
            continue
    return f"{min(numbers):.2f}" if numbers else None


def _path(url: str) -> str:
    parts = urlsplit(url)
    return parts.path + (f"?{parts.query}" if parts.query else "")


def _walk(node: object) -> Iterable[dict]:
    if isinstance(node, dict):
        yield node
        for value in node.values():
            yield from _walk(value)
    elif isinstance(node, list):
        for value in node:
            yield from _walk(value)


def _is_product(node: dict) -> bool:
    kind = node.get("@type")
    return kind == "Product" or (isinstance(kind, list) and "Product" in kind)


def ld_product(page: str, url: str) -> dict | None:
    """The page's schema.org Product as a Shopify-shaped product, or None."""
    for block in _LD_JSON.findall(page):
        try:
            data = json.loads(block.strip())
        except ValueError:
            continue
        product = next((node for node in _walk(data) if _is_product(node)), None)
        if product is None:
            continue
        offers = product.get("offers")
        offer_list = offers if isinstance(offers, list) else [offers] if isinstance(offers, dict) else []
        prices = []
        is_available = False
        for offer in offer_list:
            price = offer.get("price", offer.get("lowPrice"))
            if price not in (None, ""):
                prices.append(str(price))
            availability = str(offer.get("availability") or "").rsplit("/", 1)[-1].lower()
            is_available = is_available or availability in _IN_STOCK
        brand = product.get("brand")
        brand_name = brand.get("name") if isinstance(brand, dict) else brand
        category = product.get("category")
        identity = stable_id(url)
        return {
            "id": identity,
            "title": _text(product.get("name")),
            "handle": urlsplit(url).path.rstrip("/").rsplit("/", 1)[-1],
            "vendor": _text(brand_name),
            "product_type": _text(category if isinstance(category, str) else ""),
            "tags": [],
            "created_at": None,
            "url": url,
            "variants": [{
                "id": identity,
                "title": "Default Title",
                "price": _lowest(prices),
                "available": is_available,
            }],
        }
    return None
