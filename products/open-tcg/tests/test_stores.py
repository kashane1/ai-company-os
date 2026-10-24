from __future__ import annotations

import datetime as dt
from pathlib import Path

import httpx
import pytest

from radar import watchlist
from radar.catalog import classify
from radar.stores import collect, match, registry, report
from radar.stores.shopify import StoreFetchError, StoreReader

from .conftest import NOW

GROUPS = {
    24831: "ME06: Delta Reign",
    24269: "SV10: Destined Rivals",
    23821: "SV: Prismatic Evolutions",
    24380: "ME01: Mega Evolution",
    24722: "ME: 30th Celebration",
}
PRODUCTS = [
    (1, 24831, "Delta Reign Elite Trainer Box"),
    (2, 24831, "Delta Reign Pokemon Center Elite Trainer Box (Exclusive)"),
    (3, 24831, "Delta Reign Booster Box"),
    (4, 24831, "Delta Reign Booster Bundle"),
    (5, 24831, "Delta Reign Booster Pack"),
    (6, 24831, "Delta Reign Booster Pack Art Bundle [Set of 4]"),
    (7, 24831, "Delta Reign Single Pack Blister [Spritzee]"),
    (8, 24831, "Delta Reign Single Pack Blister (Target Exclusive) [Keldeo]"),
    (9, 24831, "Delta Reign 3 Pack Blister [Seel]"),
    (10, 24831, "Delta Reign Elite Trainer Box Case"),
    (11, 24269, "Destined Rivals Elite Trainer Box"),
    (12, 23821, "Prismatic Evolutions Booster Bundle"),
    (13, 24380, "Mega Evolution Booster Box"),
    (14, 24722, "30th Celebration Elite Trainer Box"),
]
STORE = registry.Store(store_id="test_store", name="Test Store", domain="teststore.com", tier="first_pass")


@pytest.fixture()
def catalog_connection(connection):
    for group_id, name in GROUPS.items():
        connection.execute("INSERT INTO catalog_groups (group_id, name) VALUES (?, ?)", (group_id, name))
    for product_id, group_id, name in PRODUCTS:
        connection.execute(
            """
            INSERT INTO products (product_id, group_id, name, product_type, exclusive_retailer, first_seen_at, updated_at)
            VALUES (?, ?, ?, ?, ?, '2026-10-01', '2026-10-01')
            """,
            (product_id, group_id, name, classify.product_type(name), classify.exclusive_retailer(name)),
        )
    connection.commit()
    return connection


@pytest.fixture()
def catalog(catalog_connection):
    return match.Catalog.from_db(catalog_connection)


# Titles below are real store listing titles seen on 2026-10-23.
@pytest.mark.parametrize(
    ("title", "product_id"),
    [
        ("Pokémon TCG: Mega Evolution – Delta Reign Pokémon Center Elite Trainer Box", 2),
        ("(Pre-Order) Pokemon Delta Reign Booster Box", 3),
        ("(Pre-Order) Pokemon Delta Reign Booster Bundle", 4),
        ("Delta Reign Booster Display", 3),
        ("Pokemon Delta Reign ETB", 1),
        ("Pokemon TCG: Scarlet & Violet Destined Rivals Elite Trainer Box", 11),
        ("Destined Rivals Pokemon Elite Trainer Box - ETB", 11),
        ("Prismatic Evolutions - Booster Bundle (Pokemon TCG)", 12),
        ("Pokémon TCG: 30th Celebration (Anniversary) Elite Trainer Box", 14),
        ("Delta Reign Booster Pack Art Bundle [Set of 4]", 6),
        ("Delta Reign Booster Pack", 5),
        ("Mega Evolution: Delta Reign - Single Pack Blister [Spritzee]", 7),
    ],
)
def test_exact_matches(catalog, title, product_id):
    result = match.match_listing(catalog, title)
    assert (result.status, result.catalog_product_id) == ("exact", product_id)


@pytest.mark.parametrize(
    ("title", "status", "reason"),
    [
        ("Pokémon TCG: Japanese Scarlet & Violet Glory of Team Rocket", "excluded", "non_english"),
        ("Tornadus #210 ETB Promo (Sealed) - White Flare", "excluded", "single_card"),
        ("Pikachu ETB Promo", "excluded", "promo_card"),
        ("Trick or Trade BOOster Bundle 2023: 069/185 Duskull", "excluded", "single_card"),
        ("PSA 10 Delta Reign Elite Trainer Box", "excluded", "graded"),
        ("Delta Reign Elite Trainer Box Sleeves", "excluded", "accessory"),
        ("Delta Reign Booster Pack x 50 (LIVE)", "ambiguous", "quantity_unclear"),
        ("Pokemon Lost Origin Elite Trainer Box", "unmatched", "set_not_in_catalog"),
        ("Pokémon Mega Evolution Phantasmal Flames Booster Box", "ambiguous", "era_name_only"),
        ("Delta Reign 3 Pack Blister", "ambiguous", "variant_unclear"),
        ("Delta Reign Mystery Repack", "excluded", "repack"),
        ("Delta Reign Playmat Bundle", "excluded", "accessory"),
    ],
)
def test_non_exact_matches(catalog, title, status, reason):
    result = match.match_listing(catalog, title)
    assert (result.status, result.reason, result.catalog_product_id) == (status, reason, None)


