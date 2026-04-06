from __future__ import annotations

import importlib.util
from pathlib import Path
from threading import Event

from apps.api.control_plane import ControlPlaneService
from packages.db.event_store import EventStore
from packages.db.goal_store import GoalStore
from packages.db.release_store import ReleaseStore
from packages.db.task_store import TaskStore
from packages.schemas.release import (
    BuildCandidate,
    BuildStatus,
    MetadataDraft,
    MetadataStatus,
    ReleaseRecord,
    ReleaseStatus,
    ScreenshotSet,
    ScreenshotStatus,
    StoreChannelStatus,
)
from packages.schemas.task_packet import RiskLevel, TaskResult, TaskStatus, WorkerLane


def load_appstore_worker_main():
    module_path = Path(__file__).resolve().parents[3] / "apps" / "worker-appstore" / "main.py"
    spec = importlib.util.spec_from_file_location("worker_appstore_main", module_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def create_release_record(release_id: str) -> None:
    store = ReleaseStore()
    store.save_build_candidate(
        BuildCandidate(
            id=f"build-{release_id}",
            product_id="fishing-logbook",
            repo_id="fishing-logbook-ios",
            source_task_run_id="run-source-1",
            version="1.0.0",
            build_number="1",
            status=BuildStatus.READY,
            created_at="2026-04-01T00:00:00+00:00",
        )
    )
    store.save_metadata_draft(
        MetadataDraft(
            id=f"metadata-{release_id}",
            product_id="fishing-logbook",
            locale="en-US",
            path="/tmp/metadata.md",
            status=MetadataStatus.READY,
            created_at="2026-04-01T00:00:00+00:00",
        )
    )
    store.save_screenshot_set(
        ScreenshotSet(
            id=f"screenshots-{release_id}",
            product_id="fishing-logbook",
            locale="en-US",
            device_family="iphone",
            asset_paths=[],
            status=ScreenshotStatus.READY,
            created_at="2026-04-01T00:00:00+00:00",
        )
    )
    store.save_release_record(
        ReleaseRecord(
            id=release_id,
            product_id="fishing-logbook",
            build_candidate_id=f"build-{release_id}",
            metadata_draft_id=f"metadata-{release_id}",
            screenshot_set_id=f"screenshots-{release_id}",
            testflight_status=StoreChannelStatus.NOT_STARTED,
            appstore_status=StoreChannelStatus.NOT_STARTED,
            status=ReleaseStatus.DRAFT,
            created_at="2026-04-01T00:00:00+00:00",
            updated_at="2026-04-01T00:00:00+00:00",
        )
    )


def test_appstore_worker_claims_executes_and_submits_through_control_plane(
    isolated_repo_root: Path,
) -> None:
    worker_appstore_main = load_appstore_worker_main()
    service = ControlPlaneService()
    create_release_record("release-prepare-1")
    goal = service.create_goal(
        title="Run App Store task through control plane",
        summary="Claim and execute one App Store task.",
    )
    task = service.create_task_for_goal(
        goal_id=goal.id,
        repo_id="fishing-logbook-ios",
        lane=WorkerLane.APPSTORE,
        title="Prepare TestFlight state",
        summary="Run the App Store lane via the control plane.",
        task_type="appstore_release",
        risk_level=RiskLevel.MEDIUM,
        constraints=[
            "release_id=release-prepare-1",
            "release_action=prepare_testflight",
        ],
    )

    result = worker_appstore_main.execute_claimed_task(
        worker_id="worker-appstore-1",
        service=service,
    )

    stored_task = TaskStore().load(task.id)
    stored_goal = GoalStore().load(goal.id)
    stored_release = ReleaseStore().load_release_record("release-prepare-1")
    events = EventStore().list()

    assert result is not None
    assert result.task_id == "release-prepare-1"
    assert stored_task.status is TaskStatus.COMPLETED
    assert stored_task.claimed_by == "worker-appstore-1"
    assert stored_task.result_summary == "Prepared release state for action prepare_testflight."
    assert stored_goal.status.value == "completed"
    assert stored_release.testflight_status is StoreChannelStatus.READY
    assert [event.event_type for event in events] == [
        "goal_created",
        "task_created",
        "task_claimed",
        "task_completed",
    ]


def test_appstore_worker_requests_approval_and_blocks_when_action_is_gated(
    isolated_repo_root: Path,
) -> None:
    worker_appstore_main = load_appstore_worker_main()
    service = ControlPlaneService()
    create_release_record("release-submit-1")
    goal = service.create_goal(
        title="Request App Store approval",
        summary="Blocked release action should request approval through control plane.",
    )
    task = service.create_task_for_goal(
        goal_id=goal.id,
        repo_id="fishing-logbook-ios",
        lane=WorkerLane.APPSTORE,
        title="Submit to App Store",
        summary="Request approval through the control plane.",
        task_type="appstore_release",
        constraints=[
            "release_id=release-submit-1",
            "release_action=submit_appstore",
        ],
    )

    result = worker_appstore_main.execute_claimed_task(
        worker_id="worker-appstore-2",
        service=service,
    )

    stored_task = TaskStore().load(task.id)
    stored_goal = GoalStore().load(goal.id)
    approval_events = [event for event in EventStore().list() if event.event_type == "approval_requested"]

    assert result is not None
    assert result.status is TaskStatus.BLOCKED
    assert result.approval_id is not None
    assert stored_task.status is TaskStatus.BLOCKED
    assert stored_goal.status.value == "in_progress"
    assert len(approval_events) == 1
    assert approval_events[0].task_id == task.id
    assert approval_events[0].payload["action"] == "submit_appstore"


def test_appstore_worker_marks_claimed_task_failed_when_execute_raises(
    isolated_repo_root: Path,
    monkeypatch,
) -> None:
    worker_appstore_main = load_appstore_worker_main()
    service = ControlPlaneService()
    create_release_record("release-fail-1")
    goal = service.create_goal(
        title="Handle App Store failure",
        summary="Claimed App Store task should fail through control plane when execute raises.",
    )
    task = service.create_task_for_goal(
        goal_id=goal.id,
        repo_id="fishing-logbook-ios",
        lane=WorkerLane.APPSTORE,
        title="Prepare failing release action",
        summary="Simulate an unhandled App Store exception.",
        task_type="appstore_release",
        constraints=[
            "release_id=release-fail-1",
            "release_action=prepare_testflight",
        ],
    )

    monkeypatch.setattr(
        worker_appstore_main,
        "execute",
        lambda task_packet: (_ for _ in ()).throw(RuntimeError("release state mutation crashed")),
    )

    try:
        worker_appstore_main.execute_claimed_task(
            worker_id="worker-appstore-3",
            service=service,
        )
    except RuntimeError:
        pass
    else:
        raise AssertionError("expected execute_claimed_task to re-raise runner exception")

    stored_task = TaskStore().load(task.id)
    failure_events = [event for event in EventStore().list() if event.event_type == "task_failed"]

    assert stored_task.status is TaskStatus.FAILED
    assert stored_task.error_summary == "App Store worker execution failed: release state mutation crashed"
    assert len(failure_events) == 1
    assert failure_events[0].task_id == task.id


def test_appstore_worker_loop_counts_processed_task_before_stop(
    isolated_repo_root: Path,
    monkeypatch,
) -> None:
    worker_appstore_main = load_appstore_worker_main()
    stop_event = Event()
    sleep_calls: list[float] = []

    def fake_execute_claimed_task(*, worker_id: str, service=None):
        return TaskResult(
            task_id="task-appstore-1",
            status=TaskStatus.COMPLETED,
            summary="done",
        )

    def fake_sleep(seconds: float) -> None:
        sleep_calls.append(seconds)
        stop_event.set()

    monkeypatch.setattr(worker_appstore_main, "execute_claimed_task", fake_execute_claimed_task)

    result = worker_appstore_main.run_worker_loop(
        worker_id="worker-appstore-1",
        poll_interval_seconds=0.25,
        stop_event=stop_event,
        sleep_fn=fake_sleep,
    )

    assert result.processed_count == 1
    assert result.stop_reason == "stop_requested"
    assert sleep_calls == [0.25]


def test_appstore_worker_loop_preserves_processed_count_when_interrupted_during_sleep(
    isolated_repo_root: Path,
    monkeypatch,
) -> None:
    worker_appstore_main = load_appstore_worker_main()

    def fake_execute_claimed_task(*, worker_id: str, service=None):
        return TaskResult(
            task_id="task-appstore-1",
            status=TaskStatus.COMPLETED,
            summary="done",
        )

    def fake_sleep(seconds: float) -> None:
        raise KeyboardInterrupt

    monkeypatch.setattr(worker_appstore_main, "execute_claimed_task", fake_execute_claimed_task)

    result = worker_appstore_main.run_worker_loop(
        worker_id="worker-appstore-1",
        poll_interval_seconds=0.25,
        sleep_fn=fake_sleep,
    )

    assert result.processed_count == 1
    assert result.idle_cycles == 0
    assert result.stop_reason == "interrupted"


def test_appstore_worker_loop_processes_tasks_and_idles_when_queue_is_empty(
    isolated_repo_root: Path,
) -> None:
    worker_appstore_main = load_appstore_worker_main()
    service = ControlPlaneService()
    create_release_record("release-loop-1")
    create_release_record("release-loop-2")
    goal = service.create_goal(
        title="Loop App Store work",
        summary="Process multiple App Store tasks before idling.",
    )
    first_task = service.create_task_for_goal(
        goal_id=goal.id,
        repo_id="fishing-logbook-ios",
        lane=WorkerLane.APPSTORE,
        title="First App Store task",
        summary="Process first App Store task.",
        task_type="appstore_release",
        constraints=[
            "release_id=release-loop-1",
            "release_action=prepare_testflight",
        ],
    )
    second_task = service.create_task_for_goal(
        goal_id=goal.id,
        repo_id="fishing-logbook-ios",
        lane=WorkerLane.APPSTORE,
        title="Second App Store task",
        summary="Process second App Store task.",
        task_type="appstore_release",
        constraints=[
            "release_id=release-loop-2",
            "release_action=prepare_testflight",
        ],
    )

    sleep_calls: list[float] = []
    stats = worker_appstore_main.run_worker_loop(
        worker_id="worker-appstore-loop",
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
    assert sleep_calls == [0.25, 0.25, 0.25]
    assert first_stored.status is TaskStatus.COMPLETED
    assert second_stored.status is TaskStatus.COMPLETED


def test_appstore_worker_loop_stops_cleanly_when_stop_is_requested(
    isolated_repo_root: Path,
) -> None:
    worker_appstore_main = load_appstore_worker_main()
    service = ControlPlaneService()
    stop_event = Event()
    sleep_calls: list[float] = []

    def fake_sleep(seconds: float) -> None:
        sleep_calls.append(seconds)
        stop_event.set()

    stats = worker_appstore_main.run_worker_loop(
        worker_id="worker-appstore-stop",
        service=service,
        poll_interval_seconds=0.5,
        stop_event=stop_event,
        sleep_fn=fake_sleep,
    )

    assert stats.processed_count == 0
    assert stats.idle_cycles == 1
    assert stats.stop_reason == "stop_requested"
    assert sleep_calls == [0.5]
