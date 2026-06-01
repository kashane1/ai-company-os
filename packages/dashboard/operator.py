from __future__ import annotations

import html
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Callable, Protocol

from packages.db.approval_store import ApprovalStore
from packages.db.event_store import EventStore
from packages.db.task_store import TaskStore
from packages.queue import TaskQueue
from packages.schemas.approval import ApprovalRecord, ApprovalStatus
from packages.schemas.event import EventRecord
from packages.schemas.task import Task
from packages.schemas.task_packet import WorkerLane


class _TaskReadStore(Protocol):
    def list_recent(self, *, limit: int = 50) -> list[Task]:
        ...

    def count_by_status(self) -> dict[str, int]:
        ...

    def latest_for_lane(self, lane: str) -> Task | None:
        ...


class _ApprovalReadStore(Protocol):
    def list_recent(self, *, limit: int = 50) -> list[ApprovalRecord]:
        ...

    def count_by_status(self) -> dict[str, int]:
        ...


class _EventReadStore(Protocol):
    def list_recent(self, *, limit: int = 50) -> list[EventRecord]:
        ...


class _QueueReadStore(Protocol):
    def size(self, lane: WorkerLane | None = None) -> int:
        ...

    def counts_by_lane(self) -> dict[str, int]:
        ...


@dataclass(frozen=True)
class LaneRow:
    lane: str
    queued: int
    latest_task_id: str | None = None
    latest_status: str | None = None
    latest_updated_at: str | None = None
    latest_title: str | None = None


@dataclass(frozen=True)
class TaskRow:
    id: str
    lane: str
    status: str
    title: str
    updated_at: str
    claimed_by: str | None = None
    approval_id: str | None = None


@dataclass(frozen=True)
class ApprovalRow:
    id: str
    status: str
    action: str
    subject_type: str
    subject_id: str
    summary: str
    created_at: str


@dataclass(frozen=True)
class EventRow:
    id: str
    event_type: str
    subject_type: str
    subject_id: str
    created_at: str


@dataclass(frozen=True)
class OperatorDashboardView:
    generated_at: str
    database: dict[str, object]
    queue_backend: str
    queued_tasks: int
    task_counts: dict[str, int] = field(default_factory=dict)
    approval_counts: dict[str, int] = field(default_factory=dict)
    lanes: list[LaneRow] = field(default_factory=list)
    tasks: list[TaskRow] = field(default_factory=list)
    approvals: list[ApprovalRow] = field(default_factory=list)
    events: list[EventRow] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return {
            "generated_at": self.generated_at,
            "database": dict(self.database),
            "queue_backend": self.queue_backend,
            "queued_tasks": self.queued_tasks,
            "task_counts": dict(self.task_counts),
            "approval_counts": dict(self.approval_counts),
            "lanes": [row.__dict__ for row in self.lanes],
            "tasks": [row.__dict__ for row in self.tasks],
            "approvals": [row.__dict__ for row in self.approvals],
            "events": [row.__dict__ for row in self.events],
        }


def build_operator_dashboard(
    *,
    tasks: _TaskReadStore | None = None,
    approvals: _ApprovalReadStore | None = None,
    events: _EventReadStore | None = None,
    queue: _QueueReadStore | None = None,
    queue_backend: str = "database",
    now: Callable[[], datetime] | None = None,
    task_limit: int = 25,
    approval_limit: int = 25,
    event_limit: int = 25,
) -> OperatorDashboardView:
    task_store = tasks or TaskStore()
    approval_store = approvals or ApprovalStore()
    event_store = events or EventStore()
    task_queue = queue or TaskQueue()
    clock = now or (lambda: datetime.now(timezone.utc))

    queue_counts = task_queue.counts_by_lane()
    lane_rows: list[LaneRow] = []
    for lane in WorkerLane:
        latest = task_store.latest_for_lane(lane.value)
        lane_rows.append(
            LaneRow(
                lane=lane.value,
                queued=queue_counts.get(lane.value, 0),
                latest_task_id=latest.id if latest else None,
                latest_status=latest.status.value if latest else None,
                latest_updated_at=latest.updated_at if latest else None,
                latest_title=latest.title if latest else None,
            )
        )

    recent_tasks = [
        TaskRow(
            id=task.id,
            lane=task.lane.value,
            status=task.status.value,
            title=task.title,
            updated_at=task.updated_at,
            claimed_by=task.claimed_by,
            approval_id=task.approval_id,
        )
        for task in task_store.list_recent(limit=task_limit)
    ]
    recent_approvals = [
        ApprovalRow(
            id=approval.id,
            status=approval.status.value,
            action=approval.action,
            subject_type=approval.subject_type,
            subject_id=approval.subject_id,
            summary=approval.summary,
            created_at=approval.created_at,
        )
        for approval in _pending_first(approval_store.list_recent(limit=approval_limit))
    ]
    recent_events = [
        EventRow(
            id=event.id,
            event_type=event.event_type,
            subject_type=event.subject_type,
            subject_id=event.subject_id,
            created_at=event.created_at,
        )
        for event in event_store.list_recent(limit=event_limit)
    ]

    database = getattr(getattr(task_queue, "db", None), "health_info", lambda: {})()
    return OperatorDashboardView(
        generated_at=clock().isoformat(),
        database=database,
        queue_backend=queue_backend,
        queued_tasks=task_queue.size(),
        task_counts=task_store.count_by_status(),
        approval_counts=approval_store.count_by_status(),
        lanes=lane_rows,
        tasks=recent_tasks,
        approvals=recent_approvals,
        events=recent_events,
    )