def test_retailer_exclusive_needs_retailer_named(catalog):
    assert match.match_listing(catalog, "Delta Reign Single Pack Blister [Keldeo]").status == "ambiguous"
    named = match.match_listing(catalog, "Delta Reign Single Pack Blister Target Exclusive [Keldeo]")
    assert named.catalog_product_id == 8


def test_variant_names_the_form_for_multi_form_listings(catalog):
    # Real Pokémon Plug listing shape; the title alone reads as a case.
    box =match.match_listing(catalog, "Delta Reign Booster Boxes & Cases", "1 Sealed Booster Box (36 Packs) (Order 6 for Sealed Case)")
    assert box.catalog_product_id == 3


def test_variant_title_is_part_of_the_listing(catalog):
    result = match.match_listing(catalog, "Pokemon Delta Reign", "Elite Trainer Box")
    assert result.catalog_product_id == 1
    assert match.match_listing(catalog, "Delta Reign Elite Trainer Box", "Default Title").catalog_product_id == 1


def test_registry_loads_and_rejects_bad_rows(tmp_path: Path):
    path = tmp_path / "stores.toml"
    path.write_text('[[store]]\nstore_id = "a"\nname = "A"\ndomain = "a.com"\ntier = "first_pass"\n')
    assert registry.load(path)[0].base_url == "https://a.com"
    path.write_text(path.read_text() + '[[store]]\nstore_id = "b"\nname = "B"\ndomain = "a.com"\ntier = "explore"\n')
    with pytest.raises(ValueError, match="duplicate domain"):
        registry.load(path)
    path.write_text('[[store]]\nstore_id = "a"\nname = "A"\ndomain = "https://a.com/"\ntier = "first_pass"\n')
    with pytest.raises(ValueError, match="bare host"):
        registry.load(path)


def test_shipped_registry_is_valid():
    stores = registry.load()
    assert len(stores) == 20
    assert all(store.platform == "shopify_json" for store in stores)


def _product(
    product_id: int, title: str, *, price: str = "49.99", available: bool = True, vendor: str = "Pokemon"
) -> dict:
    return {
        "id": product_id,
        "title": title,
        "handle": f"p-{product_id}",
        "vendor": vendor,
        "product_type": "Sealed",
        "tags": [],
        "created_at": "2026-10-20T10:00:00-04:00",
        "variants": [{"id": product_id * 10, "title": "Default Title", "price": price, "available": available}],
    }


def _reader(handler, store: registry.Store = STORE) -> StoreReader:
    client = httpx.Client(transport=httpx.MockTransport(handler), follow_redirects=True)
    return StoreReader(store, client, min_interval_s=0, sleep=lambda _: None)


def test_reader_pages_until_short_page(monkeypatch):
    monkeypatch.setattr("radar.stores.shopify.STORE_PAGE_SIZE", 2)
    pages = {"1": [_product(1, "a"), _product(2, "b")], "2": [_product(3, "c")]}
    seen = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request.url.params["page"])
        return httpx.Response(200, json={"products": pages[request.url.params["page"]]})

    result = _reader(handler).fetch(max_pages=5)
    assert (len(result.products), result.pages_fetched, result.is_truncated, seen) == (3, 2, False, ["1", "2"])


def test_reader_marks_truncated_sweep(monkeypatch):
    monkeypatch.setattr("radar.stores.shopify.STORE_PAGE_SIZE", 1)
    result = _reader(lambda request: httpx.Response(200, json={"products": [_product(1, "a")]})).fetch(max_pages=3)
    assert (result.pages_fetched, result.is_truncated) == (3, True)


def test_reader_rejects_off_domain_redirect():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.host == "teststore.com":
            return httpx.Response(301, headers={"Location": "https://lookalike-store.com/products.json"})
        return httpx.Response(200, json={"products": []})

    with pytest.raises(StoreFetchError, match="redirected off"):
        _reader(handler).products_page(1)


def test_reader_accepts_www_and_reads_robots():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.host == "teststore.com":
            return httpx.Response(301, headers={"Location": f"https://www.teststore.com{request.url.path}"})
        return httpx.Response(200, text="User-agent: *\nDisallow: /products.json\n")

    assert _reader(handler).robots_allows_products() is False


def test_reader_rejects_non_json():
    with pytest.raises(StoreFetchError, match="not Shopify product JSON"):
        _reader(lambda request: httpx.Response(200, text="<html>")).products_page(1)


