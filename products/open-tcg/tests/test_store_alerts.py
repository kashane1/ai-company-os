from __future__ import annotations

import datetime as dt

import pytest

from radar import watchlist
from radar.stores import alerts, match, msrp

from .conftest import NOW
from .test_stores import _collect, _product, catalog_connection  # noqa: F401  (fixture)

DELTA_ETB, DELTA_BUNDLE, RIVALS_ETB = 1, 4, 11
LATER = NOW + dt.timedelta(minutes=15)


def _resolver(**prices: tuple[int, str]) -> msrp.Resolver:
    evidence = {
        int(product_id[1:]): [msrp.Reference(int(product_id[1:]), cents, basis, "https://example.com", "2026-10-01", "test")]
        for product_id, (cents, basis) in prices.items()
    }
    return msrp.Resolver(evidence, msrp.Config([], [], [], {}))


def _policy(*names: str, alert_at: float | None = None, exclude: tuple[str, ...] = ()) -> watchlist.Policy:
    items = tuple(watchlist.WatchItem(name=name, alert_at=alert_at, retailers=(), auto_buy=False) for name in names)
    return watchlist.Policy(items=items, exclude_terms=exclude)


@pytest.fixture()
def store_connection(catalog_connection):  # noqa: F811
    _collect(catalog_connection, NOW, [])  # baseline sweep: an empty store
    return catalog_connection


def _run(connection, policy, resolver, now=LATER):
    sent = []
    summary = alerts.evaluate(connection, now=now, send=lambda t, b: sent.append((t, b)), policy=policy, resolver=resolver)
    return summary, sent


def test_watched_set_product_at_msrp_alerts_once(store_connection):
    _collect(store_connection, LATER, [_product(1, "Pokemon Delta Reign Booster Bundle", price="26.99")])
    resolver = _resolver(p4=(2694, "big_box_first_party"))
    policy = _policy("Pokemon Delta Reign Elite Trainer Box")  # watches the set, not the bundle
    summary, sent = _run(store_connection, policy, resolver)
    assert (summary.observations, summary.alerts) == (1, 1)
    title, body = sent[0]
    assert title == "At MSRP · Test Store"
    assert "Delta Reign Booster Bundle $26.99 (MSRP $26.94 big-box, market -)" in body
    assert "watched set, at_msrp" in body and body.endswith("https://teststore.com/products/p-1?variant=10")
    # The same change is never handled twice.
    assert _run(store_connection, policy, resolver) == (alerts.AlertSummary(0, 0), [])
    source = store_connection.execute("SELECT first_source_id FROM episodes").fetchone()[0]
    assert source == "stores:test_store"
    details = store_connection.execute(
        "SELECT store_trust, catalog_product_id, price_cents, msrp_cents, msrp_basis, price_class, is_alert_eligible "
        "FROM store_offer_details"
    ).fetchone()
    assert tuple(details) == ("unvetted", 4, 2699, 2694, "big_box_first_party", "at_msrp", 1)


def test_below_msrp_on_unvetted_store_warns(store_connection):
    _collect(store_connection, LATER, [_product(1, "Delta Reign Elite Trainer Box", price="39.99")])
    _, sent = _run(store_connection, _policy("Delta Reign Booster Box"), _resolver(p1=(4999, "official_listing")))
    title, body = sent[0]
    assert title == "Below MSRP (unvetted store) · Test Store"
    assert "Unvetted store, below MSRP: check it before paying." in body


def test_far_below_market_on_unvetted_store_warns(store_connection):
    store_connection.execute("INSERT INTO ref_price_points (product_id, day, market_price) VALUES (1, '2026-09-25', 400.0)")
    _collect(store_connection, LATER, [_product(1, "Delta Reign Elite Trainer Box", price="49.99")])
    _, sent = _run(store_connection, _policy("Delta Reign Booster Box"), _resolver(p1=(4999, "official_listing")))
    title, body = sent[0]
    assert title == "At MSRP (unvetted store) · Test Store"
    assert "far below market ($400.00)" in body


