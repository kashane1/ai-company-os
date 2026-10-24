from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

import httpx
import pytest

from radar import watchlist
from radar.catalog import classify
from radar.stores import collect, collections, match, reference, registry, report, review
from radar.stores.shopify import StoreFetchError, StoreReader

from .conftest import FIXTURES, NOW

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
        connection.execute("INSERT INTO ref_groups (group_id, name) VALUES (?, ?)", (group_id, name))
    for product_id, group_id, name in PRODUCTS:
        connection.execute(
            """
            INSERT INTO ref_products (product_id, group_id, name, product_type, exclusive_retailer, updated_at)
            VALUES (?, ?, ?, ?, ?, '2026-10-01')
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
    assert len(stores) == 109
    polled = [store for store in stores if store.is_polled]
    assert len(polled) == 85  # 86 open Shopify stores, minus parked GG Legends
    pilot = [store for store in polled if store.discovery_minutes == 15]
    assert len(pilot) == 20


def test_registry_cadence_and_not_polled_reasons(tmp_path: Path):
    path = tmp_path / "stores.toml"
    path.write_text(
        '[[store]]\nstore_id = "a"\nname = "A"\ndomain = "a.com"\ntier = "explore"\n'
        '[[store]]\nstore_id = "b"\nname = "B"\ndomain = "b.com"\ntier = "explore"\n'
        'discovery_every_minutes = 15\n'
        '[[store]]\nstore_id = "c"\nname = "C"\ndomain = "c.com"\ntier = "backup"\nplatform = "challenge"\n'
        'newsletter = true\n'
        '[[store]]\nstore_id = "d"\nname = "D"\ndomain = "d.com"\ntier = "parked"\n'
    )
    a, b, c, d = registry.load(path)
    assert (a.discovery_minutes, b.discovery_minutes) == (60, 15)
    assert (c.is_polled, c.not_polled_reason, c.has_newsletter) == (False, "no adapter for challenge", True)
    assert (d.is_polled, d.not_polled_reason) == (False, "parked")
    path.write_text('[[store]]\nstore_id = "a"\nname = "A"\ndomain = "a.com"\ntier = "explore"\ndiscovery_every_minutes = 1\n')
    with pytest.raises(ValueError, match="at least 5"):
        registry.load(path)


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
    with pytest.raises(StoreFetchError, match="not Shopify products JSON"):
        _reader(lambda request: httpx.Response(200, text="<html>")).products_page(1)


class FakeReader:
    """Stands in for StoreReader.

    Catalog reads pop `responses` in order (a list of products or an exception).
    `collection_list` is what /collections.json returns, and `collection_products`
    maps a handle to its products (or an exception).
    """

    responses: list = []
    collection_list: list = []
    collection_products: dict = {}
    calls: list = []

    def __init__(self, store, client):
        self.store = store

    def robots_allows_products(self) -> bool:
        return True

    def robots_allows(self, path: str) -> bool:
        return True

    def collections(self, *, max_pages: int):
        FakeReader.calls.append("collections")
        return FakeReader.collection_list

    def _products(self, collection):
        if collection is None:
            response = FakeReader.responses.pop(0)
        else:
            response = FakeReader.collection_products[collection]
        if isinstance(response, Exception):
            raise response
        return response

    def products_page(self, page: int, collection: str | None = None):
        FakeReader.calls.append(f"page:{collection}")
        return self._products(collection)

    def fetch(self, *, max_pages: int, collection: str | None = None):
        from radar.stores.shopify import FetchResult

        FakeReader.calls.append(f"fetch:{collection}:{max_pages}")
        return FetchResult(products=self._products(collection), pages_fetched=1)


def _collect(connection, now: dt.datetime, *responses, stores=None, collection_list=(), collection_products=None):
    FakeReader.responses = list(responses)
    FakeReader.collection_list = list(collection_list)
    FakeReader.collection_products = collection_products or {}
    FakeReader.calls = []
    return collect.collect(
        connection,
        now=now,
        stores=stores or [STORE],
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


def test_discovery_follows_tier_cadence(catalog_connection):
    connection = catalog_connection
    explore = registry.Store(store_id="test_store", name="Test Store", domain="teststore.com", tier="explore")
    _collect(connection, NOW, [], stores=[explore])
    assert collect.plan(connection, [explore], NOW + dt.timedelta(minutes=30)) == []
    plans = collect.plan(connection, [explore], NOW + dt.timedelta(minutes=59))
    assert [(p.is_discovery_due, p.is_full_sweep) for p in plans] == [(True, False)]


def test_catalog_sweeps_are_staggered_but_collection_sweeps_are_not(catalog_connection):
    stores = [
        registry.Store(store_id=f"s{n}", name=f"S{n}", domain=f"s{n}.com", tier="first_pass") for n in range(3)
    ]
    FakeReader.responses = [[] for _ in range(5)]
    FakeReader.collection_list = []
    FakeReader.collection_products = {}
    FakeReader.calls = []
    summary = collect.collect(
        catalog_connection, now=NOW, stores=stores, make_reader=FakeReader,
        client_factory=lambda: httpx.Client(), workers=1, max_catalog_sweeps=2,
    )
    assert (summary.full_sweeps, summary.catalog_sweeps_deferred) == (2, 1)
    assert FakeReader.calls.count("fetch:None:40") == 2
    deferred = catalog_connection.execute("SELECT * FROM stores WHERE store_id = 's2'").fetchone()
    assert (deferred["baseline_at"], deferred["last_discovery_at"] is not None) == (None, True)

    # A store whose collection check selects a collection sweeps it even with no budget left.
    budget = collect.CatalogSweepBudget(0)
    collect.sync_registry(catalog_connection, [STORE])
    plan_item = collect.plan(catalog_connection, [STORE], NOW)[0]
    FakeReader.responses = [[]]
    FakeReader.collection_list = [{"handle": "pokemon-sealed", "title": "Pokemon Sealed", "products_count": 3}]
    FakeReader.collection_products = {"pokemon-sealed": SEALED_COLLECTION}
    outcome = collect.fetch(plan_item, FakeReader(STORE, None), match.Catalog.from_db(catalog_connection), budget)
    assert (outcome.sweep_mode, outcome.is_catalog_sweep_deferred) == ("collections", False)


SEALED_COLLECTION = [
    _product(1, "Delta Reign Elite Trainer Box"),
    _product(3, "Delta Reign Booster Bundle"),
    _product(4, "Lost Origin Elite Trainer Box"),
]


def test_collection_candidates_skip_singles_titles_but_not_mislabeled_handles():
    found = collections.candidates(
        [
            {"handle": "pokemon-singles", "title": "Pokemon Singles", "products_count": 1783},
            {"handle": "sealed-151-pokemon-copy", "title": "Sealed Paradox Rift Pokemon", "products_count": 4},
            {"handle": "pokemon-cards", "title": "Pokemon Sealed", "products_count": 92},
            {"handle": "pokemon", "title": "Pokemon", "products_count": 79},
            {"handle": "mtg-sealed", "title": "Magic Sealed", "products_count": 40},
            {"handle": "japanese-pokemon", "title": "Japanese Pokemon Boxes", "products_count": 20},
            {"handle": "pokemon-empty", "title": "Pokemon Boxes", "products_count": 0},
            {"handle": "lionz-pokemon-model", "title": "Lionz - Pokemon Model", "products_count": 46},
            {"handle": "nanoblocks-pokemon", "title": "Nanoblocks  Pokémon", "products_count": 66},
        ]
    )
    assert [c["handle"] for c in found] == ["pokemon-cards", "sealed-151-pokemon-copy", "pokemon"]


def test_collection_sample_selects_mostly_sealed_pages(catalog):
    sealed = collections.sample("pokemon-sealed", "Pokemon Sealed", SEALED_COLLECTION, catalog)
    assert (sealed.sampled_count, sealed.sealed_count, sealed.is_strong) == (3, 3, True)
    singles = collections.sample(
        "pokemon", "Pokemon", [_product(7, "Pikachu 069/185"), _product(8, "Eevee 070/185"), _product(1, "Delta Reign ETB")],
        catalog,
    )
    assert (singles.sealed_count, singles.is_eligible) == (1, False)
    assert collections.sample("x", "X", [], catalog).is_eligible is False
    kits = collections.sample(
        "pokemon-models", "Pokemon Models", [_product(5, "Pokemon Model Kit Pikachu"), _product(6, "Pokemon Plush Eevee")], catalog
    )
    assert (kits.sealed_count, kits.is_eligible) == (0, False)


def test_broad_collections_only_when_no_strong_one():
    def sample(handle, sealed, sampled):
        return collections.CollectionSample(handle, handle, sampled, sealed)

    with_strong = collections.CollectionCheck(samples=[sample("pokemon", 127, 250), sample("pokemon-sealed", 237, 250)])
    assert with_strong.selected_handles == ["pokemon-sealed"]
    only_broad = collections.CollectionCheck(samples=[sample("pokemon", 152, 222), sample("misc", 2, 10)])
    assert only_broad.selected_handles == ["pokemon"]


def test_full_sweep_reads_selected_collections_not_the_catalog(catalog_connection):
    connection = catalog_connection
    summary = _collect(
        connection,
        NOW,
        [_product(9, "Delta Reign Booster Box")],  # the newest catalog page
        collection_list=[{"handle": "pokemon-sealed", "title": "Pokemon Sealed", "products_count": 3}],
        collection_products={"pokemon-sealed": SEALED_COLLECTION},
    )
    assert FakeReader.calls == [
        "collections",
        "page:pokemon-sealed",
        "fetch:pokemon-sealed:40",
        "fetch:None:1",
    ]
    assert (summary.full_sweeps, summary.collection_checks) == (1, 1)
    kept = {row["variant_id"] for row in connection.execute("SELECT variant_id FROM store_listings")}
    assert kept == {10, 30, 40, 90}
    check = connection.execute("SELECT * FROM store_collection_checks").fetchone()
    assert (check["candidate_count"], check["selected_count"], check["error"]) == (1, 1, None)


def test_broken_collection_falls_back_to_catalog_and_rechecks(catalog_connection):
    connection = catalog_connection
    listing = {"handle": "pokemon-sealed", "title": "Pokemon Sealed", "products_count": 3}
    _collect(
        connection, NOW, [], collection_list=[listing], collection_products={"pokemon-sealed": SEALED_COLLECTION}
    )
    later = NOW + dt.timedelta(hours=24)
    summary = _collect(
        connection,
        later,
        [_product(1, "Delta Reign Elite Trainer Box")],
        collection_products={"pokemon-sealed": StoreFetchError("HTTP 404")},
    )
    assert FakeReader.calls == ["fetch:pokemon-sealed:40", "fetch:None:40"]
    assert (summary.stores_failed, summary.full_sweeps) == (0, 1)
    assert connection.execute("SELECT COUNT(*) FROM store_collection_checks").fetchone()[0] == 0
    plans = collect.plan(connection, [STORE], later + dt.timedelta(minutes=15))
    assert plans[0].is_collection_check_due is True


def test_store_health_line(catalog_connection):
    connection = catalog_connection
    blocked = registry.Store(store_id="blocked", name="Blocked", domain="blocked.com", tier="backup", platform="challenge")
    _collect(connection, NOW, [])
    line = report.store_health(connection, [STORE, blocked])
    assert line == "stores: 1 ok, 0 failing, 0 not yet read; not polled: 1 no adapter for challenge"


def test_report_shows_offers_under_alert_at_and_stock_spans(catalog_connection):
    connection = catalog_connection
    connection.execute("INSERT INTO ref_price_points (product_id, day, market_price) VALUES (1, '2026-09-25', 80.0)")
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


# --- P2: reference catalog, matcher upgrades, review decisions ----------------

P2_GROUPS = {
    1: "SV: Scarlet & Violet 151",
    2: "ME01: Mega Evolution",
    3: "Miscellaneous Cards & Products",
    4: "Arceus",
    5: "ME04: Chaos Rising",
    6: "SV01: Scarlet & Violet Base Set",
}
P2_PRODUCTS = [
    (101, 1, "151 Booster Bundle"),
    (102, 1, "151 Elite Trainer Box"),
    (103, 1, "151 Booster Pack"),
    (201, 2, "Mega Evolution Elite Trainer Box [Mega Lucario]"),
    (202, 2, "Mega Evolution Elite Trainer Box [Mega Gardevoir]"),
    (203, 2, "Mega Evolution Booster Box"),
    (301, 3, "Charizard ex Premium Collection"),
    (302, 3, "Charizard ex Super-Premium Collection"),
    (303, 3, "Arceus V Figure Collection"),
    (401, 4, "Arceus Booster Pack"),
    (501, 5, "Mega Greninja ex Premium Collection"),
    (502, 5, "Chaos Rising 3-Pack Blister [Charmeleon]"),
    (503, 5, "Chaos Rising Booster Box Case"),
    (504, 5, "Chaos Rising Booster Pack"),
    (505, 5, "Chaos Rising Elite Trainer Box"),
    (506, 5, "Chaos Rising Elite Trainer Box Case"),
    (601, 6, "Scarlet & Violet Booster Pack"),
]


@pytest.fixture()
def p2_catalog():
    rows = [(pid, gid, name, classify.product_type(name), classify.exclusive_retailer(name)) for pid, gid, name in P2_PRODUCTS]
    return match.Catalog.from_rows(list(P2_GROUPS.items()), rows)


@pytest.mark.parametrize(
    ("title", "variant", "expected"),
    [
        ("Pokemon 151 Booster Bundle", None, ("exact", 101)),  # alias without the era
        ("Pokémon 151 Booster Pack", None, ("exact", 103)),  # "151" is a set, not a pack count
        ("Pokémon 151 Booster Pack x 10", None, ("ambiguous", None)),
        ("Mega Evolution Elite Trainer Box - Lucario", None, ("exact", 201)),  # era name = base set
        ("Pokémon Mega Evolution Phantasmal Flames Booster Box", None, ("ambiguous", None)),  # unexplained set words
        ("Pokémon Mega Greninja ex Premium Collection Box", None, ("exact", 501)),  # no set named
        ("Pokemon Charizard ex Premium Collection", None, ("exact", 301)),
        ("Pokemon TCG: Charizard ex Super Premium Collection", None, ("exact", 302)),
        ("Pokemon TCG Arceus V Figure Collection Box", None, ("exact", 303)),  # "Arceus" set has no collection
        ("Pokemon: Scarlet & Violet Booster Pack", None, ("exact", 601)),
        ("Chaos Rising Elite Trainer Box", "Factory Sealed Case of 10 Elite Trainer Boxes (FREE Double Box Shipping)", ("exact", 506)),
        ("Chaos Rising 3-Pack Booster Blister", "Factory Sealed Case of 24x 3-Pack Blisters (FREE Double Box Shipping)", ("unmatched", None)),
        ("Pokémon TCG: Chaos Rising: Booster Pack: 36 Loose Packs", None, ("ambiguous", None)),
        ("Pokemon Chaos Rising Booster Box Case (6 boxes)", None, ("exact", 503)),
        ("Chaos Rising Elite Trainer Box [DAMAGED]", None, ("ambiguous", None)),
        ("Pokémon Mega Evolutions ME4 - Chaos Rising Elite Trainer Box", None, ("exact", 505)),
        ("Chaos Rising Elite Trainer Box", "Near Mint / English / New", ("exact", 505)),
        ("Pokemon 30th Celebration Battle Deck RELEASE DATE 10/30/2026", None, ("unmatched", None)),  # date isn't a card number
        ("Shining Celebi 106 - Holofoil ME 30th Celebration Classic Collection", "Lightly Played", ("excluded", None)),
        ("Mega Evolution: Ninja Spinner - Booster Box (J)", None, ("excluded", None)),
    ],
)
def test_p2_matching(p2_catalog, title, variant, expected):
    result = match.match_listing(p2_catalog, title, variant)
    assert (result.status, result.catalog_product_id) == expected


def test_candidates_rank_by_shared_words(p2_catalog):
    names = [p.name for p in match.candidates(p2_catalog, "Mega Evolution Elite Trainer Box")]
    assert names[:2] == ["Mega Evolution Elite Trainer Box [Mega Gardevoir]", "Mega Evolution Elite Trainer Box [Mega Lucario]"]


class FakeReferenceClient:
    def __init__(self):
        self.groups = [
            {"groupId": 7, "name": "SWSH07: Evolving Skies", "publishedOn": "2021-08-27T00:00:00", "modifiedOn": "a"},
            {"groupId": 8, "name": "Jumbo Cards", "publishedOn": "2015-01-01T00:00:00", "modifiedOn": "b"},
        ]
        self.calls = []

    def fetch_groups(self):
        return self.groups

    def fetch_products(self, group_id):
        self.calls.append(("products", group_id))
        if group_id == 7:
            return [
                {"productId": 70, "name": "Evolving Skies Booster Box", "extendedData": []},
                {"productId": 71, "name": "Umbreon VMAX", "extendedData": [{"name": "Number", "value": "215/203"}, {"name": "Rarity", "value": "Secret Rare"}]},
            ]
        return []

    def fetch_prices(self, group_id):
        self.calls.append(("prices", group_id))
        return [{"productId": 70, "marketPrice": 1200.0, "lowPrice": 1100.0}]


def test_reference_sync_is_silent_and_incremental(connection):
    client = FakeReferenceClient()
    result = reference.sync_reference(connection, client, now=NOW)
    assert (result.groups_seen, result.groups_refetched, result.products_upserted, result.price_groups) == (2, 2, 1, 1)
    assert [r["name"] for r in connection.execute("SELECT name FROM ref_products")] == ["Evolving Skies Booster Box"]
    assert connection.execute("SELECT COUNT(*) FROM calendar_events").fetchone()[0] == 0
    assert connection.execute("SELECT COUNT(*) FROM catalog_groups").fetchone()[0] == 0
    assert connection.execute("SELECT COUNT(*) FROM products").fetchone()[0] == 0
    client.calls = []
    reference.sync_reference(connection, client, now=NOW + dt.timedelta(days=1))
    # Unchanged groups aren't refetched, and a set over three years old reprices weekly.
    assert client.calls == []
    reference.sync_reference(connection, client, now=NOW + dt.timedelta(days=7))
    assert client.calls == [("prices", 7)]


def test_decisions_override_matching_and_survive_rematch(catalog_connection):
    connection = catalog_connection
    _collect(connection, NOW, [_product(1, "Delta Reign 3 Pack Blister"), _product(2, "Delta Reign Stickers Pokemon")])
    assert _listing(connection, 10)["match_status"] == "ambiguous"
    with pytest.raises(review.DecisionError, match="no reference product"):
        review.decide(connection, store_id="test_store", variant_id=10, product="999", decided_by="claude", now=NOW)
    review.decide(connection, store_id="test_store", variant_id=10, product="9", decided_by="claude", now=NOW, note="art is Seel")
    review.decide(connection, store_id="test_store", variant_id=20, product="reject", decided_by="founder", now=NOW)
    assert (_listing(connection, 10)["match_status"], _listing(connection, 10)["catalog_product_id"]) == ("confirmed", 9)
    assert (_listing(connection, 20)["match_status"], _listing(connection, 20)["match_reason"]) == ("excluded", "reviewed")

    collect.rematch(connection)
    _collect(connection, NOW + dt.timedelta(minutes=15), [_product(1, "Delta Reign 3 Pack Blister"), _product(2, "Delta Reign Stickers Pokemon")])
    assert _listing(connection, 10)["match_status"] == "confirmed"
    assert _listing(connection, 20)["match_reason"] == "reviewed"
    assert review.queue(connection) == []


def test_same_title_decision_covers_other_stores(catalog_connection):
    connection = catalog_connection
    other = registry.Store(store_id="other_store", name="Other", domain="other.com", tier="first_pass")
    _collect(
        connection,
        NOW,
        [_product(1, "Delta Reign 3 Pack Blister")],
        [_product(5, "Delta Reign: 3 Pack Blister"), _product(6, "Delta Reign 3-Pack Blister")],
        stores=[STORE, other],
    )
    items = review.queue(connection)
    # "Delta Reign: 3 Pack Blister" folds to the same title; "3-Pack" doesn't.
    assert sorted((i.listing_count, i.reason) for i in items) == [(1, "variant_unclear"), (2, "variant_unclear")]
    count = review.decide(
        connection, store_id="test_store", variant_id=10, product="9", decided_by="claude", now=NOW, same_title=True
    )
    assert count == 2
    assert {(r["store_id"], r["variant_id"]) for r in connection.execute("SELECT * FROM listing_decisions")} == {
        ("test_store", 10),
        ("other_store", 50),
    }
    assert [(i.title, i.listing_count) for i in review.queue(connection)] == [("Delta Reign 3-Pack Blister", 1)]


def test_ensure_schema_repoints_old_listing_foreign_key(connection):
    connection.executescript(
        """
        DROP TABLE listing_snapshots;
        DROP TABLE store_listings;
        CREATE TABLE store_listings (
            store_id TEXT NOT NULL, variant_id INTEGER NOT NULL, title TEXT NOT NULL,
            catalog_product_id INTEGER REFERENCES products(product_id),
            PRIMARY KEY (store_id, variant_id)
        ) WITHOUT ROWID;
        INSERT INTO store_listings VALUES ('s', 1, 'Old listing', NULL);
        """
    )
    review.ensure_schema(connection)
    targets = {row["table"] for row in connection.execute("PRAGMA foreign_key_list(store_listings)")}
    assert targets == {"ref_products"}
    assert connection.execute("SELECT title FROM store_listings").fetchone()["title"] == "Old listing"
    review.ensure_schema(connection)  # idempotent


def test_matching_accuracy_on_300_real_titles():
    """Hand-labeled sample of real titles: no wrong exact match, at least 90% recall."""
    fixture = json.loads((FIXTURES / "store_titles_p2.json").read_text())
    groups = fixture["catalog"]["groups"]
    catalog = match.Catalog.from_rows(
        [(group_id, name) for group_id, name, _ in groups],
        [tuple(row) for row in fixture["catalog"]["products"]],
        [abbreviation for _, _, abbreviation in groups if abbreviation],
    )
    wrong, found, matchable = [], 0, 0
    for item in fixture["titles"]:
        result = match.match_listing(catalog, item["title"], item["variant"])
        expected = item["expected_product_id"]
        if result.status == "exact" and result.catalog_product_id != expected:
            wrong.append((item["title"], result.catalog_product_id, expected))
        if expected is not None:
            matchable += 1
            found += result.status == "exact" and result.catalog_product_id == expected
    assert wrong == []
    assert len(fixture["titles"]) == 300
    assert found / matchable >= 0.90, f"recall {found}/{matchable}"
