"""Derive screener metrics (drawdowns, window highs, momentum) per variant.

Implementation note: this streams `price_observations` ordered by
(variant_id, day) — which is the table's clustered order, so it is one
sequential scan with no extra index — and hands each variant's complete series
to :func:`compute_variant_metrics`, a pure function. Doing the arithmetic in
Python rather than one large SQL statement keeps the definitions readable and
unit-testable, which matters more here than shaving seconds off a batch job.

Metric vocabulary, stated once so the UI and API can stay consistent:

    peak_price      Highest daily market price in our recorded window. Our
                    history starts 2024-02-08, so this is a *recorded* peak,
                    not a true all-time high. Never label it "ATH" in the UI.
    high_52w/26w/13w  Highest daily market price in the trailing window. Fully
                    defensible — the window fits inside our history.
    discount_*      Percent below that reference: 60.0 == "60% below".
    pct_of_52w_range  0 == sitting at the 52-week low, 100 == at the high.
"""

from __future__ import annotations

import datetime as dt
import sqlite3
from dataclasses import astuple, dataclass
from typing import Iterable, Iterator, Sequence

from .config import DAY_EPOCH, date_from_day_index

# Trailing windows, in days.
WINDOW_52W = 365
WINDOW_26W = 182
WINDOW_13W = 91

# A variant whose most recent observation is older than this is treated as
# no longer priced: reporting a "current price" from stale data would mislead.
MAX_STALENESS_DAYS = 7

# How soon after a set's release a peak counts as a release-week spike.
RELEASE_SPIKE_WINDOW_DAYS = 30


@dataclass(frozen=True)
class Observation:
    day: int
    market_price: float
    low_price: float | None
    high_price: float | None


@dataclass(frozen=True)
class VariantMetrics:
    variant_id: int
    as_of_day: int
    current_price: float
    peak_price: float
    peak_day: int
    high_52w: float
    high_26w: float
    high_13w: float
    low_52w: float
    discount_from_peak_pct: float
    discount_from_52w_high_pct: float
    discount_from_26w_high_pct: float
    discount_from_13w_high_pct: float
    pct_of_52w_range: float | None
    change_7d_pct: float | None
    change_30d_pct: float | None
    change_90d_pct: float | None
    observation_count: int
    observation_count_30d: int
    first_day: int
    history_days: int
    days_since_peak: int
    spread_pct: float | None
    coverage_30d_pct: float
    peak_is_first_observation: int
    peak_within_30d_of_release: int
    distinct_prices_90d: int
    days_since_price_change: int | None
    median_price_90d: float | None
    current_vs_median_90d_pct: float | None


def _percent_below(reference: float, current: float) -> float:
    """How far `current` sits below `reference`, as a 0..100 percent.

    Clamped at zero so a card printing a fresh high reports 0% off rather than
    a negative discount, which would sort nonsensically in the screener.
    """
    if reference <= 0:
        return 0.0
    return max(0.0, (reference - current) / reference * 100.0)


def _median(values: Sequence[float]) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    middle = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[middle]
    return (ordered[middle - 1] + ordered[middle]) / 2.0


def _price_on_or_before(series: Sequence[Observation], target_day: int) -> float | None:
    """Most recent market price at or before `target_day`.

    Series are short (<= ~900 points) and already sorted, so a reverse linear
    scan beats the overhead of bisect bookkeeping here.
    """
    for observation in reversed(series):
        if observation.day <= target_day:
            return observation.market_price
    return None


def _percent_change(previous: float | None, current: float) -> float | None:
    if previous is None or previous <= 0:
        return None
    return (current - previous) / previous * 100.0


