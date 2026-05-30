"""Discovery dashboard — the operator dashboard's first panel (D3).

The full operator dashboard is described architecturally but deliberately not
scaffolded, to avoid speculative frontend. This is its natural first panel: a
read-only *discovery view* over the records the loop already produces — the
ranked opportunity inbox plus discovery-run status/history — now that runs and
opportunities live in the same control plane (E2/E3).

The design keeps the data and the rendering separate and dependency-free:

* ``build_dashboard`` reads two repository seams (opportunities + runs) and
  returns a plain ``DiscoveryDashboardView`` dataclass. It's pure and injectable,
  so it's testable with file/in-memory repos and has no web or DB dependency.
* ``render_html`` turns that view into a single self-contained HTML page (inline
  CSS, no JS, no external assets) the API layer can serve as-is.

The FastAPI wrapper (``apps/api/discovery_endpoint.py``) is a thin adapter that
defaults the repos to the control-plane stores and serves the JSON + HTML.
"""

from __future__ import annotations

import html
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Callable, Protocol

from packages.discovery.run import DiscoveryRunReport
from packages.schemas.opportunity import OpportunityRecord


class _OpportunityLister(Protocol):
    def list(self) -> list[OpportunityRecord]:
        ...


class _RunLister(Protocol):
    def latest(self) -> DiscoveryRunReport | None:
        ...


@dataclass(frozen=True)
class InboxRow:
    id: str
    title: str
    audience: str
    connector: str
    status: str
    score: float | None
    confidence: float | None


@dataclass(frozen=True)
class RunRow:
    run_id: str
    status: str
    signals_ingested: int
    sources_hit: dict[str, int]
    queries: list[str]
    started_at: str
    finished_at: str

    @property
    def running(self) -> bool:
        return not self.finished_at


@dataclass(frozen=True)
class DiscoveryDashboardView:
    generated_at: str
    total_opportunities: int
    status_counts: dict[str, int] = field(default_factory=dict)
    inbox: list[InboxRow] = field(default_factory=list)  # ranked, best first
    latest_run: RunRow | None = None
    recent_runs: list[RunRow] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return {
            "generated_at": self.generated_at,
            "total_opportunities": self.total_opportunities,
            "status_counts": dict(self.status_counts),
            "inbox": [row.__dict__ for row in self.inbox],
            "latest_run": self.latest_run.__dict__ if self.latest_run else None,
            "recent_runs": [row.__dict__ for row in self.recent_runs],
        }


def _to_run_row(report: DiscoveryRunReport) -> RunRow:
    return RunRow(
        run_id=report.run_id,
        status=report.status,
        signals_ingested=report.signals_ingested,
        sources_hit=dict(report.sources_hit),
        queries=list(report.queries),
        started_at=report.started_at,
        finished_at=report.finished_at,
    )


def _score_key(record: OpportunityRecord) -> tuple[int, float, str]:
    # Mirror OpportunityStore ranking: scored first (NULLs last), highest score,
    # newest as tiebreaker. Works whether the repo pre-sorts or not.
    has_score = 0 if record.score is None else 1
    return (has_score, record.score or 0.0, record.updated_at)


def build_dashboard(
    opportunities: _OpportunityLister,
    runs: _RunLister,
    *,
    inbox_limit: int = 20,
    now: Callable[[], datetime] | None = None,
) -> DiscoveryDashboardView:
    """Assemble the discovery view from the opportunity + run repositories.

    Opportunities are ranked best-first (scored ahead of unscored). ``runs`` only
    needs ``latest()``; if it can also ``list()`` (the file and DB run stores
    both can), the recent-run history is included too.
    """
    clock = now or (lambda: datetime.now(timezone.utc))
    records = list(opportunities.list())
    records.sort(key=_score_key, reverse=True)

    status_counts: dict[str, int] = {}
    for record in records:
        key = record.status.value
        status_counts[key] = status_counts.get(key, 0) + 1

    inbox = [
        InboxRow(
            id=record.id,
            title=record.title,
            audience=record.audience,
            connector=record.source.connector,
            status=record.status.value,
            score=record.score,
            confidence=record.confidence,
        )
        for record in records[:inbox_limit]
    ]

    latest = runs.latest()
    latest_row = _to_run_row(latest) if latest is not None else None

    recent: list[RunRow] = []
    lister = getattr(runs, "list", None)
    if callable(lister):
        recent = [_to_run_row(report) for report in list(lister())[:10]]
    elif latest_row is not None:
        recent = [latest_row]

    return DiscoveryDashboardView(
        generated_at=clock().isoformat(),
        total_opportunities=len(records),
        status_counts=status_counts,
        inbox=inbox,
        latest_run=latest_row,
        recent_runs=recent,
    )


