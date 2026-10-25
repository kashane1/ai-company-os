from __future__ import annotations

from pathlib import Path

import pytest

from radar import watchlist
from radar.catalog import classify
from radar.stores import match, msrp

GROUPS = {1: "ME06: Delta Reign", 2: "SV: Prismatic Evolutions", 3: "Sword & Shield"}
# (product_id, group_id, name, release_on)
PRODUCTS = [
    (11, 1, "Delta Reign Elite Trainer Box", "2026-11-06"),
    (12, 1, "Delta Reign Pokemon Center Elite Trainer Box (Exclusive)", "2026-11-06"),
    (13, 1, "Delta Reign Booster Box", "2026-11-06"),
    (14, 1, "Delta Reign Booster Bundle", "2026-11-06"),
    (21, 2, "Prismatic Evolutions Elite Trainer Box", "2025-01-17"),
    (22, 2, "Prismatic Evolutions Super-Premium Collection (10 Booster Packs)", "2025-01-17"),
    (31, 3, "Sword & Shield Elite Trainer Box", "2020-02-07"),
]

TOML = """
[[reference]]
product_id = 11
name = "Delta Reign Elite Trainer Box"
msrp = 59.99
basis = "distributor_or_press"
evidence_url = "https://example.com/press"
checked_on = "2026-10-01"

[[reference]]
product_id = 11
name = "Delta Reign Elite Trainer Box"
msrp = 54.99
basis = "official_listing"
evidence_url = "https://www.pokemoncenter.com/product/x"
checked_on = "2026-10-20"

[[form_default]]
form = "etb"
msrp = 49.99
since = "2023-01-01"

[[form_default]]
form = "etb"
msrp = 54.99
since = "2026-01-01"

[[form_default]]
form = "etb"
exclusive = "Pokemon Center"
msrp = 59.99
since = "2023-01-01"

[[pack_price]]
msrp = 4.49
since = "2023-01-01"

[[unpriced]]
product_id = 13
reason = "not yet listed anywhere"
"""


@pytest.fixture()
def msrp_connection(connection):
    for group_id, name in GROUPS.items():
        connection.execute("INSERT INTO ref_groups (group_id, name) VALUES (?, ?)", (group_id, name))
    for product_id, group_id, name, release_on in PRODUCTS:
        connection.execute(
            """
            INSERT INTO ref_products (product_id, group_id, name, product_type, exclusive_retailer, release_on, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, '2026-10-01')
            """,
            (product_id, group_id, name, classify.product_type(name), classify.exclusive_retailer(name), release_on),
        )
    connection.commit()
    return connection


@pytest.fixture()
def config(tmp_path: Path) -> msrp.Config:
    path = tmp_path / "msrp.toml"
    path.write_text(TOML)
    return msrp.load(path)


def _resolve(connection, config, product_id, items=()):
    msrp.sync(connection, config, items=list(items))
    return msrp.Resolver.from_db(connection, config).resolve(msrp.product(connection, product_id))


def test_strongest_evidence_wins(msrp_connection, config):
    resolved = _resolve(msrp_connection, config, 11)
    assert (resolved.msrp_cents, resolved.basis, resolved.is_estimated) == (5499, "official_listing", False)


def test_estimates_follow_form_window_exclusive_and_pack_count(msrp_connection, config):
    assert _resolve(msrp_connection, config, 21) == msrp.Msrp(4999, "form_default")  # 2025 standard ETB
    assert _resolve(msrp_connection, config, 12) == msrp.Msrp(5999, "form_default")  # Pokémon Center ETB
    assert _resolve(msrp_connection, config, 22) == msrp.Msrp(4490, "per_pack_estimate")  # 10 packs
    assert _resolve(msrp_connection, config, 31) is None  # before every rule's window
    assert _resolve(msrp_connection, config, 13) is None  # booster box: no evidence, no default


def test_unpriced_and_name_excludes_block_estimates(msrp_connection, tmp_path):
    path = tmp_path / "msrp.toml"
    path.write_text(
        '[[form_default]]\nform = "etb"\nmsrp = 49.99\nsince = "2025-01-01"\nname_excludes = ["Prismatic"]\n'
        '[[form_default]]\nform = "etb"\nexclusive = "Pokemon Center"\nmsrp = 59.99\nsince = "2025-01-01"\n'
        '[[unpriced]]\nproduct_id = 12\nreason = "test"\n'
    )
    config = msrp.load(path)
    assert _resolve(msrp_connection, config, 21) is None  # name excluded
    assert _resolve(msrp_connection, config, 12) is None  # unpriced, despite the PC default
    assert _resolve(msrp_connection, config, 11) == msrp.Msrp(4999, "form_default")


def test_newest_form_default_applies(msrp_connection, config):
    # A 2026 standard ETB without evidence takes the 2026 default, not the 2023 one.
    msrp_connection.execute("DELETE FROM msrp_references")
    resolver = msrp.Resolver({}, config)
    assert resolver.resolve(msrp.product(msrp_connection, 11)) == msrp.Msrp(5499, "form_default")


