from __future__ import annotations

import json

import httpx
import pytest

from radar.stores import collect, match, readers, registry

WOO = registry.Store(store_id="woo", name="Woo", domain="woo.com", tier="explore", platform="woocommerce")
WIX = registry.Store(store_id="wix", name="Wix", domain="wix.com", tier="explore", platform="wix",
                     product_path="/product-page")


def _client(routes: dict[str, httpx.Response | str]) -> tuple[httpx.Client, list[str]]:
    seen: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        key = request.url.path + (f"?{request.url.query.decode()}" if request.url.query else "")
        seen.append(key)
        for prefix, response in routes.items():
            if key == prefix or key.startswith(prefix + "?"):
                return response if isinstance(response, httpx.Response) else httpx.Response(200, text=response)
        return httpx.Response(404)

    return httpx.Client(transport=httpx.MockTransport(handler), follow_redirects=True), seen


def _woo_item(product_id: int, name: str, *, cents: str = "4999", in_stock: bool = True) -> dict:
    return {
        "id": product_id, "name": name, "slug": f"p{product_id}", "permalink": f"https://woo.com/product/p{product_id}/",
        "prices": {"price": cents, "currency_minor_unit": 2}, "is_in_stock": in_stock, "is_purchasable": True,
        "categories": [{"name": "Pok&eacute;mon"}], "tags": [],
    }


def test_woocommerce_product_mapping():
    product = readers.woo_product(_woo_item(7, "Delta Reign Elite Trainer Box &#8211; English", cents="5499"))
    assert product["title"] == "Delta Reign Elite Trainer Box – English"
    assert product["url"] == "https://woo.com/product/p7/"
    assert product["variants"] == [{"id": 7, "title": "Default Title", "price": "54.99", "available": True}]
    assert match.is_pokemon(product)  # from the category


def test_woocommerce_reader_pages_newest_first(monkeypatch):
    monkeypatch.setattr(readers, "WOO_PAGE_SIZE", 2)
    pages = {
        "1": [_woo_item(1, "a"), _woo_item(2, "b")],
        "2": [_woo_item(3, "c", in_stock=False)],
    }

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params["orderby"] == "date" and request.url.params["order"] == "desc"
        return httpx.Response(200, json=pages[request.url.params["page"]])

    client = httpx.Client(transport=httpx.MockTransport(handler))
    reader = readers.WooCommerceReader(WOO, client, min_interval_s=0, sleep=lambda _: None)
    result = reader.fetch(max_pages=5)
    assert [p["id"] for p in result.products] == [1, 2, 3] and result.pages_fetched == 2
    assert result.products[2]["variants"][0]["available"] is False


def _page(name: str, price: str, availability: str) -> str:
    data = {"@context": "https://schema.org", "@type": "Product", "name": name, "brand": {"@type": "Brand", "name": "Pokémon"},
            "offers": {"@type": "Offer", "price": price, "priceCurrency": "USD", "availability": f"https://schema.org/{availability}"}}
    return f'<html><script type="application/ld+json">{json.dumps(data)}</script></html>'


SITEMAP_INDEX = """<?xml version="1.0"?><sitemapindex>
<sitemap><loc>https://wix.com/blog-posts-sitemap.xml</loc></sitemap>
<sitemap><loc>https://wix.com/store-products-sitemap.xml</loc></sitemap></sitemapindex>"""
PRODUCT_SITEMAP = """<urlset>
<url><loc>https://wix.com/product-page/pokemon-delta-reign-etb</loc><lastmod>2026-10-23</lastmod></url>
<url><loc>https://wix.com/product-page/prismatic-evolutions-booster-bundle</loc><lastmod>2026-10-24</lastmod></url>
<url><loc>https://wix.com/product-page/star-wars-unlimited-box</loc><lastmod>2026-10-25</lastmod></url>
<url><loc>https://wix.com/about</loc></url></urlset>"""


def test_sitemap_reader_reads_pokemon_product_pages_newest_first(monkeypatch):
    client, seen = _client({
        "/sitemap.xml": SITEMAP_INDEX,
        "/store-products-sitemap.xml": PRODUCT_SITEMAP,
        "/product-page/pokemon-delta-reign-etb": _page("Pokémon TCG: Delta Reign Elite Trainer Box", "49.99", "PreOrder"),
        "/product-page/prismatic-evolutions-booster-bundle": _page("Prismatic Evolutions Booster Bundle", "39.99", "OutOfStock"),
    })
    reader = readers.SitemapReader(WIX, client, match_words={"prismatic evolutions"}, min_interval_s=0, sleep=lambda _: None)
    result = reader.fetch(max_pages=40)
    assert [p["title"] for p in result.products] == [
        "Prismatic Evolutions Booster Bundle", "Pokémon TCG: Delta Reign Elite Trainer Box",
    ]
    bundle, etb = result.products
    assert (etb["variants"][0]["price"], etb["variants"][0]["available"]) == ("49.99", True)  # pre-order counts
    assert bundle["variants"][0]["available"] is False
    assert etb["url"] == "https://wix.com/product-page/pokemon-delta-reign-etb"
    assert etb["id"] == readers.stable_id(etb["url"])
    assert "/product-page/star-wars-unlimited-box" not in seen  # not a Pokémon page
    # A discovery read fetches only the newest pages.
    monkeypatch.setattr(readers, "SITEMAP_DISCOVERY_PAGES", 1)
    assert [p["title"] for p in reader.fetch(max_pages=1).products] == ["Prismatic Evolutions Booster Bundle"]


def test_ld_product_handles_aggregate_offers_and_missing_data():
    page = ('<script type="application/ld+json">{"@graph": [{"@type": "WebPage"}, {"@type": ["Product"], "name": "X",'
            '"offers": {"@type": "AggregateOffer", "lowPrice": "$1,049.50", "availability": "InStock"}}]}</script>')
    product = readers.ld_product(page, "https://a.com/product/x")
    assert product["variants"][0]["price"] == "1049.50" and product["variants"][0]["available"] is True
    assert readers.ld_product("<html>no data</html>", "https://a.com/product/y") is None


def test_reader_factory_picks_by_platform():
    catalog = match.Catalog.from_rows([(1, "ME06: Delta Reign")], [(11, 1, "Delta Reign Elite Trainer Box", "etb", None)])
    make = collect.reader_factory(catalog)
    client = httpx.Client()
    assert type(make(WOO, client)) is readers.WooCommerceReader
    wix_reader = make(WIX, client)
    assert type(wix_reader) is readers.SitemapReader and "delta reign" in wix_reader.match_words
    shopify = registry.Store(store_id="s", name="S", domain="s.com", tier="explore")
    assert type(make(shopify, client)).__name__ == "StoreReader"


@pytest.mark.parametrize("platform", ["woocommerce", "wix", "sitemap_jsonld"])
def test_new_platforms_are_polled_without_collection_checks(connection, platform):
    from .conftest import NOW

    store = registry.Store(store_id="x", name="X", domain="x.com", tier="explore", platform=platform)
    assert store.is_polled
    collect.sync_registry(connection, [store])
    (plan_item,) = collect.plan(connection, [store], NOW)
    assert plan_item.is_collection_check_due is False and plan_item.is_full_sweep is True