@pytest.mark.parametrize(
    ("price", "policy", "resolver", "reason"),
    [
        ("59.99", _policy("Delta Reign Booster Box"), _resolver(p1=(4999, "official_listing")), "near_msrp"),
        ("49.99", _policy("Destined Rivals Booster Box"), _resolver(p1=(4999, "official_listing")), "set not watched"),
        ("49.99", _policy("Delta Reign Booster Box"), _resolver(), "no evidence MSRP"),
        ("49.99", _policy("Delta Reign Booster Box", exclude=("Delta Reign",)), _resolver(p1=(4999, "official_listing")),
         "excluded term"),
        ("52.99", _policy("Pokemon Delta Reign Elite Trainer Box", alert_at=50.0), _resolver(p1=(4999, "official_listing")),
         "watched, above alert_at"),
    ],
)
def test_no_alert_cases_still_record_observations(store_connection, price, policy, resolver, reason):
    _collect(store_connection, LATER, [_product(1, "Delta Reign Elite Trainer Box", price=price)])
    candidate = alerts.candidates(store_connection, now=LATER, resolver=resolver)[0]
    context = alerts.watch_context(store_connection, match.Catalog.from_db(store_connection), policy)
    assert alerts.decide(candidate, context).reason == reason
    summary, sent = _run(store_connection, policy, resolver)
    assert (summary.observations, summary.alerts, sent) == (1, 0, [])


def test_watched_product_without_evidence_alerts_at_alert_at(store_connection):
    _collect(store_connection, LATER, [_product(1, "Delta Reign Elite Trainer Box", price="49.99")])
    summary, sent = _run(store_connection, _policy("Pokemon Delta Reign Elite Trainer Box", alert_at=50.0), _resolver())
    assert summary.alerts == 1
    assert sent[0][0] == "Under your alert_at · Test Store"
    assert "watched, at or below alert_at" in sent[0][1]


def test_marked_up_never_alerts_even_when_watched(store_connection):
    store_connection.execute("INSERT INTO ref_price_points (product_id, day, market_price) VALUES (1, '2026-09-25', 60.0)")
    _collect(store_connection, LATER, [_product(1, "Delta Reign Elite Trainer Box", price="99.99")])
    resolver = _resolver(p1=(4999, "official_listing"))
    candidate = alerts.candidates(store_connection, now=LATER, resolver=resolver)[0]
    assert candidate.price_class.name == "marked_up"
    summary, sent = _run(store_connection, _policy("Pokemon Delta Reign Elite Trainer Box", alert_at=120.0), resolver)
    assert (summary.alerts, sent) == (0, [])


def test_only_changes_that_make_it_newly_buyable_and_fresh(store_connection):
    resolver = _resolver(p1=(4999, "official_listing"))
    policy = _policy("Delta Reign Booster Box")
    _collect(store_connection, LATER, [_product(1, "Delta Reign Elite Trainer Box", price="49.99")])
    assert _run(store_connection, policy, resolver)[0].alerts == 1
    # A price rise is not a candidate.
    t2 = LATER + dt.timedelta(minutes=30)
    _collect(store_connection, t2, [_product(1, "Delta Reign Elite Trainer Box", price="54.99")])
    assert alerts.candidates(store_connection, now=t2, resolver=resolver) == []
    # A drop back is, but it is the same episode (within the hour), so no second banner.
    t3 = t2 + dt.timedelta(minutes=15)
    _collect(store_connection, t3, [_product(1, "Delta Reign Elite Trainer Box", price="49.99")])
    summary, sent = _run(store_connection, policy, resolver, now=t3)
    assert (summary.observations, summary.alerts) == (1, 0)
    # Changes older than the freshness window are ignored.
    assert alerts.candidates(store_connection, now=t3 + dt.timedelta(minutes=16), resolver=resolver) == []


def test_baseline_sweep_never_alerts(catalog_connection):  # noqa: F811
    _collect(catalog_connection, NOW, [_product(1, "Delta Reign Elite Trainer Box", price="49.99")])
    assert alerts.candidates(catalog_connection, now=NOW, resolver=_resolver(p1=(4999, "official_listing"))) == []


