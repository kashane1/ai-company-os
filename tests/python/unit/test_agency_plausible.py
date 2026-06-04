"""Tests for the Plausible Stats adapter (G10)."""

from __future__ import annotations

import pytest

from packages.agency.plausible import (
    FORM_LEAD_GOAL,
    GoalNotConfigured,
    MonthlyStats,
    StatsClient,
    fetch_monthly_stats,
    month_to_date_range,
    site_has_goal,
)


def _row(metrics, dimensions=None):
    return {"results": [{"dimensions": dimensions or [], "metrics": metrics}]}


class FakeStats:
    """Routes the three query shapes the adapter sends to canned responses."""

    def __init__(self, *, traffic, goals, leads) -> None:
        self.traffic, self.goals, self.leads = traffic, goals, leads
        self.bodies: list[dict] = []

    def query(self, body):
        self.bodies.append(body)
        if "dimensions" in body:  # the goal-presence probe
            return self.goals
        if "filters" in body:  # the goal-filtered lead query
            return self.leads
        return self.traffic  # plain traffic


def test_protocol_smoke() -> None:
    assert isinstance(FakeStats(traffic={}, goals={}, leads={}), StatsClient)


def test_month_to_date_range() -> None:
    assert month_to_date_range("2026-05") == ["2026-05-01", "2026-05-31"]
    assert month_to_date_range("2026-02") == ["2026-02-01", "2026-02-28"]  # non-leap


def test_fetch_returns_real_numbers() -> None:
    client = FakeStats(
        traffic=_row([342, 1187]),
        goals=_row([7], dimensions=[FORM_LEAD_GOAL]),
        leads=_row([7, 9]),
    )
    stats = fetch_monthly_stats(client, site_id="joe.com", date_range=["2026-05-01", "2026-05-31"])
    assert stats == MonthlyStats(visits=342, pageviews=1187, form_leads=7)


def test_goal_present_but_zero_conversions_is_real_zero() -> None:
    client = FakeStats(
        traffic=_row([100, 200]),
        goals=_row([0], dimensions=[FORM_LEAD_GOAL]),
        leads={"results": []},  # goal exists, no conversions this month
    )
    stats = fetch_monthly_stats(client, site_id="joe.com", date_range=["2026-05-01", "2026-05-31"])
    assert stats.form_leads == 0


def test_missing_goal_fails_loud() -> None:
    client = FakeStats(
        traffic=_row([100, 200]),
        goals=_row([2], dimensions=["Some Other Goal"]),  # no Form Lead
        leads=_row([5, 5]),
    )
    with pytest.raises(GoalNotConfigured):
        fetch_monthly_stats(client, site_id="joe.com", date_range=["2026-05-01", "2026-05-31"])


def test_site_has_goal() -> None:
    yes = FakeStats(traffic={}, goals=_row([1], dimensions=[FORM_LEAD_GOAL]), leads={})
    no = FakeStats(traffic={}, goals=_row([1], dimensions=["Other"]), leads={})
    rng = ["2026-05-01", "2026-05-31"]
    assert site_has_goal(yes, "joe.com", rng) is True
    assert site_has_goal(no, "joe.com", rng) is False
