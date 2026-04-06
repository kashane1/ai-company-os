from __future__ import annotations

import importlib.util
from pathlib import Path
from threading import Event

from apps.api.control_plane import ControlPlaneService
from packages.db.event_store import EventStore
from packages.db.goal_store import GoalStore
from packages.db.task_store import TaskStore
from packages.schemas.task_packet import RiskLevel, TaskResult, TaskStatus, WorkerLane


def load_engineering_worker_main():
    module_path = Path(__file__).resolve().parents[3] / "apps" / "worker-engineering" / "main.py"
    spec = importlib.util.spec_from_file_location("worker_engineering_main", module_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_engineering_worker_claims_executes_and_submits_through_control_plane(
    isolated_repo_root: Path,
    monkeypatch,
) -> None:
    worker_engineering_main = load_engineering_worker_main()
    service = ControlPlaneService()
    goal = service.create_goal(
        title="Run engineering task through control plane",
        summary="Claim and execute one engineering task.",
    )
    task = service.create_task_for_goal(
        goal_id=goal.id,
        repo_id="ai-company-os",
        lane=WorkerLane.ENGINEERING,
        title="Execute bounded work",
        summary="Run the engineering lane via the control plane.",
        task_type="engineering_change",
        risk_level=RiskLevel.MEDIUM,
    )

    monkeypatch.setattr(
        worker_engineering_main,
        "execute_task",
        lambda task_id, **kwargs: TaskResult(
            task_id=task_id,
            status=TaskStatus.COMPLETED,
            summary="Executed through engineering runtime.",
            run_id=f"run-{task_id}",
            approval_id="approval-runtime-1",
        ),
    )

    requested_approvals = []
    original_request_approval = service.request_approval

    def capture_request_approval(**kwargs):
        requested_approvals.append(kwargs)
        return original_request_approval(**kwargs, approval_id="approval-runtime-1")

    monkeypatch.setattr(service, "request_approval", capture_request_approval)

    result = worker_engineering_main.execute_claimed_task(
        worker_id="worker-engineering-1",
        service=service,
    )

    stored_task = TaskStore().load(task.id)
    stored_goal = GoalStore().load(goal.id)
    events = EventStore().list()

    assert result is not None
    assert result.task_id == task.id
    assert stored_task.status is TaskStatus.COMPLETED
    assert stored_task.claimed_by == "worker-engineering-1"
    assert stored_task.result_summary == "Executed through engineering runtime."
    assert stored_task.approval_id == "approval-runtime-1"
    assert stored_goal.status.value == "completed"
    assert requested_approvals == []
    assert [event.event_type for event in events] == [
        "goal_created",
        "task_created",
        "task_claimed",
        "task_completed",
    ]


def test_engineering_worker_runtime_requests_approval_when_runner_does(
    isolated_repo_root: Path,
    monkeypatch,
) -> None:
    worker_engineering_main = load_engineering_worker_main()
    service = ControlPlaneService()
    goal = service.create_goal(
        title="Request review approval",
        summary="Engineering worker should ask through control plane.",
    )
    task = service.create_task_for_goal(
        goal_id=goal.id,
        repo_id="ai-company-os",
        lane=WorkerLane.ENGINEERING,
        title="Prepare reviewable diff",
        summary="Runner should create approval through control plane service.",
        task_type="engineering_change",
    )

    def fake_execute_task(task_id: str, **kwargs) -> TaskResult:
        approval = kwargs["approval_factory"](
            task_id,
            f"run-{task_id}",
            "/tmp/review.json",
            "Ready for review.",
        )
        return TaskResult(
            task_id=task_id,
            status=TaskStatus.COMPLETED,
            summary="Ready for review.",
            run_id=f"run-{task_id}",
            approval_id=approval.id,
        )

    monkeypatch.setattr(worker_engineering_main, "execute_task", fake_execute_task)

    result = worker_engineering_main.execute_claimed_task(
        worker_id="worker-engineering-2",
        service=service,
    )

    stored_task = TaskStore().load(task.id)
    events = EventStore().list()

    assert result is not None
    assert stored_task.approval_id is not None
    approval_events = [event for event in events if event.event_type == "approval_requested"]
    assert len(approval_events) == 1
    assert approval_events[0].task_id == task.id
    assert approval_events[0].payload["action"] == "review_engineering_task"


def test_engineering_worker_marks_claimed_task_failed_when_runner_raises(
    isolated_repo_root: Path,
    monkeypatch,
) -> None:
    worker_engineering_main = load_engineering_worker_main()
    service = ControlPlaneService()
    goal = service.create_goal(
        title="Handle engineering failure",
        summary="Claimed task should fail through control plane when runner raises.",
    )
    task = service.create_task_for_goal(
        goal_id=goal.id,
        repo_id="ai-company-os",
        lane=WorkerLane.ENGINEERING,
        title="Runner crash",
        summary="Simulate an unhandled engineering exception.",
        task_type="engineering_change",
    )

    def crash_execute_task(task_id: str, **kwargs) -> TaskResult:
        raise RuntimeError("codex execution crashed")

    monkeypatch.setattr(worker_engineering_main, "execute_task", crash_execute_task)

    try:
        worker_engineering_main.execute_claimed_task(
            worker_id="worker-engineering-3",
            service=service,
        )
    except RuntimeError:
        pass
    else:
        raise AssertionError("expected execute_claimed_task to re-raise runner exception")

    stored_task = TaskStore().load(task.id)
    failure_events = [event for event in EventStore().list() if event.event_type == "task_failed"]

    assert stored_task.status is TaskStatus.FAILED
    assert stored_task.error_summary == "Engineering worker execution failed: codex execution crashed"
    assert len(failure_events) == 1
    assert failure_events[0].task_id == task.id


def test_engineering_worker_loop_processes_tasks_and_idles_when_queue_is_empty(
    isolated_repo_root: Path,
    monkeypatch,
) -> None:
    worker_engineering_main = load_engineering_worker_main()
    service = ControlPlaneService()
    goal = service.create_goal(
        title="Loop engineering work",
        summary="Process multiple tasks before idling.",
    )
    first_task = service.create_task_for_goal(
        goal_id=goal.id,
        repo_id="ai-company-os",
        lane=WorkerLane.ENGINEERING,
        title="First engineering task",
        summary="Process first task.",
        task_type="engineering_change",
    )
    second_task = service.create_task_for_goal(
        goal_id=goal.id,
        repo_id="ai-company-os",
        lane=WorkerLane.ENGINEERING,
        title="Second engineering task",
        summary="Process second task.",
        task_type="engineering_change",
    )

    monkeypatch.setattr(
        worker_engineering_main,
        "execute_task",
        lambda task_id, **kwargs: TaskResult(
            task_id=task_id,
            status=TaskStatus.COMPLETED,
            summary=f"Completed {task_id}",
            run_id=f"run-{task_id}",
        ),
    )

    sleep_calls: list[float] = []
    stats = worker_engineering_main.run_worker_loop(
        worker_id="worker-engineering-loop",
        service=service,
        poll_interval_seconds=0.25,
        sleep_fn=lambda seconds: sleep_calls.append(seconds),
        max_iterations=3,
    )

    first_stored = TaskStore().load(first_task.id)
    second_stored = TaskStore().load(second_task.id)

    assert stats.processed_count == 2
    assert stats.idle_cycles == 1
    assert stats.stop_reason == "idle"
    assert sleep_calls == [0.25]
    assert first_stored.status is TaskStatus.COMPLETED
    assert second_stored.status is TaskStatus.COMPLETED


def test_engineering_worker_loop_stops_cleanly_when_stop_is_requested(
    isolated_repo_root: Path,
    monkeypatch,
) -> None:
    worker_engineering_main = load_engineering_worker_main()
    service = ControlPlaneService()
    stop_event = Event()
    sleep_calls: list[float] = []

    def fake_sleep(seconds: float) -> None:
        sleep_calls.append(seconds)
        stop_event.set()

    monkeypatch.setattr(
        worker_engineering_main,
        "execute_task",
        lambda task_id, **kwargs: TaskResult(
            task_id=task_id,
            status=TaskStatus.COMPLETED,
            summary=f"Completed {task_id}",
            run_id=f"run-{task_id}",
        ),
    )

    stats = worker_engineering_main.run_worker_loop(
        worker_id="worker-engineering-stop",
        service=service,
        poll_interval_seconds=0.5,
        stop_event=stop_event,
        sleep_fn=fake_sleep,
    )

    assert stats.processed_count == 0
    assert stats.idle_cycles == 1
    assert stats.stop_reason == "stop_requested"
    assert sleep_calls == [0.5]
