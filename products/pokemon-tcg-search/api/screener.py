"""Screener query construction.

Kept separate from the HTTP layer so the filter semantics can be unit tested
without a running server, and so every SQL fragment lives in one auditable
place. All user input reaches SQLite as bound parameters; the only interpolated
strings are whitelisted column names.
"""

from __future__ import annotations

from dataclasses import dataclass, field

# Which high the discount is measured against. The UI defaults to 52w: it is
# the strongest claim our data can actually support, because a 52-week window
# fits entirely inside our recorded history.
BENCHMARKS: dict[str, tuple[str, str, str]] = {
    # key: (discount column, reference-price column, human label)
    "peak": ("discount_from_peak_pct", "peak_price", "recorded peak"),
    "52w": ("discount_from_52w_high_pct", "high_52w", "52-week high"),
    "26w": ("discount_from_26w_high_pct", "high_26w", "6-month high"),
    "13w": ("discount_from_13w_high_pct", "high_13w", "3-month high"),
}

# An empty value marks a sort whose column depends on the active benchmark, so it
# cannot be named here; build_query resolves those against resolved_benchmark().
BENCHMARK_RELATIVE_SORTS = ("discount", "reference")

SORT_COLUMNS: dict[str, str] = {
    "discount": "",  # resolved to the active benchmark's discount column
    "reference": "",  # resolved to the active benchmark's reference-price column
    "price": "current_price",
    "range_position": "pct_of_52w_range",
    "change_7d": "change_7d_pct",
    "change_30d": "change_30d_pct",
    "change_90d": "change_90d_pct",
    "peak_price": "peak_price",
    "days_since_peak": "days_since_peak",
    "price_movement": "distinct_prices_90d",
    "name": "card_name",
    "released": "released_on",
    "history": "history_days",
}

MAX_LIMIT = 200

RESULT_COLUMNS = """
    variant_id, product_id, card_name, card_number, rarity, card_type,
    hp, stage, card_class, trainer_kind,
    image_url, tcgplayer_url, sub_type, group_id, set_name, set_abbreviation,
    released_on, current_price, peak_price, peak_day, high_52w, high_26w,
    high_13w, low_52w, discount_from_peak_pct, discount_from_52w_high_pct,
    discount_from_26w_high_pct, discount_from_13w_high_pct, pct_of_52w_range,
    change_7d_pct, change_30d_pct, change_90d_pct, observation_count,
    observation_count_30d, history_days, days_since_peak, spread_pct,
    coverage_30d_pct, distinct_prices_90d, days_since_price_change,
    median_price_90d, current_vs_median_90d_pct,
    peak_is_first_observation, peak_within_30d_of_release, as_of_day
"""