def test_set_keys_named_prefers_set_over_era():
    groups = ["ME01: Mega Evolution", "ME06: Delta Reign", "SV: Prismatic Evolutions"]
    names = ["Pokemon Mega Evolution Delta Reign Elite Trainer Box (English)", "Prismatic Evolutions Poster Collection"]
    assert alerts._set_keys_named(groups, names) == {"delta reign", "prismatic evolutions"}


def test_deals_digest_groups_by_class_with_daily_change(store_connection):
    from radar.stores import deals

    store_connection.execute("INSERT INTO ref_price_points (product_id, day, market_price) VALUES (11, '2026-09-25', 60.0)")
    _collect(store_connection, LATER, [
        _product(1, "Delta Reign Elite Trainer Box", price="54.99"),
        _product(2, "Destined Rivals Elite Trainer Box", price="99.99"),
    ])
    day_later = LATER + dt.timedelta(days=1, minutes=15)
    _collect(store_connection, day_later, [
        _product(1, "Delta Reign Elite Trainer Box", price="49.99"),
        _product(2, "Destined Rivals Elite Trainer Box", price="99.99"),
        _product(4, "Delta Reign Booster Bundle", price="29.99"),
    ])
    resolver = _resolver(p1=(4999, "official_listing"), p11=(4999, "official_listing"))
    items = {d.offer.product_id: d for d in deals.deals(store_connection, now=day_later, resolver=resolver)}
    assert (items[1].offer.price_class.name, items[1].yesterday_cents) == ("at_msrp", 5499)
    assert items[11].offer.price_class.name == "marked_up"
    assert items[4].yesterday_cents is None


def test_avoid_store_is_never_offered_or_alerted(store_connection):
    from radar.stores import report

    _collect(store_connection, LATER, [_product(1, "Delta Reign Elite Trainer Box", price="39.99")])
    store_connection.execute("UPDATE stores SET trust = 'avoid' WHERE store_id = 'test_store'")
    resolver = _resolver(p1=(4999, "official_listing"))
    assert alerts.candidates(store_connection, now=LATER, resolver=resolver) == []
    assert report.offers(store_connection, {}, resolver) == []


def test_alert_and_report_show_shipping(store_connection, monkeypatch):
    from radar.stores import registry, report

    shipped = registry.Store(store_id="test_store", name="Test Store", domain="teststore.com", tier="first_pass",
                             shipping_cents=999, free_shipping_over_cents=10000)
    monkeypatch.setattr(registry, "load", lambda *a, **k: [shipped])
    _collect(store_connection, LATER, [_product(1, "Delta Reign Elite Trainer Box", price="49.99")])
    _, sent = _run(store_connection, _policy("Delta Reign Booster Box"), _resolver(p1=(4999, "official_listing")))
    assert "Delta Reign Elite Trainer Box $49.99 + $9.99 ship = $59.98 (MSRP $49.99 official" in sent[0][1]
    assert sent[0][0] == "At MSRP · Test Store"  # classes stay on the item price
    assert report.price_with_shipping(12000, shipped.shipping_for(12000)) == "$120.00, free shipping"
    assert report.price_with_shipping(4999, None) == "$49.99"


def test_registry_shipping_fields(tmp_path):
    from radar.stores import registry

    path = tmp_path / "stores.toml"
    path.write_text('[[store]]\nstore_id = "a"\nname = "A"\ndomain = "a.com"\ntier = "explore"\n'
                    'shipping = 9.99\nfree_shipping_over = 100\n')
    (store,) = registry.load(path)
    assert (store.shipping_for(4999), store.shipping_for(10000)) == (999, 0)
    path.write_text('[[store]]\nstore_id = "a"\nname = "A"\ndomain = "a.com"\ntier = "explore"\nshipping = -1\n')
    with pytest.raises(ValueError, match="shipping"):
        registry.load(path)