def _fmt_score(value: float | None) -> str:
    return "—" if value is None else f"{value:.0f}"


def _fmt_conf(value: float | None) -> str:
    return "—" if value is None else f"{value:.2f}"


def _e(text: str) -> str:
    return html.escape(text)


def render_html(view: DiscoveryDashboardView) -> str:
    """Render the view as a single self-contained HTML page (no JS/assets)."""
    counts = " · ".join(f"{_e(k)}: {v}" for k, v in sorted(view.status_counts.items())) or "—"

    if view.latest_run is None:
        run_block = "<p class='muted'>No discovery runs recorded yet.</p>"
    else:
        run = view.latest_run
        state = "running" if run.running else _e(run.status)
        sources = ", ".join(f"{_e(s)} ({n})" for s, n in sorted(run.sources_hit.items())) or "—"
        run_block = (
            "<table>"
            "<tr><th>Latest run</th><td>" + _e(run.run_id) + "</td></tr>"
            "<tr><th>Status</th><td>" + state + "</td></tr>"
            "<tr><th>Signals ingested</th><td>" + str(run.signals_ingested) + "</td></tr>"
            "<tr><th>Sources hit</th><td>" + sources + "</td></tr>"
            "<tr><th>Queries</th><td>" + (_e(", ".join(run.queries)) or "—") + "</td></tr>"
            "<tr><th>Started</th><td>" + _e(run.started_at) + "</td></tr>"
            "<tr><th>Finished</th><td>" + (_e(run.finished_at) or "(running)") + "</td></tr>"
            "</table>"
        )

    if view.inbox:
        rows = "".join(
            "<tr>"
            f"<td class='num'>{i}</td>"
            f"<td class='num'>{_fmt_score(row.score)}</td>"
            f"<td class='num'>{_fmt_conf(row.confidence)}</td>"
            f"<td>{_e(row.status)}</td>"
            f"<td>{_e(row.title)}</td>"
            f"<td>{_e(row.audience)}</td>"
            f"<td>{_e(row.connector)}</td>"
            "</tr>"
            for i, row in enumerate(view.inbox, start=1)
        )
        inbox_block = (
            "<table>"
            "<tr><th>#</th><th>Score</th><th>Conf</th><th>Status</th>"
            "<th>Title</th><th>Audience</th><th>Source</th></tr>"
            f"{rows}</table>"
        )
    else:
        inbox_block = "<p class='muted'>Inbox is empty — start a discovery run.</p>"

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Discovery — operator dashboard</title>
<style>
  body {{ font: 14px/1.5 -apple-system, system-ui, sans-serif; margin: 2rem auto; max-width: 960px;
         color: #1d1d1f; padding: 0 1rem; }}
  h1 {{ font-size: 1.4rem; margin: 0 0 .25rem; }}
  h2 {{ font-size: 1.05rem; margin: 2rem 0 .5rem; }}
  .muted {{ color: #86868b; }}
  .meta {{ color: #86868b; font-size: .85rem; }}
  table {{ border-collapse: collapse; width: 100%; }}
  th, td {{ text-align: left; padding: .4rem .6rem; border-bottom: 1px solid #e5e5e7; }}
  td.num, th.num {{ text-align: right; font-variant-numeric: tabular-nums; }}
</style>
</head>
<body>
  <h1>Discovery</h1>
  <p class="meta">Generated {_e(view.generated_at)} · {view.total_opportunities} opportunities ·
     {counts}</p>
  <h2>Run status</h2>
  {run_block}
  <h2>Inbox (ranked)</h2>
  {inbox_block}
</body>
</html>
"""


__all__ = [
    "DiscoveryDashboardView",
    "InboxRow",
    "RunRow",
    "build_dashboard",
    "render_html",
]