@dataclass
class ScreenerFilters:
    """One screener request. Defaults are deliberately permissive except for
    the quality floors, which exist to keep junk off the first page."""

    benchmark: str = "52w"
    min_discount_pct: float | None = 25.0
    max_discount_pct: float | None = None

    # Defaults to $1: below that, a 99% discount is $0.98 of movement on a bulk
    # common. Percentage drawdown stops being meaningful and the screener fills
    # with cards nobody is deciding whether to buy.
    min_price: float | None = 1.0
    max_price: float | None = None

    search: str | None = None
    group_ids: list[int] = field(default_factory=list)
    rarities: list[str] = field(default_factory=list)
    sub_types: list[str] = field(default_factory=list)

    # The mirror of the three lists above, for the far shorter way of saying
    # "everything except these". Each pair is one control in the UI, which sends
    # only one side of it, but they stay separate fields so the API keeps a
    # single explicit vocabulary instead of a mode flag changing what a list
    # means.
    exclude_group_ids: list[int] = field(default_factory=list)
    exclude_rarities: list[str] = field(default_factory=list)
    exclude_sub_types: list[str] = field(default_factory=list)

    # Release year, inclusive, matched on the set's release date. A card has no
    # release date of its own in this feed — the set's is the only one there is,
    # which is the right answer anyway for "when did this card come out".
    min_release_year: int | None = None
    max_release_year: int | None = None

    # Card class (Pokemon / Trainer / Energy) and, for Trainers, which kind.
    # Include and exclude are separate lists rather than one signed list so the
    # UI can offer a three-state control per class without encoding tricks.
    card_classes: list[str] = field(default_factory=list)
    exclude_card_classes: list[str] = field(default_factory=list)
    trainer_kinds: list[str] = field(default_factory=list)

    # Momentum gates. max_change_7d_pct < 0 finds cards still falling;
    # min_change_7d_pct >= 0 finds ones that have stopped bleeding.
    min_change_7d_pct: float | None = None
    max_change_7d_pct: float | None = None
    min_change_30d_pct: float | None = None
    max_change_30d_pct: float | None = None

    # Quality / liquidity floors.
    min_history_days: int = 180
    min_observations_30d: int = 10
    max_spread_pct: float | None = None
    # Defaults to 5, chosen by measuring against real data: every implausible
    # row (a $427 vintage single now quoting $28, a $299 one quoting $1.38) sat
    # at 2-4 distinct prices, having stepped once from a high plateau to a low
    # one and never moved again. Raising the floor from 5 to 20 removed 400 more
    # rows without changing the top of the list, so the junk is entirely below
    # 5 and anything stricter only costs coverage.
    min_distinct_prices_90d: int = 5
    min_range_position_pct: float | None = None
    max_range_position_pct: float | None = None

    # Release-hype guards, on by default: a card 90% below a release-week
    # spike it never revisited is not a bargain, it is a normal price.
    exclude_release_spikes: bool = True
    exclude_truncated_peaks: bool = False

    # Drops rows whose current price is implausibly far below their own 90-day
    # median — a feed error, not a crash. On by default: sorted by deepest
    # discount these otherwise occupy the entire first page.
    exclude_price_outliers: bool = True
    outlier_floor_pct: float = 25.0

    sort: str = "discount"
    descending: bool = True
    limit: int = 50
    offset: int = 0

    def resolved_benchmark(self) -> tuple[str, str, str]:
        return BENCHMARKS.get(self.benchmark, BENCHMARKS["52w"])


def _escape_like(value: str) -> str:
    """Neutralise LIKE wildcards in user text.

    Without this, searching `%` matches every card and `_` matches any single
    character, so the result count silently stops reflecting what was typed.
    Backslash goes first, otherwise it would escape the escapes we add.
    """
    for character in ("\\", "%", "_"):
        value = value.replace(character, f"\\{character}")
    return value