@pytest.mark.parametrize(
    ("price", "market", "expected"),
    [
        (4700, None, "below_msrp"),   # 0.94x
        (4750, None, "at_msrp"),      # 0.95x
        (5500, None, "at_msrp"),      # 1.10x
        (5600, None, "near_msrp"),
        (6250, None, "near_msrp"),    # 1.25x
        (6300, None, "market"),       # market unknown
        (8000, 8000, "market"),
        (8401, 8000, "marked_up"),    # over 1.05x market
    ],
)
def test_class_boundaries(price, market, expected):
    assert msrp.classify(price, msrp.Msrp(5000, "official_listing"), market).name == expected


def test_set_number_is_not_a_pack_count(msrp_connection, config):
    assert msrp.name_pack_count("151 Booster Pack") is None
    assert msrp.name_pack_count("Super-Premium Collection (10 Booster Packs)") == 10


def test_warning_for_unvetted_below_msrp_or_far_below_market():
    reference = msrp.Msrp(4999, "official_listing")
    at = msrp.classify(4999, reference, 40000)
    assert "far below market ($400.00)" in msrp.warning(at, "unvetted", 4999, 40000)
    assert msrp.warning(at, "checked", 4999, 40000) is None
    assert msrp.warning(at, "unvetted", 4999, 6000) is None
    below = msrp.classify(3999, reference, 6000)
    assert msrp.warning(below, "unvetted", 3999, 6000).startswith("Unvetted store, below MSRP")


def test_only_evidence_is_alert_eligible():
    evidence = msrp.Msrp(5000, "big_box_first_party")
    estimate = msrp.Msrp(5000, "form_default")
    assert msrp.classify(4999, evidence, None).is_alert_eligible is True
    assert msrp.classify(4999, estimate, None).is_alert_eligible is False
    assert msrp.classify(6000, evidence, None).is_alert_eligible is False
    assert msrp.classify(4999, None, None).name == "no_msrp"


def _watch(name, alert_at, basis, urls):
    identity = watchlist.Identity(
        watch_id="w", game="pokemon", language="en", market="US", edition="standard", form="booster_bundle",
        packs=6, status="active", ceiling_basis=basis, evidence_urls=tuple(urls), evidence_date="2026-10-18",
    )
    return watchlist.WatchItem(name=name, alert_at=alert_at, retailers=("Best Buy",), auto_buy=False, identity=identity)


@pytest.mark.skipif(not hasattr(watchlist, "Identity"), reason="structured watches not in this checkout")
def test_best_buy_watches_become_references_and_toml_wins(msrp_connection, config):
    bestbuy = "https://www.bestbuy.com/product/delta-reign-bundle"
    items = [
        _watch("Pokemon Delta Reign Booster Bundle (English)", 26.94, "Best Buy first-party retail reference, not MSRP",
               ["https://pokemon.com/news", bestbuy]),
        _watch("Pokemon Delta Reign Elite Trainer Box", 44.0, "Price unverified; discovery only", [bestbuy]),
    ]
    resolved = _resolve(msrp_connection, config, 14, items)
    assert resolved == msrp.Msrp(2694, "big_box_first_party", bestbuy)
    source = msrp_connection.execute("SELECT source FROM msrp_references WHERE product_id = 14").fetchone()[0]
    assert source == "watchlist:w"
    # The unverified watch adds nothing; product 11 keeps its msrp.toml evidence.
    assert _resolve(msrp_connection, config, 11, items).msrp_cents == 5499


def test_coverage_lists_products_without_evidence(msrp_connection, config):
    msrp.sync(msrp_connection, config, items=[])
    text = msrp.render_coverage(msrp_connection, msrp.Resolver.from_db(msrp_connection, config))
    assert "official_listing" in text
    assert "Delta Reign Booster Box" in text and "[not yet listed anywhere]" in text
    assert "Delta Reign Elite Trainer Box " not in text.split("Without evidence")[1]


def test_load_rejects_estimate_basis_and_missing_evidence(tmp_path):
    path = tmp_path / "msrp.toml"
    path.write_text('[[reference]]\nproduct_id = 1\nmsrp = 1\nbasis = "form_default"\nevidence_url = "x"\nchecked_on = "2026-01-01"\n')
    with pytest.raises(ValueError, match="evidence bases"):
        msrp.load(path)
    path.write_text('[[reference]]\nproduct_id = 1\nmsrp = 1\nbasis = "official_listing"\nchecked_on = "2026-01-01"\n')
    with pytest.raises(ValueError, match="evidence_url"):
        msrp.load(path)


def test_shipped_msrp_file_loads():
    config = msrp.load()
    assert all(reference.basis in msrp.EVIDENCE_BASES for reference in config.references)
