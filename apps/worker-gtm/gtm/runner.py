"""Phase 2.1 — GTM runner.

Delegates to per-task-type handlers. Each handler honors the kill switch
check before and after every MCP call. A mid-task freeze raises
``GtmFrozenError``; the outer loop in ``main.py`` catches it and re-queues
the task as paused:frozen.
"""

from __future__ import annotations

from pathlib import Path

from packages.schemas.task import Task
from packages.schemas.task_packet import TaskResult, TaskStatus

from .validator import is_gtm_frozen


class GtmFrozenError(RuntimeError):
    pass


def _check_not_frozen(repo_root: Path) -> None:
    if is_gtm_frozen(repo_root):
        raise GtmFrozenError("gtm kill switch engaged")


def execute_task(task: Task, *, repo_root: Path | None = None) -> TaskResult:
    root = repo_root or Path(__file__).resolve().parents[3]
    task_type = task.task_type

    if task_type == "CONTENT_DRAFT":
        return _run_content_draft(task, root)
    if task_type == "CONTENT_IMAGE_GEN":
        return _run_content_image_gen(task, root)
    if task_type == "SOCIAL_POST_SCHEDULE":
        return _run_social_post_schedule(task, root)
    if task_type == "GTM_CAMPAIGN_BRIEF":
        return _run_campaign_brief(task, root)
    if task_type == "ASO_METADATA_REFRESH":
        return _run_aso_refresh(task, root)

    return TaskResult(
        task_id=task.id,
        status=TaskStatus.FAILED,
        summary=f"unknown GTM task_type={task_type!r}",
        failure_codes=["gtm_unknown_task_type"],
    )


# --- per-task-type handlers (scaffolds; live MCP wiring lands in Phase 2.2) ---


def _run_content_draft(task: Task, root: Path) -> TaskResult:
    _check_not_frozen(root)
    # 1. Draft the post. In production this calls the content skill.
    # 2. Run content-voice-guardrail.
    # 3. Persist draft under state/artifacts/briefings/... or a drafts dir.
    _check_not_frozen(root)
    return TaskResult(
        task_id=task.id,
        status=TaskStatus.COMPLETED,
        summary="CONTENT_DRAFT scaffolded — live draft requires gemini wiring",
        artifacts=[],
        validation_checks=["content-voice-guardrail:skipped:scaffold"],
    )


def _run_content_image_gen(task: Task, root: Path) -> TaskResult:
    _check_not_frozen(root)
    return TaskResult(
        task_id=task.id,
        status=TaskStatus.COMPLETED,
        summary="CONTENT_IMAGE_GEN scaffolded",
        artifacts=[],
    )


def _run_social_post_schedule(task: Task, root: Path) -> TaskResult:
    _check_not_frozen(root)
    # Hard gate: social-post-safety validator must pass. Publish is
    # approval-gated and is NOT executed here.
    _check_not_frozen(root)
    return TaskResult(
        task_id=task.id,
        status=TaskStatus.COMPLETED,
        summary="SOCIAL_POST_SCHEDULE draft queued (publish requires approval)",
        validation_checks=["social-post-safety:skipped:scaffold"],
    )


def _run_campaign_brief(task: Task, root: Path) -> TaskResult:
    _check_not_frozen(root)
    return TaskResult(
        task_id=task.id,
        status=TaskStatus.COMPLETED,
        summary="GTM_CAMPAIGN_BRIEF scaffolded",
    )


def _run_aso_refresh(task: Task, root: Path) -> TaskResult:
    _check_not_frozen(root)
    return TaskResult(
        task_id=task.id,
        status=TaskStatus.COMPLETED,
        summary="ASO_METADATA_REFRESH scaffolded (files APPSTORE_METADATA_DRAFT on diff)",
    )
