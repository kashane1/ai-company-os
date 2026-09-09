from __future__ import annotations

import argparse

import pytest

from apps.api.control_plane import ControlPlaneService
from packages.queue.task_queue import QueueReconciliationReport
from packages.schemas.task import Task
from packages.schemas.task_packet import RiskLevel, TaskStatus, WorkerLane
from scripts import control_plane_db


def _reconcile_args(*, apply: bool = False, workers_stopped: bool = False) -> argparse.Namespace:
    return argparse.Namespace(apply=apply, workers_stopped=workers_stopped)


def _recover_args(
    task_id: str,
    *,
    apply: bool = False,
    workers_stopped: bool = False,
) -> argparse.Namespace:
    return argparse.Namespace(
        task_id=task_id,
        reason="worker process was confirmed stopped",
        apply=apply,
        workers_stopped=workers_stopped,
    )


def test_reconcile_queue_dry_run_uses_all_canonical_tasks(monkeypatch: pytest.MonkeyPatch) -> None:
    service = ControlPlaneService()
    for index in range(51):
        service.tasks.save(
            Task(
                id=f"task-reconcile-{index}",
                repo_id="ai-company-os",
                lane=WorkerLane.OUTREACH,
                title="Reconcile all tasks",
                summary="A synthetic canonical task.",
                task_type="OUTREACH_LEDGER_REFRESH",
                status=TaskStatus.PENDING,
                risk_level=RiskLevel.LOW,
            )
        )
    captured: dict[str, object] = {}

    def reconcile(tasks, *, dry_run, workers_stopped):
        captured["tasks"] = tasks
        captured["dry_run"] = dry_run
        captured["workers_stopped"] = workers_stopped
        return QueueReconciliationReport(True, (), (), (), ())

    monkeypatch.setattr(service.queue, "reconcile_pending", reconcile)
    monkeypatch.setattr(control_plane_db, "ControlPlaneService", lambda: service)

    assert control_plane_db._cmd_reconcile_queue(_reconcile_args()) == 0
    assert len(captured["tasks"]) == 51
    assert captured["dry_run"] is True
    assert captured["workers_stopped"] is False
    assert control_plane_db._cmd_reconcile_queue(
        _reconcile_args(apply=True, workers_stopped=True)
    ) == 0
    assert captured["dry_run"] is False
    assert captured["workers_stopped"] is True


def test_reconcile_queue_apply_requires_stopped_worker_guard(monkeypatch: pytest.MonkeyPatch) -> None:
    service = ControlPlaneService()
    called = False

    def reconcile(*args, **kwargs):
        nonlocal called
        called = True
        raise AssertionError("guard must prevent reconciliation")

    monkeypatch.setattr(service.queue, "reconcile_pending", reconcile)
    monkeypatch.setattr(control_plane_db, "ControlPlaneService", lambda: service)

    assert control_plane_db._cmd_reconcile_queue(_reconcile_args(apply=True)) == 2
    assert called is False


def test_recover_task_dry_run_and_guard_do_not_mutate_then_apply_preserves_history(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = ControlPlaneService()
    old_goal = service.create_goal(title="Original goal", summary="Keep history")
    old_task = service.create_task_for_goal(
        goal_id=old_goal.id,
        repo_id="ai-company-os",
        lane=WorkerLane.OUTREACH,
        title="Original task",
        summary="Retry this work safely.",
        task_type="OUTREACH_LEDGER_REFRESH",
        risk_level=RiskLevel.HIGH,
        product_id="product-1",
        requires_approval=True,
        constraints=["keep audit history"],
    )
    service.claim_task(lane=old_task.lane, worker_id="stopped-worker")
    monkeypatch.setattr(control_plane_db, "ControlPlaneService", lambda: service)

    assert control_plane_db._cmd_recover_task(_recover_args(old_task.id)) == 0
    assert service.tasks.load(old_task.id).status is TaskStatus.IN_PROGRESS
    assert len(service.list_goals()) == 1
    assert len(service.list_tasks_for_goal(old_goal.id)) == 1

    assert control_plane_db._cmd_recover_task(_recover_args(old_task.id, apply=True)) == 2
    assert service.tasks.load(old_task.id).status is TaskStatus.IN_PROGRESS

    assert control_plane_db._cmd_recover_task(
        _recover_args(old_task.id, apply=True, workers_stopped=True)
    ) == 0
    failed = service.tasks.load(old_task.id)
    assert failed.status is TaskStatus.FAILED
    assert "confirmed stopped" in (failed.error_summary or "")
    recovery_goals = [goal for goal in service.list_goals() if goal.parent_goal_id == old_goal.id]
    assert len(recovery_goals) == 1
    replacement_tasks = service.list_tasks_for_goal(recovery_goals[0].id)
    assert len(replacement_tasks) == 1
    replacement = replacement_tasks[0]
    assert replacement.id != old_task.id
    assert replacement.status is TaskStatus.PENDING
    assert (replacement.repo_id, replacement.lane, replacement.task_type) == (
        old_task.repo_id,
        old_task.lane,
        old_task.task_type,
    )
    assert (replacement.product_id, replacement.risk_level, replacement.requires_approval) == (
        old_task.product_id,
        old_task.risk_level,
        old_task.requires_approval,
    )
    assert replacement.constraints == old_task.constraints
    abandoned = [event for event in service.list_events() if event.event_type == "task_abandoned"]
    assert len(abandoned) == 1
    assert abandoned[0].subject_id == old_task.id
    assert abandoned[0].payload["replacement_task_id"] == replacement.id

    assert control_plane_db._cmd_recover_task(
        _recover_args(old_task.id, apply=True, workers_stopped=True)
    ) == 1
    assert len([goal for goal in service.list_goals() if goal.parent_goal_id == old_goal.id]) == 1


def test_abandon_task_rolls_back_if_replacement_creation_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = ControlPlaneService()
    goal = service.create_goal(title="Atomic recovery", summary="Keep old attempt on failure")
    task = service.create_task_for_goal(
        goal_id=goal.id,
        repo_id="ai-company-os",
        lane=WorkerLane.OUTREACH,
        title="Old attempt",
        summary="Do not lose this history.",
        task_type="OUTREACH_LEDGER_REFRESH",
    )
    service.claim_task(lane=task.lane, worker_id="stopped-worker")
    before_goal = service.goals.load(goal.id)

    def fail_replacement(**kwargs):
        raise OSError("injected replacement failure")

    monkeypatch.setattr(service, "create_task_for_goal", fail_replacement)
    with pytest.raises(OSError, match="replacement failure"):
        service.abandon_task(task_id=task.id, reason="confirmed stopped worker", workers_stopped=True)

    assert service.tasks.load(task.id).status is TaskStatus.IN_PROGRESS
    queued = service.tasks.db.fetch_one(
        "SELECT task_id FROM task_queue WHERE task_id = :id",
        {"id": task.id},
    )
    assert queued is not None
    assert service.list_goals() == [before_goal]
    assert not any(event.event_type == "task_abandoned" for event in service.list_events())