def compute_variant_metrics(
    variant_id: int,
    series: Sequence[Observation],
    *,
    latest_day: int,
    set_released_day: int | None = None,
) -> VariantMetrics | None:
    """Compute every screener metric for one variant's price series.

    Returns None when the series cannot support a screener row: no
    observations, or a last observation too old for `current_price` to mean
    anything.
    """
    if not series:
        return None

    last = series[-1]
    if latest_day - last.day > MAX_STALENESS_DAYS:
        return None

    current_price = last.market_price
    if current_price <= 0:
        return None

    # Peak. On ties take the most recent occurrence: "days since the price was
    # last this high" is the useful reading for a drawdown screener.
    peak_price = max(observation.market_price for observation in series)
    peak_day = max(
        observation.day for observation in series if observation.market_price == peak_price
    )

    def window_high(days: int) -> float:
        cutoff = latest_day - days
        prices = [o.market_price for o in series if o.day > cutoff]
        return max(prices) if prices else current_price

    cutoff_52w = latest_day - WINDOW_52W
    prices_52w = [o.market_price for o in series if o.day > cutoff_52w]
    high_52w = max(prices_52w) if prices_52w else current_price
    low_52w = min(prices_52w) if prices_52w else current_price

    high_26w = window_high(WINDOW_26W)
    high_13w = window_high(WINDOW_13W)

    span_52w = high_52w - low_52w
    pct_of_52w_range = (current_price - low_52w) / span_52w * 100.0 if span_52w > 0 else None

    cutoff_30d = latest_day - 30
    observations_30d = [o for o in series if o.day > cutoff_30d]

    spread_pct = None
    if last.high_price is not None and last.low_price is not None and current_price > 0:
        if last.high_price >= last.low_price:
            spread_pct = (last.high_price - last.low_price) / current_price * 100.0

    # Price movement. A market price that never changes is a stale quote, not a
    # stable market: TCGplayer holds the last value when nothing sells.
    cutoff_90d = latest_day - WINDOW_13W
    prices_90d = [o.market_price for o in series if o.day > cutoff_90d]
    distinct_prices_90d = len(set(prices_90d))

    # Median, not mean: the point is to be unmovable by the same outliers this
    # is meant to detect.
    median_price_90d = _median(prices_90d)
    current_vs_median_90d_pct = (
        current_price / median_price_90d * 100.0
        if median_price_90d and median_price_90d > 0
        else None
    )

    days_since_price_change = None
    for observation in reversed(series):
        if observation.market_price != current_price:
            days_since_price_change = latest_day - observation.day
            break

    peak_within_release_window = 0
    if set_released_day is not None:
        peak_within_release_window = int(
            peak_day - set_released_day <= RELEASE_SPIKE_WINDOW_DAYS
        )

    return VariantMetrics(
        variant_id=variant_id,
        as_of_day=last.day,
        current_price=current_price,
        peak_price=peak_price,
        peak_day=peak_day,
        high_52w=high_52w,
        high_26w=high_26w,
        high_13w=high_13w,
        low_52w=low_52w,
        discount_from_peak_pct=_percent_below(peak_price, current_price),
        discount_from_52w_high_pct=_percent_below(high_52w, current_price),
        discount_from_26w_high_pct=_percent_below(high_26w, current_price),
        discount_from_13w_high_pct=_percent_below(high_13w, current_price),
        pct_of_52w_range=pct_of_52w_range,
        change_7d_pct=_percent_change(_price_on_or_before(series, latest_day - 7), current_price),
        change_30d_pct=_percent_change(_price_on_or_before(series, latest_day - 30), current_price),
        change_90d_pct=_percent_change(_price_on_or_before(series, latest_day - 90), current_price),
        observation_count=len(series),
        observation_count_30d=len(observations_30d),
        first_day=series[0].day,
        history_days=last.day - series[0].day + 1,
        days_since_peak=latest_day - peak_day,
        spread_pct=spread_pct,
        coverage_30d_pct=len(observations_30d) / 30.0 * 100.0,
        peak_is_first_observation=int(peak_day == series[0].day),
        peak_within_30d_of_release=peak_within_release_window,
        distinct_prices_90d=distinct_prices_90d,
        days_since_price_change=days_since_price_change,
        median_price_90d=median_price_90d,
        current_vs_median_90d_pct=current_vs_median_90d_pct,
    )


# ---------------------------------------------------------------------------
# Batch rebuild
# ---------------------------------------------------------------------------