def _pending_first(approvals: list[ApprovalRecord]) -> list[ApprovalRecord]:
    return sorted(
        approvals,
        key=lambda approval: (
            0 if approval.status is ApprovalStatus.PENDING else 1,
            approval.created_at,
        ),
        reverse=False,
    )


def _e(value: object) -> str:
    return html.escape("" if value is None else str(value))


def _counts(counts: dict[str, int]) -> str:
    return " · ".join(f"{_e(key)}: {value}" for key, value in sorted(counts.items())) or "none"


def _table(headers: list[str], rows: list[list[object]]) -> str:
    if not rows:
        return "<p class='muted'>No records yet.</p>"
    head = "".join(f"<th>{_e(header)}</th>" for header in headers)
    body = "".join(
        "<tr>" + "".join(f"<td>{_e(cell)}</td>" for cell in row) + "</tr>"
        for row in rows
    )
    return f"<table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>"


def render_html(view: OperatorDashboardView) -> str:
    pending_approvals = _e(view.approval_counts.get(ApprovalStatus.PENDING.value, 0))
    task_counts = _counts(view.task_counts)
    approval_counts = _counts(view.approval_counts)
    lane_rows = [
        [
            lane.lane,
            lane.queued,
            lane.latest_status or "-",
            lane.latest_title or "-",
            lane.latest_updated_at or "-",
        ]
        for lane in view.lanes
    ]
    task_rows = [
        [task.status, task.lane, task.title, task.claimed_by or "-", task.updated_at]
        for task in view.tasks
    ]
    approval_rows = [
        [
            approval.status,
            approval.action,
            f"{approval.subject_type}:{approval.subject_id}",
            approval.summary,
            approval.created_at,
        ]
        for approval in view.approvals
    ]
    event_rows = [
        [event.created_at, event.event_type, f"{event.subject_type}:{event.subject_id}"]
        for event in view.events
    ]
    db = view.database
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="refresh" content="5">
<title>ai-company-os dashboard</title>
<style>
  body {{ font: 14px/1.45 -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
         color: #202124; margin: 0; background: #f6f7f9; }}
  header {{ background: #121417; color: white; padding: 18px 24px; }}
  main {{ max-width: 1240px; margin: 0 auto; padding: 20px 24px 48px; }}
  h1 {{ font-size: 20px; margin: 0 0 4px; }}
  h2 {{ font-size: 15px; margin: 28px 0 10px; }}
  .meta {{ color: #c7ccd1; font-size: 13px; }}
  .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(190px, 1fr)); gap: 10px; }}
  .metric {{ background: white; border: 1px solid #dde1e6; border-radius: 6px; padding: 12px; }}
  .metric b {{ display: block; font-size: 20px; margin-bottom: 2px; }}
  .muted {{ color: #697077; }}
  table {{ width: 100%; border-collapse: collapse; background: white; border: 1px solid #dde1e6; }}
  th, td {{ text-align: left; border-bottom: 1px solid #edf0f2;
            padding: 7px 8px; vertical-align: top; }}
  th {{ font-size: 12px; color: #4f5b62; background: #fafbfc; }}
  td {{ font-size: 13px; }}
</style>
</head>
<body>
<header>
  <h1>ai-company-os dashboard</h1>
  <div class="meta">Generated {_e(view.generated_at)} · auto-refresh 5s</div>
</header>
<main>
  <section class="grid">
    <div class="metric"><b>{_e(db.get("backend", "unknown"))}</b><span>database</span></div>
    <div class="metric"><b>{_e(view.queue_backend)}</b><span>queue backend</span></div>
    <div class="metric"><b>{view.queued_tasks}</b><span>queued tasks</span></div>
    <div class="metric"><b>{pending_approvals}</b><span>pending approvals</span></div>
  </section>
  <p class="muted">DB: {_e(db.get("dsn", ""))} · tasks: {task_counts}
     · approvals: {approval_counts}</p>

  <h2>Lanes</h2>
  {_table(["Lane", "Queued", "Latest status", "Latest task", "Updated"], lane_rows)}

  <h2>Recent tasks</h2>
  {_table(["Status", "Lane", "Task", "Claimed by", "Updated"], task_rows)}

  <h2>Approvals</h2>
  {_table(["Status", "Action", "Subject", "Summary", "Created"], approval_rows)}

  <h2>Events</h2>
  {_table(["Created", "Type", "Subject"], event_rows)}
</main>
</body>
</html>
"""


__all__ = ["OperatorDashboardView", "build_operator_dashboard", "render_html"]
