from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from threading import Event

from apps.api.control_plane import ControlPlaneService
from packages.db.approval_store import ApprovalStore
from packages.db.event_store import EventStore
from packages.db.goal_store import GoalStore
from packages.db.release_store import ReleaseStore
from packages.db.task_store import TaskStore
from packages.policies.approvals import PolicyViolation
from packages.policies.release_readiness import APP_STORE_SUBMISSION_APPROVAL_TYPE
from packages.schemas.approval import ApprovalRecord, ApprovalStatus
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
            product_id="catchbook",
            repo_id="catchbook-ios",
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
            product_id="catchbook",
            locale="en-US",
            path="/tmp/metadata.md",
            status=MetadataStatus.READY,
            created_at="2026-04-01T00:00:00+00:00",
        )
    )
    store.save_screenshot_set(
        ScreenshotSet(
            id=f"screenshots-{release_id}",
            product_id="catchbook",
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
            product_id="catchbook",
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
        repo_id="catchbook-ios",
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
        repo_id="catchbook-ios",
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
    approval_events = [
        event for event in EventStore().list() if event.event_type == "approval_requested"
    ]

    assert result is not None
    assert result.status is TaskStatus.BLOCKED
    assert result.approval_id is not None
    assert stored_task.status is TaskStatus.BLOCKED
    assert stored_goal.status.value == "in_progress"
    assert len(approval_events) == 1
    assert approval_events[0].task_id == task.id
    assert approval_events[0].payload["action"] == "submit_appstore"
    artifact = (
        isolated_repo_root
        / "state"
        / "artifacts"
        / "appstore"
        / task.id
        / "submission_summary.json"
    )
    assert artifact.exists()
    assert json.loads(artifact.read_text(encoding="utf-8"))["status"] == "blocked"
    assert [event.event_type for event in EventStore().list()][-1] == "task_blocked"


def test_appstore_worker_blocks_claimed_task_without_release_id(
    isolated_repo_root: Path,
) -> None:
    worker_appstore_main = load_appstore_worker_main()
    service = ControlPlaneService()
    goal = service.create_goal(
        title="Reject incomplete App Store task",
        summary="A claimed task without a release must reach a durable terminal state.",
    )
    task = service.create_task_for_goal(
        goal_id=goal.id,
        repo_id="catchbook-ios",
        lane=WorkerLane.APPSTORE,
        title="Prepare unspecified release",
        summary="No release identifier was supplied.",
        task_type="appstore_release",
        constraints=["release_action=prepare_testflight"],
    )

    result = worker_appstore_main.execute_claimed_task(
        worker_id="worker-appstore-missing-release",
        service=service,
    )

    assert result is not None
    assert result.status is TaskStatus.BLOCKED
    assert result.failure_codes == ["missing_release_id"]
    assert "release_id" in result.summary
    assert TaskStore().load(task.id).status is TaskStatus.BLOCKED
    assert EventStore().list()[-1].event_type == "task_blocked"
    artifact = (
        isolated_repo_root
        / "state"
        / "artifacts"
        / "appstore"
        / task.id
        / "submission_summary.json"
    )
    assert json.loads(artifact.read_text(encoding="utf-8"))["status"] == "blocked"


def test_appstore_worker_blocks_missing_or_mismatched_release_approval(
    isolated_repo_root: Path,
) -> None:
    worker_appstore_main = load_appstore_worker_main()
    create_release_record("release-approval-1")
    approvals = ApprovalStore()
    for approval_id, approval_type, subject_type, subject_id, action in (
        (
            "approval-wrong-release",
            "release_action",
            "release",
            "release-other",
            "submit_appstore",
        ),
        (
            "approval-wrong-type",
            "app_store_submission",
            "release",
            "release-approval-1",
            "submit_appstore",
        ),
        (
            "approval-wrong-subject",
            "release_action",
            "task",
            "release-approval-1",
            "submit_appstore",
        ),
        (
            "approval-wrong-action",
            "release_action",
            "release",
            "release-approval-1",
            "submit_testflight",
        ),
    ):
        approvals.save(
            ApprovalRecord(
                id=approval_id,
                status=ApprovalStatus.APPROVED,
                summary="Mismatched approval.",
                created_at="2026-04-01T00:00:00+00:00",
                approval_type=approval_type,
                subject_type=subject_type,
                subject_id=subject_id,
                action=action,
            )
        )

    missing = worker_appstore_main.execute_release_action(
        "release-approval-1", "submit_appstore", approval_id="approval-missing"
    )
    mismatched = [
        worker_appstore_main.execute_release_action(
            "release-approval-1", "submit_appstore", approval_id=approval_id
        )
        for approval_id in (
            "approval-wrong-release",
            "approval-wrong-type",
            "approval-wrong-subject",
            "approval-wrong-action",
        )
    ]

    assert missing.status is TaskStatus.BLOCKED
    assert all(result.status is TaskStatus.BLOCKED for result in mismatched)
    assert ReleaseStore().load_release_record("release-approval-1").appstore_status is (
        StoreChannelStatus.NOT_STARTED
    )


def test_appstore_worker_runs_release_readiness_before_local_submission_transition(
    isolated_repo_root: Path, monkeypatch
) -> None:
    worker_appstore_main = load_appstore_worker_main()
    create_release_record("release-approval-2")
    service = ControlPlaneService()
    # Safe preparation establishes the local READY_FOR_REVIEW state without
    # requiring an approval or attempting App Store Connect work.
    prepared = worker_appstore_main.execute_release_action(
        "release-approval-2", "prepare_testflight"
    )
    assert prepared.status is TaskStatus.COMPLETED
    approval = service.request_approval(
        summary="Approve the local submission transition.",
        subject_type="release",
        subject_id="release-approval-2",
        action="submit_appstore",
        approval_type=APP_STORE_SUBMISSION_APPROVAL_TYPE,
    )
    service.decide_approval(
        approval_id=approval.id,
        status=ApprovalStatus.APPROVED,
        decided_by="founder",
    )
    readiness_calls: list[tuple[str, str, str, str]] = []
    monkeypatch.setattr(
        worker_appstore_main,
        "approve_release_action",
        lambda release_id, approval_id, *, action, product_id, release_store: (
            readiness_calls.append((release_id, approval_id, product_id, action))
            or ReleaseStore().load_release_record(release_id)
        ),
    )
    goal = service.create_goal(
        title="Submit approved App Store release",
        summary="Use the approved release action.",
    )
    task = service.create_task_for_goal(
        goal_id=goal.id,
        repo_id="catchbook-ios",
        lane=WorkerLane.APPSTORE,
        title="Submit App Store release",
        summary="Submit the approved release action.",
        task_type="appstore_release",
        constraints=[
            "release_id=release-approval-2",
            "release_action=submit_appstore",
            f"approval_id={approval.id}",
        ],
    )

    result = worker_appstore_main.execute_claimed_task(
        worker_id="worker-appstore-approved",
        service=service,
    )

    assert result is not None
    assert result.status is TaskStatus.COMPLETED
    assert result.approval_id == approval.id
    assert result.validation_checks == ["release_readiness:passed"]
    assert TaskStore().load(task.id).approval_id == approval.id
    assert EventStore().list()[-1].approval_id == approval.id
    assert ReleaseStore().load_release_record("release-approval-2").appstore_status is (
        StoreChannelStatus.APPROVED
    )
    assert readiness_calls == [
        ("release-approval-2", approval.id, "catchbook", "submit_appstore")
    ]


def test_appstore_worker_blocks_local_submission_when_readiness_rejects(
    isolated_repo_root: Path, monkeypatch
) -> None:
    worker_appstore_main = load_appstore_worker_main()
    create_release_record("release-readiness-blocked")
    worker_appstore_main.execute_release_action("release-readiness-blocked", "prepare_testflight")
    approval = ApprovalRecord(
        id="approval-readiness-blocked",
        status=ApprovalStatus.APPROVED,
        summary="Approved record but incomplete checklist.",
        created_at="2026-04-01T00:00:00+00:00",
        approval_type=APP_STORE_SUBMISSION_APPROVAL_TYPE,
        subject_type="release",
        subject_id="release-readiness-blocked",
        action="submit_appstore",
    )
    ApprovalStore().save(approval)
    monkeypatch.setattr(
        worker_appstore_main,
        "approve_release_action",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            PolicyViolation("submission_checklist_incomplete", "2 items remain")
        ),
    )

    result = worker_appstore_main.execute_release_action(
        "release-readiness-blocked", "submit_appstore", approval_id=approval.id
    )

    assert result.status is TaskStatus.BLOCKED
    assert "submission_checklist_incomplete" in result.summary
    assert result.failure_codes == ["submission_checklist_incomplete"]
    assert ReleaseStore().load_release_record("release-readiness-blocked").appstore_status is (
        StoreChannelStatus.NOT_STARTED
    )


def test_appstore_worker_persists_release_readiness_rejection(
    isolated_repo_root: Path, monkeypatch
) -> None:
    worker_appstore_main = load_appstore_worker_main()
    service = ControlPlaneService()
    create_release_record("release-readiness-artifact")
    worker_appstore_main.execute_release_action(
        "release-readiness-artifact", "prepare_testflight"
    )
    approval = ApprovalRecord(
        id="approval-readiness-artifact",
        status=ApprovalStatus.APPROVED,
        summary="Approved record with incomplete readiness.",
        created_at="2026-04-01T00:00:00+00:00",
        approval_type=APP_STORE_SUBMISSION_APPROVAL_TYPE,
        subject_type="release",
        subject_id="release-readiness-artifact",
        action="submit_appstore",
    )
    ApprovalStore().save(approval)
    goal = service.create_goal(
        title="Check release readiness", summary="Persist the rejected policy result."
    )
    task = service.create_task_for_goal(
        goal_id=goal.id,
        repo_id="catchbook-ios",
        lane=WorkerLane.APPSTORE,
        title="Prepare App Store submission",
        summary="Readiness remains local.",
        task_type="appstore_release",
        constraints=[
            "release_id=release-readiness-artifact",
            "release_action=submit_appstore",
            f"approval_id={approval.id}",
        ],
    )
    monkeypatch.setattr(
        worker_appstore_main,
        "approve_release_action",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            PolicyViolation("submission_checklist_incomplete", "2 items remain")
        ),
    )

    result = worker_appstore_main.execute_claimed_task(
        worker_id="worker-appstore-readiness", service=service
    )

    assert result is not None
    assert result.status is TaskStatus.BLOCKED
    artifact = (
        isolated_repo_root
        / "state"
        / "artifacts"
        / "appstore"
        / task.id
        / "submission_summary.json"
    )
    payload = json.loads(artifact.read_text(encoding="utf-8"))
    assert payload["failure_codes"] == ["submission_checklist_incomplete"]
    assert TaskStore().load(task.id).status is TaskStatus.BLOCKED


def test_appstore_worker_blocks_unknown_release_actions(isolated_repo_root: Path) -> None:
    worker_appstore_main = load_appstore_worker_main()
    create_release_record("release-unknown-action")

    result = worker_appstore_main.execute_release_action(
        "release-unknown-action", "delete_release"
    )

    assert result.status is TaskStatus.BLOCKED
    assert (
        ReleaseStore().load_release_record("release-unknown-action").status
        is ReleaseStatus.DRAFT
    )


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
        repo_id="catchbook-ios",
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

    result = worker_appstore_main.execute_claimed_task(
        worker_id="worker-appstore-3",
        service=service,
    )

    stored_task = TaskStore().load(task.id)
    failure_events = [event for event in EventStore().list() if event.event_type == "task_failed"]

    assert stored_task.status is TaskStatus.FAILED
    assert result is not None
    assert result.status is TaskStatus.FAILED
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
        repo_id="catchbook-ios",
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
        repo_id="catchbook-ios",
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
