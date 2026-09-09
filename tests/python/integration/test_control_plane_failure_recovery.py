from __future__ import annotations

import pytest

from apps.api.control_plane import ControlPlaneService
from packages.schemas.approval import ApprovalStatus
from packages.schemas.goal import GoalStatus
from packages.schemas.task_packet import TaskStatus, WorkerLane


def _new_task(service, goal_id, task_id="fault-task"):
    return service.create_task_for_goal(
        goal_id=goal_id, repo_id="ai-company-os", lane=WorkerLane.OUTREACH,
        title="Transactional task", summary="Inspect failure boundaries",
        task_type="OUTREACH_LEDGER_REFRESH", task_id=task_id,
    )


def test_task_creation_rolls_back_queue_task_goal_and_event(monkeypatch):
    service = ControlPlaneService()
    goal = service.create_goal(title="Failure exercise", summary="Synthetic")
    original = service._append_event

    def fail_after_event(**kwargs):
        original(**kwargs)
        raise OSError("injected after event write")

    with monkeypatch.context() as patch:
        patch.setattr(service, "_append_event", fail_after_event)
        with pytest.raises(OSError, match="injected"):
            _new_task(service, goal.id)
    assert service.queue.size() == 0
    assert service.list_tasks_for_goal(goal.id) == []
    assert service.goals.load(goal.id).status is GoalStatus.OPEN
    assert [e.event_type for e in service.list_events()] == ["goal_created"]
    assert _new_task(service, goal.id).status is TaskStatus.PENDING


def test_result_failure_rolls_back_ack_and_terminal_state_then_retry_succeeds(monkeypatch):
    service = ControlPlaneService()
    goal = service.create_goal(title="Failure exercise", summary="Synthetic")
    task = _new_task(service, goal.id)
    service.claim_task(lane=task.lane, worker_id="owner")
    original = service._refresh_goal_status

    def fail_after_refresh(*args):
        original(*args)
        raise OSError("injected after goal refresh")

    result = dict(task_id=task.id, status=TaskStatus.FAILED, summary="local operation failed", worker_id="owner")
    with monkeypatch.context() as patch:
        patch.setattr(service, "_refresh_goal_status", fail_after_refresh)
        with pytest.raises(OSError, match="injected"):
            service.submit_task_result(**result)
    assert service.tasks.load(task.id).status is TaskStatus.IN_PROGRESS
    assert service.goals.load(goal.id).status is GoalStatus.IN_PROGRESS
    assert not any(e.event_type == "task_failed" for e in service.list_events())
    queued = service.tasks.db.fetch_one("SELECT task_id FROM task_queue WHERE task_id = :id", {"id": task.id})
    assert queued is not None
    assert service.submit_task_result(**result).status is TaskStatus.FAILED
    assert service.goals.load(goal.id).status is GoalStatus.FAILED
    # A repeated delivery produces the same terminal record and one effect/event.
    assert service.submit_task_result(**result).status is TaskStatus.FAILED
    assert sum(e.event_type == "task_failed" for e in service.list_events()) == 1


@pytest.mark.parametrize("claimed", [False, True])
def test_result_requires_current_claimant(claimed):
    service = ControlPlaneService()
    goal = service.create_goal(title="Owner fence", summary="Synthetic")
    task = _new_task(service, goal.id)
    if claimed:
        service.claim_task(lane=task.lane, worker_id="owner")
    with pytest.raises(ValueError, match="claim"):
        service.submit_task_result(task_id=task.id, status=TaskStatus.FAILED,
                                   summary="stale result", worker_id="other")
    assert service.tasks.load(task.id).status is (TaskStatus.IN_PROGRESS if claimed else TaskStatus.PENDING)


def test_terminal_task_cannot_be_reopened_by_generic_status_update():
    service = ControlPlaneService()
    goal = service.create_goal(title="Terminal state", summary="Synthetic")
    task = _new_task(service, goal.id)
    service.claim_task(lane=task.lane, worker_id="owner")
    service.submit_task_result(task_id=task.id, status=TaskStatus.FAILED, summary="failed", worker_id="owner")
    with pytest.raises(ValueError, match="transition"):
        service.tasks.set_status(task.id, TaskStatus.IN_PROGRESS, updated_at="later")


def test_create_cannot_overwrite_existing_goal_task_or_approval():
    service = ControlPlaneService()
    goal = service.create_goal(title="Original", summary="Preserve history", goal_id="fixed-goal")
    task = _new_task(service, goal.id)
    service.claim_task(lane=task.lane, worker_id="owner")
    service.submit_task_result(task_id=task.id, status=TaskStatus.FAILED,
                               summary="original failure", worker_id="owner")
    approval_args = dict(summary="Review", subject_type="task", subject_id=task.id,
                         action="inspect", approval_type="manual", approval_id="fixed-approval")
    approval = service.request_approval(**approval_args)
    service.decide_approval(approval_id=approval.id, status=ApprovalStatus.REJECTED, decided_by="operator")
    before_events = service.list_events()
    with pytest.raises(ValueError, match="already exists"):
        service.create_goal(title="Replacement", summary="Overwrite", goal_id=goal.id)
    with pytest.raises(ValueError, match="already exists"):
        _new_task(service, goal.id)
    with pytest.raises(ValueError, match="already exists"):
        service.request_approval(**approval_args)
    assert service.goals.load(goal.id).title == "Original"
    assert service.tasks.load(task.id).status is TaskStatus.FAILED
    assert service.approvals.load(approval.id).status is ApprovalStatus.REJECTED
    assert service.list_events() == before_events
    assert service.queue.size() == 0


def test_child_goal_requires_an_existing_parent():
    service = ControlPlaneService()
    with pytest.raises(FileNotFoundError):
        service.create_goal(title="Orphan", summary="Invalid", parent_goal_id="missing")
    assert service.list_goals() == []


def test_redis_ack_waits_for_commit_and_can_retry_after_ack_failure(monkeypatch):
    service = ControlPlaneService()
    goal = service.create_goal(title="Redis commit boundary", summary="Synthetic")
    task = _new_task(service, goal.id)
    service.claim_task(lane=task.lane, worker_id="owner")

    class RedisProbe:
        name = "redis"
        calls = 0
        fail_ack = True

        def assert_claim_owner(self, task_id, *, worker_id):
            pass

        def acknowledge(self, task_id, *, worker_id):
            self.calls += 1
            if self.fail_ack:
                raise OSError("injected Redis ACK failure")
            return True

    probe = RedisProbe()
    service.queue.backend = probe
    result = dict(task_id=task.id, status=TaskStatus.FAILED,
                  summary="worker failed", worker_id="owner")
    original = service._refresh_goal_status

    def fail_after_refresh(*args):
        original(*args)
        raise OSError("injected DB failure")

    with monkeypatch.context() as patch:
        patch.setattr(service, "_refresh_goal_status", fail_after_refresh)
        with pytest.raises(OSError, match="DB failure"):
            service.submit_task_result(**result)
    assert probe.calls == 0
    assert service.tasks.load(task.id).status is TaskStatus.IN_PROGRESS

    with pytest.raises(OSError, match="Redis ACK failure"):
        service.submit_task_result(**result)
    assert service.tasks.load(task.id).status is TaskStatus.FAILED
    assert service.goals.load(goal.id).status is GoalStatus.FAILED
    probe.fail_ack = False
    assert service.submit_task_result(**result).status is TaskStatus.FAILED
    assert probe.calls == 2
    assert sum(e.event_type == "task_failed" for e in service.list_events()) == 1