def build_query(filters: ScreenerFilters) -> tuple[str, str, list[object]]:
    """Return (rows SQL, count SQL, bound parameters).

    Both statements share the same WHERE clause and parameter list so the total
    can never disagree with the page.
    """
    discount_column, reference_column, _label = filters.resolved_benchmark()

    clauses: list[str] = []
    params: list[object] = []

    def add(clause: str, *values: object) -> None:
        clauses.append(clause)
        params.extend(values)

    if filters.min_discount_pct is not None:
        add(f"{discount_column} >= ?", filters.min_discount_pct)
    if filters.max_discount_pct is not None:
        add(f"{discount_column} <= ?", filters.max_discount_pct)

    if filters.min_price is not None:
        add("current_price >= ?", filters.min_price)
    if filters.max_price is not None:
        add("current_price <= ?", filters.max_price)

    if filters.search:
        # Match the card name or its set, so "Charizard" and "Evolving Skies"
        # both work in the one search box the UI exposes.
        pattern = f"%{_escape_like(filters.search.strip())}%"
        add(
            "(card_name LIKE ? ESCAPE '\\' OR set_name LIKE ? ESCAPE '\\')",
            pattern,
            pattern,
        )

    if filters.group_ids:
        add(
            f"group_id IN ({', '.join(['?'] * len(filters.group_ids))})",
            *filters.group_ids,
        )
    if filters.rarities:
        add(
            f"rarity IN ({', '.join(['?'] * len(filters.rarities))})",
            *filters.rarities,
        )
    if filters.sub_types:
        add(
            f"sub_type IN ({', '.join(['?'] * len(filters.sub_types))})",
            *filters.sub_types,
        )

    if filters.exclude_group_ids:
        add(
            f"group_id NOT IN ({', '.join(['?'] * len(filters.exclude_group_ids))})",
            *filters.exclude_group_ids,
        )
    if filters.exclude_rarities:
        # rarity is the one nullable column of the three, so it needs the same
        # care as card_class: a card the feed never graded is not secretly the
        # rarity being dropped, and a bare NOT IN would take it out too.
        add(
            "(rarity IS NULL OR rarity NOT IN "
            f"({', '.join(['?'] * len(filters.exclude_rarities))}))",
            *filters.exclude_rarities,
        )
    if filters.exclude_sub_types:
        add(
            f"sub_type NOT IN ({', '.join(['?'] * len(filters.exclude_sub_types))})",
            *filters.exclude_sub_types,
        )

    # ISO date text compares correctly and lets SQLite use sets_released_idx,
    # which strftime()/substr() on the column would not.
    if filters.min_release_year is not None:
        add("released_on >= ?", f"{filters.min_release_year:04d}-01-01")
    if filters.max_release_year is not None:
        add("released_on <= ?", f"{filters.max_release_year:04d}-12-31")

    if filters.card_classes:
        add(
            f"card_class IN ({', '.join(['?'] * len(filters.card_classes))})",
            *filters.card_classes,
        )
    if filters.exclude_card_classes:
        # A NULL card_class means the feed told us nothing, so it is not
        # excluded by name — being unclassifiable is not the same as being a
        # Trainer. `NOT IN` alone would drop those rows, hence the IS NULL arm.
        add(
            "(card_class IS NULL OR card_class NOT IN "
            f"({', '.join(['?'] * len(filters.exclude_card_classes))}))",
            *filters.exclude_card_classes,
        )
    if filters.trainer_kinds:
        add(
            f"trainer_kind IN ({', '.join(['?'] * len(filters.trainer_kinds))})",
            *filters.trainer_kinds,
        )

    for column, low, high in (
        ("change_7d_pct", filters.min_change_7d_pct, filters.max_change_7d_pct),
        ("change_30d_pct", filters.min_change_30d_pct, filters.max_change_30d_pct),
        (
            "pct_of_52w_range",
            filters.min_range_position_pct,
            filters.max_range_position_pct,
        ),
    ):
        # NULL means "not computable", which is not the same as "passes". An
        # explicit NOT NULL keeps unknowns out of a filtered result.
        if low is not None:
            add(f"({column} IS NOT NULL AND {column} >= ?)", low)
        if high is not None:
            add(f"({column} IS NOT NULL AND {column} <= ?)", high)

    if filters.min_history_days:
        add("history_days >= ?", filters.min_history_days)
    if filters.min_observations_30d:
        add("observation_count_30d >= ?", filters.min_observations_30d)
    if filters.max_spread_pct is not None:
        add("(spread_pct IS NOT NULL AND spread_pct <= ?)", filters.max_spread_pct)
    if filters.min_distinct_prices_90d:
        add("distinct_prices_90d >= ?", filters.min_distinct_prices_90d)

    if filters.exclude_price_outliers:
        # A NULL ratio means we had no 90-day window to compare against, which
        # is itself too little evidence to trust a headline discount.
        add(
            "(current_vs_median_90d_pct IS NOT NULL AND current_vs_median_90d_pct >= ?)",
            filters.outlier_floor_pct,
        )

    if filters.exclude_release_spikes:
        add("peak_within_30d_of_release = 0")
    if filters.exclude_truncated_peaks:
        add("peak_is_first_observation = 0")

    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""

    # "discount" and "reference" name a *window*, not a column: which column they
    # mean moves with the benchmark, so they are resolved here rather than in the
    # table. Anything unrecognised still falls back to the benchmark's discount.
    if filters.sort == "reference":
        sort_column = reference_column
    else:
        sort_column = SORT_COLUMNS.get(filters.sort) or discount_column
    direction = "DESC" if filters.descending else "ASC"
    # variant_id breaks ties so pagination is stable across requests.
    order = f"ORDER BY {sort_column} IS NULL, {sort_column} {direction}, variant_id ASC"

    limit = max(1, min(filters.limit, MAX_LIMIT))
    offset = max(0, filters.offset)

    rows_sql = (
        f"SELECT {RESULT_COLUMNS} FROM screener_rows {where} {order} "
        f"LIMIT {limit} OFFSET {offset}"
    )
    count_sql = f"SELECT COUNT(*) FROM screener_rows {where}"
    return rows_sql, count_sql, params


__all__ = [
    "BENCHMARKS",
    "BENCHMARK_RELATIVE_SORTS",
    "MAX_LIMIT",
    "SORT_COLUMNS",
    "ScreenerFilters",
    "build_query",
]
