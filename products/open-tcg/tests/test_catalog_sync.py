"""tcgcsv sealed-catalog sync: selection, idempotency, and calendar events."""

from __future__ import annotations

import copy
import datetime as dt

from radar import sources
from radar.catalog import sync

from .conftest import NOW, load_json

DELTA_REIGN = 24831


class FakeTcgCsv:
    """Serves fixture payloads and records which groups were fetched."""

    def __init__(self) -> None:
        self.groups = load_json("tcgcsv_groups.json")["results"]
        self.products = {DELTA_REIGN: load_json("tcgcsv_products_24831.json")["results"]}
        self.prices = {DELTA_REIGN: load_json("tcgcsv_prices_24831.json")["results"]}
        self.product_calls: list[int] = []

    def fetch_groups(self) -> list[dict]:
        return copy.deepcopy(self.groups)

    def fetch_products(self, group_id: int) -> list[dict]:
        self.product_calls.append(group_id)
        return copy.deepcopy(self.products.get(group_id, []))

    def fetch_prices(self, group_id: int) -> list[dict]:
        return copy.deepcopy(self.prices.get(group_id, []))

    def touch_group(self, group_id: int, modified_on: str) -> None:
        for group in self.groups:
            if group["groupId"] == group_id:
                group["modifiedOn"] = modified_on


def run(connection, client, *, now=NOW, watch_set_keys=()):
    result = sync.sync_catalog(connection, client, now=now, watch_set_keys=watch_set_keys)
    sources.record_run(connection, "tcgcsv", ok=True, now=now)
    return result


def events(connection, kind: str | None = None) -> list:
    query = "SELECT * FROM calendar_events"
    args: tuple = ()
    if kind:
        query += " WHERE kind = ?"
        args = (kind,)
    return connection.execute(query, args).fetchall()


def test_selects_recent_and_upcoming_groups_plus_watched_sets():
    groups = load_json("tcgcsv_groups.json")["results"]
    selected = sync.select_groups(groups, today=NOW.date(), window_days=120, watch_set_keys={"prismatic evolutions"})
    names = {group["name"] for group in selected}
    assert names == {"ME06: Delta Reign", "ME: 30th Celebration", "SV: Prismatic Evolutions"}


def test_first_run_stores_sealed_products_without_emitting_events(connection):
    client = FakeTcgCsv()
    result = run(connection, client)

    assert result.products_upserted == 5
    assert events(connection) == []
    row = connection.execute("SELECT * FROM products WHERE product_id = 712109").fetchone()
    assert row["product_type"] == "blister"
    assert row["exclusive_retailer"] == "Target"
    assert row["release_on"] == "2026-11-06"
    assert row["is_presale"] == 1


def test_prices_are_recorded_once_per_day(connection):
    client = FakeTcgCsv()
    run(connection, client)
    run(connection, client)
    rows = connection.execute("SELECT * FROM price_points WHERE product_id = 712094").fetchall()
    assert len(rows) == 1
    assert rows[0]["day"] == "2026-09-25"
    assert rows[0]["market_price"] > 0


def test_unchanged_groups_are_not_refetched(connection):
    client = FakeTcgCsv()
    run(connection, client)
    client.product_calls.clear()
    run(connection, client)
    assert DELTA_REIGN not in client.product_calls


def test_a_new_sku_emits_one_sku_added_event(connection):
    client = FakeTcgCsv()
    run(connection, client)

    new_product = copy.deepcopy(client.products[DELTA_REIGN][0])
    new_product["productId"] = 799999
    new_product["name"] = "Delta Reign Premium Collection [Mega Ampharos]"
    client.products[DELTA_REIGN].append(new_product)
    client.touch_group(DELTA_REIGN, "2026-09-26T10:00:00")

    later = NOW + dt.timedelta(days=1)
    run(connection, client, now=later)
    run(connection, client, now=later)  # a re-run must not duplicate the event

    added = events(connection, "sku_added")
    assert len(added) == 1
    assert added[0]["product_id"] == 799999
    assert "Mega Ampharos" in added[0]["subject_text"]


def test_a_changed_release_date_emits_release_date_changed(connection):
    client = FakeTcgCsv()
    run(connection, client)

    moved = client.products[DELTA_REIGN][0]
    moved["presaleInfo"]["releasedOn"] = "2026-11-13T00:00:00"
    client.touch_group(DELTA_REIGN, "2026-09-26T10:00:00")
    run(connection, client, now=NOW + dt.timedelta(days=1))

    changed = events(connection, "release_date_changed")
    assert len(changed) == 1
    assert changed[0]["value"] == "2026-11-06 -> 2026-11-13"
    stored = connection.execute(
        "SELECT release_on FROM products WHERE product_id = ?", (moved["productId"],)
    ).fetchone()
    assert stored["release_on"] == "2026-11-13"


def test_single_cards_are_skipped(connection):
    client = FakeTcgCsv()
    client.products[DELTA_REIGN].append(
        {
            "productId": 800001,
            "groupId": DELTA_REIGN,
            "name": "Mega Ampharos ex - 001/150",
            "extendedData": [{"name": "Number", "value": "001/150"}, {"name": "Rarity", "value": "Double Rare"}],
        }
    )
    result = run(connection, client)
    assert result.singles_skipped == 1
    assert connection.execute("SELECT 1 FROM products WHERE product_id = 800001").fetchone() is None


def placeholder_group(group_id: int, name: str) -> dict:
    return {
        "groupId": group_id,
        "name": name,
        "publishedOn": "2026-09-25T20:00:05.9994058Z",
        "modifiedOn": "2026-09-22T14:52:52.883",
    }


def test_placeholder_dated_legacy_groups_are_not_treated_as_new():
    groups = [placeholder_group(1422, "POP Series 1"), placeholder_group(2374, "Miscellaneous Cards & Products")]
    selected = sync.select_groups(groups, today=NOW.date(), window_days=120, watch_set_keys=set())
    # The catch-all group is kept for new presale items; old POP series are not.
    assert [group["name"] for group in selected] == ["Miscellaneous Cards & Products"]


def test_products_in_placeholder_groups_only_get_real_presale_dates(connection):
    client = FakeTcgCsv()
    client.groups.append(placeholder_group(2374, "Miscellaneous Cards & Products"))
    client.products[2374] = [
        {"productId": 900001, "groupId": 2374, "name": "Knock Out Collection [Kyogre]", "extendedData": []},
        {
            "productId": 900002,
            "groupId": 2374,
            "name": "League Battle Deck [Mega Greninja ex]",
            "extendedData": [],
            "presaleInfo": {"isPresale": True, "releasedOn": "2026-12-04T00:00:00"},
        },
    ]
    run(connection, client)
    release = dict(connection.execute("SELECT product_id, release_on FROM products WHERE group_id = 2374").fetchall())
    assert release == {900001: None, 900002: "2026-12-04"}