class FakeReader:
    """Stands in for StoreReader: serves whatever `catalog_pages` holds."""

    responses: list = []

    def __init__(self, store, client):
        self.store = store

    def robots_allows_products(self) -> bool:
        return True

    def fetch(self, *, max_pages: int):
        response = FakeReader.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        from radar.stores.shopify import FetchResult

        return FetchResult(products=response, pages_fetched=1)


def _collect(connection, now: dt.datetime, *responses):
    FakeReader.responses = list(responses)
    return collect.collect(
        connection,
        now=now,
        stores=[STORE],
        make_reader=FakeReader,
        client_factory=lambda: httpx.Client(),
        workers=1,
    )


def _listing(connection, variant_id: int):
    return connection.execute(
        "SELECT * FROM store_listings WHERE store_id = 'test_store' AND variant_id = ?", (variant_id,)
    ).fetchone()


def test_first_sweep_is_silent_baseline_then_changes_are_recorded(catalog_connection):
    connection = catalog_connection
    first = _collect(connection, NOW, [_product(1, "Delta Reign Elite Trainer Box", price="129.99"), _product(2, "Magic Booster", vendor="Wizards")])
    assert (first.full_sweeps, first.listings_new, first.listings_changed) == (1, 0, 0)
    row = _listing(connection, 10)
    assert (row["is_baseline"], row["match_status"], row["catalog_product_id"], row["price_cents"]) == (1, "exact", 1, 12999)
    assert _listing(connection, 20) is None  # not Pokémon, not kept
    _collect(connection, NOW + dt.timedelta(minutes=5), [_product(4, "Pikachu 069/185 Delta Reign")])
    assert _listing(connection, 40) is None  # a single card, excluded, not kept

    later = NOW + dt.timedelta(minutes=15)
    second = _collect(
        connection,
        later,
        [
            _product(1, "Delta Reign Elite Trainer Box", price="49.99"),
            _product(3, "Delta Reign Booster Bundle", price="29.99"),
        ],
    )
    assert (second.full_sweeps, second.listings_new, second.listings_changed) == (0, 1, 1)
    assert _listing(connection, 30)["is_baseline"] == 0
    changes = connection.execute(
        "SELECT variant_id, change, price_cents FROM listing_snapshots ORDER BY observed_at, variant_id"
    ).fetchall()
    assert [tuple(change) for change in changes] == [
        (10, "first_seen", 12999),
        (10, "price", 4999),
        (30, "first_seen", 2999),
    ]


def test_failed_fetch_leaves_listings_unknown_not_sold_out(catalog_connection):
    connection = catalog_connection
    _collect(connection, NOW, [_product(1, "Delta Reign Elite Trainer Box")])
    summary = _collect(connection, NOW + dt.timedelta(minutes=15), StoreFetchError("HTTP 503"))
    assert (summary.stores_failed, summary.failures) == (1, ["test_store: HTTP 503"])
    assert _listing(connection, 10)["is_available"] == 1
    store = connection.execute("SELECT * FROM stores WHERE store_id = 'test_store'").fetchone()
    assert (store["consecutive_failures"], store["last_error"]) == (1, "HTTP 503")


def test_full_sweep_is_daily(catalog_connection):
    connection = catalog_connection
    _collect(connection, NOW, [])
    plans = collect.plan(connection, [STORE], NOW + dt.timedelta(hours=1))
    assert plans[0].is_full_sweep is False
    plans = collect.plan(connection, [STORE], NOW + dt.timedelta(hours=24))
    assert plans[0].is_full_sweep is True


def test_report_shows_offers_under_alert_at_and_stock_spans(catalog_connection):
    connection = catalog_connection
    connection.execute("INSERT INTO price_points (product_id, day, market_price) VALUES (1, '2026-09-25', 80.0)")
    _collect(connection, NOW, [])
    _collect(connection, NOW + dt.timedelta(minutes=15), [_product(1, "Delta Reign ETB", price="49.99")])
    _collect(connection, NOW + dt.timedelta(minutes=45), [_product(1, "Delta Reign ETB", price="49.99", available=False)])
    _collect(connection, NOW + dt.timedelta(minutes=60), [_product(1, "Delta Reign ETB", price="49.99")])

    catalog = match.Catalog.from_db(connection)
    items = [watchlist.WatchItem(name="Pokemon Delta Reign Elite Trainer Box", alert_at=55.0, retailers=(), auto_buy=False)]
    thresholds = report.watch_thresholds(catalog, items)
    assert thresholds == {1: 5500}
    offers = report.offers(connection, thresholds)
    assert [(o.price_cents, o.market_cents, o.is_at_or_below_alert_at) for o in offers] == [(4999, 8000, True)]
    spans = report.in_stock_spans(connection, NOW)
    assert spans == [("Test Store", "Delta Reign Elite Trainer Box", 30.0)]
    text = report.render(connection, now=NOW + dt.timedelta(hours=1))
    assert "Test Store" in text and "0.62x" in text
