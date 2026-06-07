"""Owner-friendly monthly retainer reports."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from packages.agency.plausible import StatsClient


@dataclass(frozen=True)
class MonthlyMetrics:
    product_id: str
    month: str
    visits: int = 0
    form_leads: int = 0
    leads_tracked: bool = True
    # Tap-to-call clicks (Plausible "Call Click" goal). None = not tracked. An honest,
    # free proxy for calls — taps on the phone link, NOT verified calls.
    phone_clicks: int | None = None
    # Bookings for the month, from a managed-booking dashboard. None = not applicable
    # (no managed booking). Operator-supplied (no booking-platform API integration).
    bookings: int | None = None
    # Verified calls from real call tracking (e.g. CallRail). None/False until added.
    calls_tracked: bool = False
    calls: int | None = None
    completed_work: list[str] = field(default_factory=list)
    recommended_action: str = ""
    billing_status: str = ""

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> "MonthlyMetrics":
        def _opt_int(key: str) -> int | None:
            return int(payload[key]) if payload.get(key) is not None else None

        return cls(
            product_id=str(payload["product_id"]),
            month=str(payload["month"]),
            visits=int(payload.get("visits", 0)),
            form_leads=int(payload.get("form_leads", 0)),
            leads_tracked=bool(payload.get("leads_tracked", True)),
            phone_clicks=_opt_int("phone_clicks"),
            bookings=_opt_int("bookings"),
            calls_tracked=bool(payload.get("calls_tracked", False)),
            calls=_opt_int("calls"),
            completed_work=[str(item) for item in list(payload.get("completed_work", []))],
            recommended_action=str(payload.get("recommended_action", "")),
            billing_status=str(payload.get("billing_status", "")),
        )


def load_monthly_metrics(path: Path) -> MonthlyMetrics:
    return MonthlyMetrics.from_dict(json.loads(path.read_text(encoding="utf-8")))


def metrics_from_plausible(
    client: "StatsClient",
    *,
    product_id: str,
    month: str,
    site_id: str,
    completed_work: list[str] | None = None,
    recommended_action: str = "",
    billing_status: str = "",
    bookings: int | None = None,
    calls_tracked: bool = False,
    calls: int | None = None,
) -> MonthlyMetrics:
    """Build :class:`MonthlyMetrics` with real visits + form-lead + tap-to-call data.

    This is the wire the report was missing: traffic and conversions come from the
    analytics adapter, not a hand-keyed JSON. Tap-to-call clicks come from the
    optional ``Call Click`` Plausible goal (a free, honest proxy for calls — taps,
    not verified calls); ``None`` when that goal isn't set up. Bookings stay
    operator-supplied (no booking-platform API). Verified calls (CallRail) too.

    If the ``Form Lead`` goal isn't configured we still report real traffic, mark
    leads as untracked (rendered "Not tracked yet", never a fake 0), and surface
    "configure the goal" as the recommended action ([D5] — don't report 0 leads
    as if they were real).
    """
    from packages.agency.plausible import (
        CALL_CLICK_GOAL,
        FORM_LEAD_GOAL,
        GoalNotConfigured,
        fetch_goal_conversions,
        fetch_monthly_stats,
        fetch_traffic,
        month_to_date_range,
    )

    date_range = month_to_date_range(month)
    leads_tracked = True
    action = recommended_action
    try:
        stats = fetch_monthly_stats(client, site_id=site_id, date_range=date_range)
        visits, form_leads = stats.visits, stats.form_leads
    except GoalNotConfigured:
        visits, _ = fetch_traffic(client, site_id=site_id, date_range=date_range)
        form_leads = 0
        leads_tracked = False
        note = (
            f"Configure the {FORM_LEAD_GOAL!r} goal in Plausible so form leads "
            "are tracked next month."
        )
        action = f"{action} {note}".strip() if action else note

    phone_clicks = fetch_goal_conversions(
        client, site_id=site_id, date_range=date_range, goal=CALL_CLICK_GOAL
    )

    return MonthlyMetrics(
        product_id=product_id,
        month=month,
        visits=visits,
        form_leads=form_leads,
        leads_tracked=leads_tracked,
        phone_clicks=phone_clicks,
        bookings=bookings,
        calls_tracked=calls_tracked,
        calls=calls,
        completed_work=list(completed_work or []),
        recommended_action=action,
        billing_status=billing_status,
    )


def render_monthly_report(metrics: MonthlyMetrics, *, client_name: str) -> str:
    leads = str(metrics.form_leads) if metrics.leads_tracked else "Not tracked yet"
    completed = "\n".join(f"- {item}" for item in metrics.completed_work) or "- Routine monitoring"
    recommended = metrics.recommended_action or "Keep the current plan running and review next month's lead volume."

    # Adaptive Results: always visits + form leads; show conversion lines only when
    # they have a real source, so the report never carries a hollow "Calls" section.
    results = [
        f"- **Website visits:** {metrics.visits}",
        f"- **Form leads:** {leads}",
    ]
    phone = str(metrics.phone_clicks) if metrics.phone_clicks is not None else "Not tracked yet"
    results.append(f"- **Phone taps (click-to-call):** {phone}")
    if metrics.bookings is not None:
        results.append(f"- **Bookings:** {metrics.bookings}")
    if metrics.calls_tracked and metrics.calls is not None:
        results.append(f"- **Calls (tracked):** {metrics.calls}")
    if metrics.billing_status:
        results.append(f"- **Billing status:** {metrics.billing_status}")

    return "\n".join(
        [
            f"# Monthly Report — {client_name}",
            "",
            f"**Month:** {metrics.month}",
            "",
            "## Results",
            "",
            *results,
            "",
            "## Work completed",
            "",
            completed,
            "",
            "## Recommended next action",
            "",
            recommended,
            "",
            "> Draft report. Operator reviews and forwards manually.",
            "",
        ]
    )


def write_monthly_report(
    docs_root: Path,
    metrics: MonthlyMetrics,
    *,
    client_name: str,
) -> Path:
    reports = docs_root / "reports"
    reports.mkdir(parents=True, exist_ok=True)
    path = reports / f"{metrics.month}.md"
    path.write_text(render_monthly_report(metrics, client_name=client_name), encoding="utf-8")
    return path
