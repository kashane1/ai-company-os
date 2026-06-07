"""Plausible Stats API adapter (Agency layer, G10 — Package C reporting data).

Feeds real monthly visit/lead numbers into ``monthly_report.MonthlyMetrics`` so
the report stops shipping zeros. The HTTP call is behind a :class:`StatsClient`
seam (a fake drives the tests — no network).

Lead counts come from a Plausible **goal** ("Form Lead", a custom event the
client site fires on submit). If that goal isn't configured, lead data doesn't
exist — and we **fail loud** rather than report ``0`` as if it were real ([D5]).
"""

from __future__ import annotations

import calendar
import json
import urllib.request
from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from packages.config.settings import (
    PLAUSIBLE_API_KEY_ENV_VAR,
    PLAUSIBLE_BASE_URL_ENV_VAR,
    get_api_key,
)

# The custom-event goal the client site must fire on form submit.
FORM_LEAD_GOAL = "Form Lead"
_DEFAULT_BASE_URL = "https://plausible.io"


class GoalNotConfigured(RuntimeError):
    """The 'Form Lead' goal is absent — don't report 0 leads as real ([D5])."""


@runtime_checkable
class StatsClient(Protocol):
    def query(self, body: dict[str, object]) -> dict[str, object]: ...


@dataclass(frozen=True)
class PlausibleStatsClient:
    api_key: str
    base_url: str = _DEFAULT_BASE_URL
    timeout: float = 15.0

    def query(self, body: dict[str, object]) -> dict[str, object]:
        request = urllib.request.Request(
            f"{self.base_url.rstrip('/')}/api/v2/query",
            data=json.dumps(body).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=self.timeout) as resp:  # noqa: S310
            return json.loads(resp.read().decode("utf-8"))


@dataclass(frozen=True)
class MonthlyStats:
    visits: int
    pageviews: int
    form_leads: int


def default_stats_client() -> PlausibleStatsClient | None:
    """Build a client from the environment, or None if no key is configured."""
    key = get_api_key(PLAUSIBLE_API_KEY_ENV_VAR)
    if not key:
        return None
    base = get_api_key(PLAUSIBLE_BASE_URL_ENV_VAR) or _DEFAULT_BASE_URL
    return PlausibleStatsClient(api_key=key, base_url=base)


def month_to_date_range(month: str) -> list[str]:
    """'YYYY-MM' -> ['YYYY-MM-01', 'YYYY-MM-<last day>'] (deterministic, no clock)."""
    year, mon = (int(part) for part in month.split("-", 1))
    last = calendar.monthrange(year, mon)[1]
    return [f"{year:04d}-{mon:02d}-01", f"{year:04d}-{mon:02d}-{last:02d}"]


def _first_metrics(result: dict[str, object]) -> list[int]:
    rows = result.get("results") or []
    if not rows:
        return []
    metrics = rows[0].get("metrics") if isinstance(rows[0], dict) else None
    return [int(m) for m in metrics] if isinstance(metrics, list) else []


def site_has_goal(
    client: StatsClient, site_id: str, date_range: list[str], goal: str = FORM_LEAD_GOAL
) -> bool:
    """True if ``goal`` is a configured goal on the site (group by event:goal)."""
    result = client.query(
        {
            "site_id": site_id,
            "metrics": ["events"],
            "date_range": date_range,
            "dimensions": ["event:goal"],
        }
    )
    names = {
        str(row["dimensions"][0])
        for row in (result.get("results") or [])
        if isinstance(row, dict) and row.get("dimensions")
    }
    return goal in names


def fetch_traffic(
    client: StatsClient, *, site_id: str, date_range: list[str]
) -> tuple[int, int]:
    """(visits, pageviews) for the date range — traffic only, no goal needed.

    Used both by :func:`fetch_monthly_stats` and as the fallback when the lead
    goal is absent: traffic is real even when conversion tracking isn't set up.
    """
    traffic = _first_metrics(
        client.query(
            {"site_id": site_id, "metrics": ["visitors", "pageviews"], "date_range": date_range}
        )
    )
    visits = traffic[0] if len(traffic) > 0 else 0
    pageviews = traffic[1] if len(traffic) > 1 else 0
    return visits, pageviews


def fetch_monthly_stats(
    client: StatsClient,
    *,
    site_id: str,
    date_range: list[str],
    goal: str = FORM_LEAD_GOAL,
) -> MonthlyStats:
    """Visitors + pageviews + form-lead conversions for the date range.

    Raises :class:`GoalNotConfigured` if ``goal`` isn't set up (so a missing goal
    is surfaced as an action item, never reported as a real zero).
    """
    visits, pageviews = fetch_traffic(client, site_id=site_id, date_range=date_range)

    if not site_has_goal(client, site_id, date_range, goal):
        raise GoalNotConfigured(
            f"site {site_id!r} has no {goal!r} goal — configure it in Plausible and "
            "fire plausible('Form Lead') on form submit before reporting leads"
        )

    leads = _first_metrics(
        client.query(
            {
                "site_id": site_id,
                "metrics": ["visitors", "events"],
                "date_range": date_range,
                "filters": [["is", "event:goal", [goal]]],
            }
        )
    )
    form_leads = leads[0] if leads else 0
    return MonthlyStats(visits=visits, pageviews=pageviews, form_leads=form_leads)
