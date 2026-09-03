"""Tests for screener filter construction.

Runs the generated SQL against a small in-memory database built from the real
schema, which catches both malformed SQL and filters that silently mean the
wrong thing.
"""

from __future__ import annotations

import sqlite3

import pytest

from api.screener import BENCHMARKS, MAX_LIMIT, ScreenerFilters, build_query
from ingest.config import SCHEMA_PATH


@pytest.fixture()
def connection() -> sqlite3.Connection:
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    connection.executescript(SCHEMA_PATH.read_text())
    connection.execute(
        "INSERT INTO sets (group_id, name, released_on) VALUES (1, 'Evolving Skies', '2021-08-27')"
    )
    connection.execute(
        "INSERT INTO sets (group_id, name, released_on) VALUES (2, 'Surging Sparks', '2024-11-08')"
    )
    return connection


def add_card(
    connection: sqlite3.Connection,
    *,
    variant_id: int,
    name: str,
    group_id: int = 1,
    sub_type: str = "Holofoil",
    rarity: str = "Ultra Rare",
    current_price: float = 50.0,
    peak_price: float = 100.0,
    high_52w: float | None = None,
    change_7d_pct: float | None = -1.0,
    history_days: int = 400,
    observation_count_30d: int = 30,
    spread_pct: float | None = 10.0,
    pct_of_52w_range: float | None = 20.0,
    peak_within_30d_of_release: int = 0,
    peak_is_first_observation: int = 0,
    distinct_prices_90d: int = 20,
    current_vs_median_90d_pct: float | None = 90.0,
    card_class: str | None = "Pokemon",
    trainer_kind: str | None = None,
) -> None:
    """Insert one screenable card. Discounts are derived so the fixtures stay
    internally consistent with what the metrics job would have written."""
    high_52w = peak_price if high_52w is None else high_52w

    def discount(reference: float) -> float:
        return max(0.0, (reference - current_price) / reference * 100.0)

    connection.execute(
        """
        INSERT INTO cards (
            product_id, group_id, name, number, rarity, card_class, trainer_kind
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (variant_id, group_id, name, "001/100", rarity, card_class, trainer_kind),
    )
    connection.execute(
        "INSERT INTO card_variants (variant_id, product_id, sub_type) VALUES (?, ?, ?)",
        (variant_id, variant_id, sub_type),
    )
    connection.execute(
        """
        INSERT INTO card_metrics (
            variant_id, as_of_day, current_price, peak_price, peak_day,
            high_52w, high_26w, high_13w, low_52w,
            discount_from_peak_pct, discount_from_52w_high_pct,
            discount_from_26w_high_pct, discount_from_13w_high_pct,
            pct_of_52w_range, change_7d_pct, change_30d_pct, change_90d_pct,
            observation_count, observation_count_30d, first_day, history_days,
            days_since_peak, spread_pct, coverage_30d_pct,
            peak_is_first_observation, peak_within_30d_of_release,
            distinct_prices_90d, current_vs_median_90d_pct
        ) VALUES (?, 900, ?, ?, 500, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?, 400, ?, 100.0, ?, ?, ?, ?)
        """,
        (
            variant_id,
            current_price,
            peak_price,
            high_52w,
            high_52w,
            high_52w,
            current_price,
            discount(peak_price),
            discount(high_52w),
            discount(high_52w),
            discount(high_52w),
            pct_of_52w_range,
            change_7d_pct,
            -5.0,
            -10.0,
            history_days,
            observation_count_30d,
            history_days,
            spread_pct,
            peak_is_first_observation,
            peak_within_30d_of_release,
            distinct_prices_90d,
            current_vs_median_90d_pct,
        ),
    )
    connection.commit()


def run(connection: sqlite3.Connection, filters: ScreenerFilters) -> list[sqlite3.Row]:
    rows_sql, count_sql, params = build_query(filters)
    total = connection.execute(count_sql, params).fetchone()[0]
    rows = connection.execute(rows_sql, params).fetchall()
    # The page can never claim a different population than the count.
    assert total >= len(rows)
    return rows


def names(rows) -> list[str]:
    return [row["card_name"] for row in rows]


# ---------------------------------------------------------------------------


def test_every_benchmark_produces_runnable_sql(connection):
    add_card(connection, variant_id=1, name="Umbreon VMAX")

    for key in BENCHMARKS:
        rows = run(connection, ScreenerFilters(benchmark=key, min_discount_pct=0))
        assert names(rows) == ["Umbreon VMAX"], key


def test_min_discount_excludes_shallower_drawdowns(connection):
    add_card(connection, variant_id=1, name="Deep", current_price=20.0, peak_price=100.0)
    add_card(connection, variant_id=2, name="Shallow", current_price=90.0, peak_price=100.0)

    rows = run(connection, ScreenerFilters(benchmark="peak", min_discount_pct=50))

    assert names(rows) == ["Deep"]


def test_discount_band_filters_from_both_ends(connection):
    add_card(connection, variant_id=1, name="Down 20", current_price=80.0, peak_price=100.0)
    add_card(connection, variant_id=2, name="Down 50", current_price=50.0, peak_price=100.0)
    add_card(connection, variant_id=3, name="Down 90", current_price=10.0, peak_price=100.0)

    rows = run(
        connection,
        ScreenerFilters(benchmark="peak", min_discount_pct=40, max_discount_pct=60),
    )

    assert names(rows) == ["Down 50"]


def test_price_bounds_apply_to_the_current_price(connection):
    add_card(connection, variant_id=1, name="Cheap", current_price=5.0, peak_price=100.0)
    add_card(connection, variant_id=2, name="Mid", current_price=25.0, peak_price=100.0)
    add_card(connection, variant_id=3, name="Pricey", current_price=400.0, peak_price=1000.0)

    rows = run(
        connection,
        ScreenerFilters(benchmark="peak", min_discount_pct=0, min_price=10, max_price=100),
    )

    assert names(rows) == ["Mid"]


def test_search_matches_card_name_or_set_name(connection):
    add_card(connection, variant_id=1, name="Charizard ex", group_id=2)
    add_card(connection, variant_id=2, name="Pikachu", group_id=1)

    by_card = run(connection, ScreenerFilters(min_discount_pct=0, search="chariz"))
    by_set = run(connection, ScreenerFilters(min_discount_pct=0, search="Evolving"))

    assert names(by_card) == ["Charizard ex"]
    assert names(by_set) == ["Pikachu"]


def test_search_treats_wildcards_as_literal_text(connection):
    """A bare % must not turn into "match everything"."""
    add_card(connection, variant_id=1, name="Pikachu")

    rows = run(connection, ScreenerFilters(min_discount_pct=0, search="%"))

    assert rows == []


def test_set_rarity_and_finish_filters_combine(connection):
    add_card(connection, variant_id=1, name="Target", group_id=2, rarity="Illustration Rare",
             sub_type="Holofoil")
    add_card(connection, variant_id=2, name="Wrong set", group_id=1, rarity="Illustration Rare",
             sub_type="Holofoil")
    add_card(connection, variant_id=3, name="Wrong rarity", group_id=2, rarity="Common",
             sub_type="Holofoil")
    add_card(connection, variant_id=4, name="Wrong finish", group_id=2,
             rarity="Illustration Rare", sub_type="Reverse Holofoil")

    rows = run(
        connection,
        ScreenerFilters(
            min_discount_pct=0,
            group_ids=[2],
            rarities=["Illustration Rare"],
            sub_types=["Holofoil"],
        ),
    )

    assert names(rows) == ["Target"]


def test_release_spikes_are_excluded_by_default(connection):
    add_card(connection, variant_id=1, name="Organic", peak_within_30d_of_release=0)
    add_card(connection, variant_id=2, name="Hype spike", peak_within_30d_of_release=1)

    default_rows = run(connection, ScreenerFilters(min_discount_pct=0))
    permissive = run(
        connection, ScreenerFilters(min_discount_pct=0, exclude_release_spikes=False)
    )

    assert names(default_rows) == ["Organic"]
    assert sorted(names(permissive)) == ["Hype spike", "Organic"]


def test_truncated_peaks_can_be_excluded(connection):
    add_card(connection, variant_id=1, name="Full history", peak_is_first_observation=0)
    add_card(connection, variant_id=2, name="Peak at edge", peak_is_first_observation=1)

    rows = run(
        connection, ScreenerFilters(min_discount_pct=0, exclude_truncated_peaks=True)
    )

    assert names(rows) == ["Full history"]


def test_quality_floors_drop_thin_history_and_illiquid_cards(connection):
    add_card(connection, variant_id=1, name="Good", history_days=400, observation_count_30d=28)
    add_card(connection, variant_id=2, name="Thin history", history_days=30,
             observation_count_30d=28)
    add_card(connection, variant_id=3, name="Illiquid", history_days=400,
             observation_count_30d=2)

    rows = run(
        connection,
        ScreenerFilters(min_discount_pct=0, min_history_days=180, min_observations_30d=10),
    )

    assert names(rows) == ["Good"]


def test_price_outliers_are_excluded_by_default(connection):
    """The $600-card-quoting-$0.99 case, which otherwise wins "deepest discount"."""
    add_card(connection, variant_id=1, name="Real decline", current_vs_median_90d_pct=80.0)
    add_card(connection, variant_id=2, name="Feed error", current_price=0.99,
             peak_price=600.0, current_vs_median_90d_pct=0.16)

    default_rows = run(connection, ScreenerFilters(benchmark="peak", min_discount_pct=0,
                                                  min_price=None))
    permissive = run(connection, ScreenerFilters(benchmark="peak", min_discount_pct=0,
                                                min_price=None,
                                                exclude_price_outliers=False))

    assert names(default_rows) == ["Real decline"]
    assert "Feed error" in names(permissive)


def test_unknown_median_ratio_is_excluded_as_insufficient_evidence(connection):
    add_card(connection, variant_id=1, name="Known", current_vs_median_90d_pct=90.0)
    add_card(connection, variant_id=2, name="No median", current_vs_median_90d_pct=None)

    rows = run(connection, ScreenerFilters(min_discount_pct=0))

    assert names(rows) == ["Known"]


def test_default_price_floor_excludes_bulk_commons(connection):
    """A 99% discount on a $0.01 common is $0.98 of movement."""
    add_card(connection, variant_id=1, name="Penny common", current_price=0.01,
             peak_price=0.98)
    add_card(connection, variant_id=2, name="Real card", current_price=24.0,
             peak_price=100.0)

    rows = run(connection, ScreenerFilters(benchmark="peak", min_discount_pct=0))

    assert names(rows) == ["Real card"]


def test_frozen_price_cards_are_excluded_by_default(connection):
    """The default floor keeps stale quotes off the first page."""
    add_card(connection, variant_id=1, name="Trading", distinct_prices_90d=25)
    add_card(connection, variant_id=2, name="Frozen quote", distinct_prices_90d=1)

    default_rows = run(connection, ScreenerFilters(min_discount_pct=0))
    permissive = run(
        connection, ScreenerFilters(min_discount_pct=0, min_distinct_prices_90d=0)
    )

    assert names(default_rows) == ["Trading"]
    assert sorted(names(permissive)) == ["Frozen quote", "Trading"]


def test_momentum_filter_finds_cards_that_stopped_falling(connection):
    add_card(connection, variant_id=1, name="Stabilised", change_7d_pct=0.5)
    add_card(connection, variant_id=2, name="Still falling", change_7d_pct=-12.0)

    rows = run(connection, ScreenerFilters(min_discount_pct=0, min_change_7d_pct=0))

    assert names(rows) == ["Stabilised"]


def test_null_metrics_do_not_pass_a_range_filter(connection):
    """NULL means "not computable", which must not be read as "in range"."""
    add_card(connection, variant_id=1, name="Known", pct_of_52w_range=15.0)
    add_card(connection, variant_id=2, name="Unknown", pct_of_52w_range=None)

    rows = run(connection, ScreenerFilters(min_discount_pct=0, max_range_position_pct=25))

    assert names(rows) == ["Known"]


def test_spread_filter_excludes_unknown_spreads(connection):
    add_card(connection, variant_id=1, name="Tight", spread_pct=8.0)
    add_card(connection, variant_id=2, name="Wide", spread_pct=90.0)
    add_card(connection, variant_id=3, name="Unknown", spread_pct=None)

    rows = run(connection, ScreenerFilters(min_discount_pct=0, max_spread_pct=20))

    assert names(rows) == ["Tight"]


# ---------------------------------------------------------------------------
# Ordering and paging
# ---------------------------------------------------------------------------


def test_default_sort_is_deepest_discount_first(connection):
    add_card(connection, variant_id=1, name="Down 30", current_price=70.0, peak_price=100.0)
    add_card(connection, variant_id=2, name="Down 80", current_price=20.0, peak_price=100.0)
    add_card(connection, variant_id=3, name="Down 55", current_price=45.0, peak_price=100.0)

    rows = run(connection, ScreenerFilters(benchmark="peak", min_discount_pct=0))

    assert names(rows) == ["Down 80", "Down 55", "Down 30"]


def test_ascending_price_sort(connection):
    add_card(connection, variant_id=1, name="Expensive", current_price=300.0, peak_price=900.0)
    add_card(connection, variant_id=2, name="Cheap", current_price=3.0, peak_price=9.0)

    rows = run(
        connection,
        ScreenerFilters(min_discount_pct=0, sort="price", descending=False),
    )

    assert names(rows) == ["Cheap", "Expensive"]


def test_reference_sort_follows_the_active_benchmark(connection):
    """The reference-price column moves with the benchmark, so sorting by it has
    to resolve late. These two cards order oppositely under the two windows, which
    a sort hardwired to one column could not satisfy. Their prices are also chosen
    so reference order disagrees with discount order — with equal current prices
    the two are the same ranking, and the fixture would prove nothing."""
    add_card(
        connection, variant_id=1, name="Low ref", current_price=2.0,
        peak_price=100.0, high_52w=20.0,
    )
    add_card(
        connection, variant_id=2, name="High ref", current_price=72.0,
        peak_price=90.0, high_52w=80.0,
    )

    by_52w = run(
        connection,
        ScreenerFilters(benchmark="52w", min_discount_pct=0, sort="reference", descending=False),
    )
    by_peak = run(
        connection,
        ScreenerFilters(benchmark="peak", min_discount_pct=0, sort="reference", descending=False),
    )

    assert names(by_52w) == ["Low ref", "High ref"]
    assert names(by_peak) == ["High ref", "Low ref"]


def test_nulls_sort_last_regardless_of_direction(connection):
    add_card(connection, variant_id=1, name="Has change", change_7d_pct=-4.0)
    add_card(connection, variant_id=2, name="No change", change_7d_pct=None)

    descending = run(connection, ScreenerFilters(min_discount_pct=0, sort="change_7d"))
    ascending = run(
        connection, ScreenerFilters(min_discount_pct=0, sort="change_7d", descending=False)
    )

    assert names(descending)[-1] == "No change"
    assert names(ascending)[-1] == "No change"


def test_pagination_walks_results_without_repeats(connection):
    for index in range(1, 6):
        add_card(
            connection,
            variant_id=index,
            name=f"Card {index}",
            current_price=float(index * 10),
            peak_price=100.0,
        )

    first = run(connection, ScreenerFilters(benchmark="peak", min_discount_pct=0, limit=2))
    second = run(
        connection,
        ScreenerFilters(benchmark="peak", min_discount_pct=0, limit=2, offset=2),
    )

    assert len(first) == 2 and len(second) == 2
    assert not set(names(first)) & set(names(second))


def test_limit_is_capped_and_offset_cannot_go_negative(connection):
    rows_sql, _, _ = build_query(ScreenerFilters(limit=10_000, offset=-5))

    assert f"LIMIT {MAX_LIMIT}" in rows_sql
    assert "OFFSET 0" in rows_sql


def test_unknown_sort_falls_back_to_the_benchmark_discount(connection):
    rows_sql, _, _ = build_query(ScreenerFilters(benchmark="26w", sort="not-a-column"))

    assert "discount_from_26w_high_pct" in rows_sql


def test_filter_values_are_bound_not_interpolated(connection):
    """Guards against a future refactor inlining user input into the SQL."""
    add_card(connection, variant_id=1, name="Pikachu")
    hostile = "'; DROP TABLE card_metrics; --"

    rows_sql, _, params = build_query(ScreenerFilters(search=hostile))

    # The payload never reaches the statement text; it arrives as a parameter.
    # (The bound value is LIKE-escaped, so compare on a wildcard-free fragment.)
    assert "DROP TABLE" not in rows_sql
    assert any("DROP TABLE" in str(param) for param in params)

    run(connection, ScreenerFilters(search=hostile))
    assert connection.execute("SELECT COUNT(*) FROM card_metrics").fetchone()[0] == 1


# ---------------------------------------------------------------------------
# Release year
# ---------------------------------------------------------------------------


def test_release_year_bounds_are_inclusive_at_both_ends(connection):
    """Group 1 is Evolving Skies (2021-08-27), group 2 Surging Sparks (2024-11-08)."""
    add_card(connection, variant_id=1, name="Umbreon VMAX", group_id=1)
    add_card(connection, variant_id=2, name="Pikachu ex", group_id=2)

    assert names(run(connection, ScreenerFilters(min_release_year=2021))) == [
        "Umbreon VMAX",
        "Pikachu ex",
    ]
    assert names(run(connection, ScreenerFilters(min_release_year=2022))) == ["Pikachu ex"]
    assert names(run(connection, ScreenerFilters(max_release_year=2021))) == ["Umbreon VMAX"]
    assert names(run(connection, ScreenerFilters(max_release_year=2024))) == [
        "Umbreon VMAX",
        "Pikachu ex",
    ]


def test_release_year_range_selects_a_single_year(connection):
    add_card(connection, variant_id=1, name="Umbreon VMAX", group_id=1)
    add_card(connection, variant_id=2, name="Pikachu ex", group_id=2)

    rows = run(
        connection, ScreenerFilters(min_release_year=2021, max_release_year=2021)
    )
    assert names(rows) == ["Umbreon VMAX"]


def test_release_year_covers_january_and_december_releases(connection):
    """The bounds are built as Jan 1 / Dec 31, so edge-of-year sets must land."""
    connection.execute(
        "INSERT INTO sets (group_id, name, released_on) VALUES (3, 'New Year', '2015-01-01')"
    )
    connection.execute(
        "INSERT INTO sets (group_id, name, released_on) VALUES (4, 'Year End', '2015-12-31')"
    )
    add_card(connection, variant_id=1, name="January", group_id=3)
    add_card(connection, variant_id=2, name="December", group_id=4)

    rows = run(
        connection, ScreenerFilters(min_release_year=2015, max_release_year=2015)
    )
    assert sorted(names(rows)) == ["December", "January"]


# ---------------------------------------------------------------------------
# Card class
# ---------------------------------------------------------------------------


def test_card_classes_includes_only_the_named_classes(connection):
    add_card(connection, variant_id=1, name="Pikachu", card_class="Pokemon")
    add_card(connection, variant_id=2, name="Ultra Ball", card_class="Trainer",
             trainer_kind="Item")
    add_card(connection, variant_id=3, name="Fire Energy", card_class="Energy")

    rows = run(connection, ScreenerFilters(card_classes=["Pokemon"]))
    assert names(rows) == ["Pikachu"]

    rows = run(connection, ScreenerFilters(card_classes=["Trainer", "Energy"]))
    assert sorted(names(rows)) == ["Fire Energy", "Ultra Ball"]


def test_exclude_card_classes_drops_the_named_classes(connection):
    add_card(connection, variant_id=1, name="Pikachu", card_class="Pokemon")
    add_card(connection, variant_id=2, name="Ultra Ball", card_class="Trainer",
             trainer_kind="Item")
    add_card(connection, variant_id=3, name="Fire Energy", card_class="Energy")

    rows = run(connection, ScreenerFilters(exclude_card_classes=["Trainer", "Energy"]))
    assert names(rows) == ["Pikachu"]


def test_exclude_keeps_unclassified_cards(connection):
    """An unclassifiable card is not secretly a Trainer, so excluding Trainers
    must not silently drop it."""
    add_card(connection, variant_id=1, name="Mystery", card_class=None)
    add_card(connection, variant_id=2, name="Ultra Ball", card_class="Trainer")

    rows = run(connection, ScreenerFilters(exclude_card_classes=["Trainer"]))
    assert names(rows) == ["Mystery"]


def test_include_omits_unclassified_cards(connection):
    """The mirror of the above: asking *for* Pokemon should not hand back a card
    we could not classify."""
    add_card(connection, variant_id=1, name="Mystery", card_class=None)
    add_card(connection, variant_id=2, name="Pikachu", card_class="Pokemon")

    rows = run(connection, ScreenerFilters(card_classes=["Pokemon"]))
    assert names(rows) == ["Pikachu"]


def test_include_and_exclude_together_resolve_to_the_intersection(connection):
    add_card(connection, variant_id=1, name="Pikachu", card_class="Pokemon")
    add_card(connection, variant_id=2, name="Ultra Ball", card_class="Trainer")

    rows = run(
        connection,
        ScreenerFilters(card_classes=["Pokemon", "Trainer"],
                        exclude_card_classes=["Trainer"]),
    )
    assert names(rows) == ["Pikachu"]


def test_trainer_kinds_narrows_within_trainers(connection):
    add_card(connection, variant_id=1, name="Ultra Ball", card_class="Trainer",
             trainer_kind="Item")
    add_card(connection, variant_id=2, name="Professor's Research",
             card_class="Trainer", trainer_kind="Supporter")
    add_card(connection, variant_id=3, name="Pikachu", card_class="Pokemon")

    rows = run(connection, ScreenerFilters(trainer_kinds=["Item"]))
    assert names(rows) == ["Ultra Ball"]

    rows = run(connection, ScreenerFilters(trainer_kinds=["Item", "Supporter"]))
    assert sorted(names(rows)) == ["Professor's Research", "Ultra Ball"]


def test_no_class_filter_returns_everything(connection):
    add_card(connection, variant_id=1, name="Pikachu", card_class="Pokemon")
    add_card(connection, variant_id=2, name="Ultra Ball", card_class="Trainer")
    add_card(connection, variant_id=3, name="Mystery", card_class=None)

    assert len(run(connection, ScreenerFilters())) == 3


# ---------------------------------------------------------------------------
# Set, rarity and finish exclusions
# ---------------------------------------------------------------------------


def test_exclude_group_ids_drops_the_named_sets(connection):
    add_card(connection, variant_id=1, name="Umbreon VMAX", group_id=1)
    add_card(connection, variant_id=2, name="Pikachu ex", group_id=2)

    rows = run(connection, ScreenerFilters(exclude_group_ids=[1]))
    assert names(rows) == ["Pikachu ex"]

    assert run(connection, ScreenerFilters(exclude_group_ids=[1, 2])) == []


def test_exclude_rarities_drops_the_named_rarities(connection):
    add_card(connection, variant_id=1, name="Pikachu", rarity="Common")
    add_card(connection, variant_id=2, name="Charizard", rarity="Ultra Rare")
    add_card(connection, variant_id=3, name="Bulbasaur", rarity="Rare")

    rows = run(connection, ScreenerFilters(exclude_rarities=["Common", "Rare"]))
    assert names(rows) == ["Charizard"]


def test_exclude_rarities_keeps_cards_the_feed_never_graded(connection):
    """Mirrors the card-class rule: a card with no rarity is not secretly the
    rarity being dropped, so excluding Common must not take it with it."""
    add_card(connection, variant_id=1, name="Mystery", rarity=None)
    add_card(connection, variant_id=2, name="Pikachu", rarity="Common")

    rows = run(connection, ScreenerFilters(exclude_rarities=["Common"]))
    assert names(rows) == ["Mystery"]


def test_exclude_sub_types_drops_the_named_finishes(connection):
    add_card(connection, variant_id=1, name="Pikachu", sub_type="Normal")
    add_card(connection, variant_id=2, name="Charizard", sub_type="Holofoil")
    add_card(connection, variant_id=3, name="Bulbasaur", sub_type="Reverse Holofoil")

    rows = run(connection, ScreenerFilters(exclude_sub_types=["Reverse Holofoil"]))
    assert sorted(names(rows)) == ["Charizard", "Pikachu"]


def test_excluding_one_dimension_leaves_the_others_alone(connection):
    """The three exclusions are independent filters, not one combined rule."""
    add_card(connection, variant_id=1, name="Keeper", group_id=2,
             rarity="Ultra Rare", sub_type="Holofoil")
    add_card(connection, variant_id=2, name="Wrong set", group_id=1,
             rarity="Ultra Rare", sub_type="Holofoil")
    add_card(connection, variant_id=3, name="Wrong rarity", group_id=2,
             rarity="Common", sub_type="Holofoil")
    add_card(connection, variant_id=4, name="Wrong finish", group_id=2,
             rarity="Ultra Rare", sub_type="Normal")

    rows = run(
        connection,
        ScreenerFilters(
            exclude_group_ids=[1],
            exclude_rarities=["Common"],
            exclude_sub_types=["Normal"],
        ),
    )
    assert names(rows) == ["Keeper"]


def test_no_exclusions_returns_everything(connection):
    add_card(connection, variant_id=1, name="Pikachu", rarity="Common")
    add_card(connection, variant_id=2, name="Charizard", sub_type="Normal")

    assert len(run(connection, ScreenerFilters())) == 2
