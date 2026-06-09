"""Outreach operations runner.

This lane manages local outreach state and drafts. It must not send outbound
email, SMS, Instagram, or Facebook messages.
"""

from __future__ import annotations

from pathlib import Path

from packages.agency.outreach_lane import refresh_client_status
from packages.schemas.task import Task
from packages.schemas.task_packet import TaskResult, TaskStatus

SEND_TASK_TYPES = {
    "OUTREACH_SEND_EMAIL",
    "OUTREACH_SEND_SMS",
    "OUTREACH_SEND_INSTAGRAM_DM",
    "OUTREACH_SEND_FACEBOOK_DM",
}


def execute_task(task: Task, *, repo_root: Path | None = None) -> TaskResult:
    if task.task_type in SEND_TASK_TYPES:
        return TaskResult(
            task_id=task.id,
            status=TaskStatus.FAILED,
            summary=f"{task.task_type} is manual-gated; outreach worker does not send outbound messages",
            failure_codes=["outreach_send_forbidden"],
        )
    if task.task_type == "OUTREACH_LEDGER_REFRESH":
        rows = refresh_client_status(repo_root=repo_root)
        return TaskResult(
            task_id=task.id,
            status=TaskStatus.COMPLETED,
            summary=f"refreshed client-status ledger with {len(rows)} outreach row(s)",
            artifacts=[
                "state/prospects/outreach-lane/client-status.json",
                "state/prospects/outreach-lane/client-status.md",
            ],
            validation_checks=["manual-send-boundary:enforced"],
        )
    if task.task_type == "OUTREACH_DRAFT":
        return TaskResult(
            task_id=task.id,
            status=TaskStatus.COMPLETED,
            summary="OUTREACH_DRAFT acknowledged; use scripts/agency/build_outreach.py for draft generation",
            next_actions=["Run scripts/agency/build_outreach.py, then refresh outreach ledger"],
            validation_checks=["manual-send-boundary:enforced"],
        )
    if task.task_type == "OUTREACH_TOUCH_LOG":
        return TaskResult(
            task_id=task.id,
            status=TaskStatus.BLOCKED,
            summary="OUTREACH_TOUCH_LOG requires operator-supplied place_id/channel/outcome via CLI",
            next_actions=["Use scripts/agency/outreach_lane.py log --place-id ..."],
        )
    if task.task_type == "OUTREACH_REPLY_RECONCILE":
        return TaskResult(
            task_id=task.id,
            status=TaskStatus.COMPLETED,
            summary="OUTREACH_REPLY_RECONCILE scaffolded; CRM/inbox adapter not installed",
            validation_checks=["no-inbox-send-path"],
        )
    return TaskResult(
        task_id=task.id,
        status=TaskStatus.FAILED,
        summary=f"unknown outreach task_type={task.task_type!r}",
        failure_codes=["outreach_unknown_task_type"],
    )
