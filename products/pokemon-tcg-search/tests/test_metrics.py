"""Tests for the screener metric math.

These are the product's core claims — "60% below its peak", "at the 52-week
low" — so they are tested directly rather than eyeballed on real data.
"""

from __future__ import annotations

import dataclasses

import pytest

from ingest.metrics import (
    MAX_STALENESS_DAYS,
    Observation,
    VariantMetrics,
    compute_variant_metrics,
)


def series(*pairs: tuple[int, float], low: float | None = None, high: float | None = None):
    """Build a price series from (day, market_price) pairs."""
    return [Observation(day, price, low, high) for day, price in pairs]


# ---------------------------------------------------------------------------
# Drawdown
# ---------------------------------------------------------------------------


def test_discount_from_peak_is_percent_below_the_peak():
    metrics = compute_variant_metrics(1, series((0, 100.0), (10, 35.0)), latest_day=10)

    assert metrics is not None
    assert metrics.peak_price == 100.0
    assert metrics.current_price == 35.0
    assert metrics.discount_from_peak_pct == pytest.approx(65.0)


def test_card_at_a_fresh_high_reports_zero_discount_not_negative():
    """A negative discount would sort to the top of a "most discounted" list."""
    metrics = compute_variant_metrics(1, series((0, 50.0), (10, 80.0)), latest_day=10)

    assert metrics is not None
    assert metrics.discount_from_peak_pct == 0.0
    assert metrics.peak_day == 10


def test_peak_ties_resolve_to_the_most_recent_day():
    """days_since_peak should read as "when was it last this expensive"."""
    metrics = compute_variant_metrics(
        1, series((0, 100.0), (5, 100.0), (10, 40.0)), latest_day=10
    )

    assert metrics is not None
    assert metrics.peak_day == 5
    assert metrics.days_since_peak == 5


# ---------------------------------------------------------------------------
# Trailing windows
# ---------------------------------------------------------------------------


def test_window_highs_ignore_peaks_older_than_the_window():
    """A 2-year-old spike must not contaminate the 52-week high."""
    metrics = compute_variant_metrics(
        1,
        series((0, 500.0), (400, 120.0), (700, 60.0)),
        latest_day=700,
    )

    assert metrics is not None
    # The 500.0 spike at day 0 is 700 days back: inside the recorded peak,
    # outside every trailing window.
    assert metrics.peak_price == 500.0
    assert metrics.high_52w == 120.0
    assert metrics.discount_from_peak_pct == pytest.approx(88.0)
    assert metrics.discount_from_52w_high_pct == pytest.approx(50.0)


def test_shorter_windows_nest_inside_longer_ones():
    observations = series((0, 200.0), (620, 150.0), (700, 100.0), (740, 80.0), (750, 70.0))
    metrics = compute_variant_metrics(1, observations, latest_day=750)

    assert metrics is not None
    assert metrics.high_52w >= metrics.high_26w >= metrics.high_13w
    assert metrics.discount_from_52w_high_pct >= metrics.discount_from_26w_high_pct
    assert metrics.discount_from_26w_high_pct >= metrics.discount_from_13w_high_pct


def test_pct_of_52w_range_places_price_between_low_and_high():
    observations = series((0, 100.0), (5, 50.0), (10, 75.0))
    metrics = compute_variant_metrics(1, observations, latest_day=10)

    assert metrics is not None
    assert metrics.low_52w == 50.0
    assert metrics.high_52w == 100.0
    assert metrics.pct_of_52w_range == pytest.approx(50.0)


def test_pct_of_52w_range_is_none_for_a_flat_price():
    """A flat series has no range to sit inside; 0 would falsely read "at the low"."""
    metrics = compute_variant_metrics(1, series((0, 20.0), (10, 20.0)), latest_day=10)

    assert metrics is not None
    assert metrics.pct_of_52w_range is None


# ---------------------------------------------------------------------------
# Momentum
# ---------------------------------------------------------------------------


def test_momentum_uses_the_last_price_at_or_before_the_lookback_day():
    """Gaps are normal in the feed, so lookbacks must not require an exact day."""
    observations = series((0, 100.0), (20, 90.0), (33, 45.0))
    metrics = compute_variant_metrics(1, observations, latest_day=33)

    assert metrics is not None
    # 30 days back is day 3; the most recent price at or before that is day 0.
    assert metrics.change_30d_pct == pytest.approx(-55.0)
    # 7 days back is day 26; carries forward from day 20.
    assert metrics.change_7d_pct == pytest.approx((45.0 - 90.0) / 90.0 * 100.0)


def test_momentum_is_none_when_history_predates_the_lookback():
    metrics = compute_variant_metrics(1, series((10, 30.0), (12, 25.0)), latest_day=12)

    assert metrics is not None
    assert metrics.change_90d_pct is None


# ---------------------------------------------------------------------------
# Guards
# ---------------------------------------------------------------------------


def test_stale_variants_are_dropped():
    """Quoting a months-old price as "current" is the worst failure mode here."""
    stale = compute_variant_metrics(
        1, series((0, 10.0), (100, 10.0)), latest_day=100 + MAX_STALENESS_DAYS + 1
    )
    fresh = compute_variant_metrics(
        1, series((0, 10.0), (100, 10.0)), latest_day=100 + MAX_STALENESS_DAYS
    )

    assert stale is None
    assert fresh is not None


def test_empty_series_yields_no_metrics():
    assert compute_variant_metrics(1, [], latest_day=10) is None