def latest_observed_day(connection: sqlite3.Connection) -> int | None:
    row = connection.execute("SELECT MAX(day) AS day FROM price_observations").fetchone()
    return row["day"] if row and row["day"] is not None else None


def _set_release_days(connection: sqlite3.Connection) -> dict[int, int]:
    """Map variant_id -> the day index of its set's release date."""
    release_days: dict[int, int] = {}
    for row in connection.execute(
        """
        SELECT v.variant_id, s.released_on
        FROM card_variants v
        JOIN cards c ON c.product_id = v.product_id
        JOIN sets  s ON s.group_id   = c.group_id
        WHERE s.released_on IS NOT NULL
        """
    ):
        try:
            released = dt.date.fromisoformat(row["released_on"])
        except (TypeError, ValueError):
            continue
        release_days[row["variant_id"]] = (released - DAY_EPOCH).days
    return release_days


def _iter_variant_series(connection: sqlite3.Connection) -> Iterator[tuple[int, list[Observation]]]:
    """Stream (variant_id, series) in clustered order — one sequential scan."""
    cursor = connection.execute(
        """
        SELECT variant_id, day, market_price, low_price, high_price
        FROM price_observations
        ORDER BY variant_id, day
        """
    )
    current_variant: int | None = None
    series: list[Observation] = []
    for variant_id, day, market_price, low_price, high_price in cursor:
        if variant_id != current_variant:
            if current_variant is not None and series:
                yield current_variant, series
            current_variant = variant_id
            series = []
        series.append(Observation(day, market_price, low_price, high_price))
    if current_variant is not None and series:
        yield current_variant, series


_INSERT_COLUMNS = (
    "variant_id, as_of_day, current_price, peak_price, peak_day, "
    "high_52w, high_26w, high_13w, low_52w, "
    "discount_from_peak_pct, discount_from_52w_high_pct, "
    "discount_from_26w_high_pct, discount_from_13w_high_pct, "
    "pct_of_52w_range, change_7d_pct, change_30d_pct, change_90d_pct, "
    "observation_count, observation_count_30d, first_day, history_days, "
    "days_since_peak, spread_pct, coverage_30d_pct, "
    "peak_is_first_observation, peak_within_30d_of_release, "
    "distinct_prices_90d, days_since_price_change, "
    "median_price_90d, current_vs_median_90d_pct"
)


def rebuild_metrics(connection: sqlite3.Connection, *, progress=None) -> int:
    """Recompute card_metrics from scratch. Returns the number of rows written."""
    latest_day = latest_observed_day(connection)
    if latest_day is None:
        raise RuntimeError("no price observations — run backfill before computing metrics")

    release_days = _set_release_days(connection)
    connection.execute("DELETE FROM card_metrics")

    placeholders = ", ".join(["?"] * len(_INSERT_COLUMNS.split(",")))
    statement = f"INSERT INTO card_metrics ({_INSERT_COLUMNS}) VALUES ({placeholders})"

    batch: list[tuple] = []
    written = 0
    scanned = 0
    for variant_id, series in _iter_variant_series(connection):
        scanned += 1
        metrics = compute_variant_metrics(
            variant_id,
            series,
            latest_day=latest_day,
            set_released_day=release_days.get(variant_id),
        )
        if metrics is None:
            continue
        batch.append(astuple(metrics))
        if len(batch) >= 5_000:
            connection.executemany(statement, batch)
            written += len(batch)
            batch.clear()
            if progress:
                progress(f"  metrics {written:,} written / {scanned:,} variants scanned")

    if batch:
        connection.executemany(statement, batch)
        written += len(batch)

    connection.commit()
    if progress:
        progress(
            f"  metrics complete: {written:,} rows from {scanned:,} variants "
            f"(as of {date_from_day_index(latest_day)})"
        )
    return written


__all__ = [
    "MAX_STALENESS_DAYS",
    "Observation",
    "VariantMetrics",
    "compute_variant_metrics",
    "latest_observed_day",
    "rebuild_metrics",
]