def test_release_spike_flag_marks_peaks_set_near_release():
    """"90% below ATH" is meaningless when the ATH was release-week hype."""
    observations = series((5, 300.0), (200, 30.0))

    spiked = compute_variant_metrics(1, observations, latest_day=200, set_released_day=0)
    organic = compute_variant_metrics(1, observations, latest_day=200, set_released_day=-400)

    assert spiked is not None and organic is not None
    assert spiked.peak_within_30d_of_release == 1
    assert organic.peak_within_30d_of_release == 0


def test_peak_is_first_observation_flags_history_truncation():
    """If the peak is our oldest datapoint, the real peak may predate our data."""
    metrics = compute_variant_metrics(1, series((0, 100.0), (50, 20.0)), latest_day=50)

    assert metrics is not None
    assert metrics.peak_is_first_observation == 1


def test_history_quality_fields_describe_the_series():
    observations = series((100, 10.0), (110, 11.0), (120, 12.0), (130, 13.0))
    metrics = compute_variant_metrics(1, observations, latest_day=130)

    assert metrics is not None
    assert metrics.observation_count == 4
    assert metrics.first_day == 100
    assert metrics.history_days == 31
    # Days 101..130 inclusive is the 30-day window: 110, 120, 130 land inside.
    assert metrics.observation_count_30d == 3
    assert metrics.coverage_30d_pct == pytest.approx(10.0)


def test_spread_uses_the_latest_low_and_high_listings():
    observations = series((0, 10.0), (10, 20.0), low=15.0, high=25.0)
    metrics = compute_variant_metrics(1, observations, latest_day=10)

    assert metrics is not None
    assert metrics.spread_pct == pytest.approx(50.0)


def test_bad_current_price_shows_up_as_far_below_the_90_day_median():
    """The real failure seen in production data: a ~$600 vintage single whose
    latest market price is reported as $0.99. That is a feed error, and left
    unguarded it becomes a fake 99.9% discount at the top of the screener."""
    history = [(day, 600.0) for day in range(0, 96, 5)]
    metrics = compute_variant_metrics(1, series(*history, (96, 0.99)), latest_day=96)

    assert metrics is not None
    assert metrics.median_price_90d == pytest.approx(600.0)
    assert metrics.current_vs_median_90d_pct < 1.0


def test_genuine_decline_stays_near_its_median():
    """A real slide must not be mistaken for a feed error: as the price falls,
    the trailing median falls with it."""
    gradual = [(day, 100.0 - day * 0.5) for day in range(0, 100, 5)]
    metrics = compute_variant_metrics(1, series(*gradual), latest_day=95)

    assert metrics is not None
    # Down ~48% over the window, yet still well above the outlier floor.
    assert metrics.discount_from_peak_pct > 40
    assert metrics.current_vs_median_90d_pct > 50


def test_median_ignores_a_single_absurd_spike():
    """A mean would be dragged by the $9,000 print; a median must not be."""
    history = [(day, 20.0) for day in range(0, 90, 5)]
    metrics = compute_variant_metrics(1, series(*history, (91, 9000.0), (92, 20.0)), latest_day=92)

    assert metrics is not None
    assert metrics.median_price_90d == pytest.approx(20.0)


def test_frozen_price_reports_a_single_distinct_price():
    """TCGplayer pins market price when nothing sells. A card quoting one value
    for 90 days has not been trading, however complete its coverage looks."""
    frozen = series(*[(day, 40.0) for day in range(0, 100, 5)])
    metrics = compute_variant_metrics(1, frozen, latest_day=95)

    assert metrics is not None
    assert metrics.distinct_prices_90d == 1
    assert metrics.coverage_30d_pct > 0  # coverage alone cannot spot this
    assert metrics.days_since_price_change is None


def test_active_price_reports_many_distinct_prices():
    active = series(*[(day, 40.0 + day * 0.3) for day in range(0, 100, 5)])
    metrics = compute_variant_metrics(1, active, latest_day=95)

    assert metrics is not None
    assert metrics.distinct_prices_90d > 10


def test_distinct_prices_ignores_movement_older_than_90_days():
    observations = series((0, 10.0), (100, 20.0), (300, 55.0), (350, 55.0), (380, 55.0))
    metrics = compute_variant_metrics(1, observations, latest_day=380)

    assert metrics is not None
    # Only the flat 55.0 stretch falls inside the trailing 90 days.
    assert metrics.distinct_prices_90d == 1


def test_days_since_price_change_finds_the_last_different_price():
    observations = series((0, 10.0), (40, 25.0), (60, 25.0), (90, 25.0))
    metrics = compute_variant_metrics(1, observations, latest_day=90)

    assert metrics is not None
    # The price last differed on day 0, which is 90 days before the latest day.
    assert metrics.days_since_price_change == 90


def test_spread_is_none_without_listing_bounds():
    metrics = compute_variant_metrics(1, series((0, 10.0), (10, 20.0)), latest_day=10)

    assert metrics is not None
    assert metrics.spread_pct is None


# ---------------------------------------------------------------------------
# Schema coupling
# ---------------------------------------------------------------------------


def test_metrics_field_order_matches_the_insert_column_list():
    """rebuild_metrics inserts via astuple(), so order is load-bearing.

    Reordering a VariantMetrics field would otherwise silently write, say,
    high_26w into the high_13w column.
    """
    from ingest.metrics import _INSERT_COLUMNS

    columns = [name.strip() for name in _INSERT_COLUMNS.split(",")]
    fields = [field.name for field in dataclasses.fields(VariantMetrics)]

    assert fields == columns
