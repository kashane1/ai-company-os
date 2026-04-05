from __future__ import annotations

from apps.api.control_plane import ControlPlaneService
from packages.db.event_store import EventStore
from packages.db.goal_store import GoalStore
from packages.db.task_store import TaskStore
from packages.schemas.approval import ApprovalStatus
from packages.schemas.goal import GoalStatus
from packages.schemas.task_packet import RiskLevel, TaskStatus, WorkerLane


def test_control_plane_service_persists_goal_task_claim_result_and_events(
    isolated_repo_root,
) -> None:
    service = ControlPlaneService()

    goal = service.create_goal(
        title="Build the control plane",
        summary="Persist goals, tasks, approvals, and events.",
        description="Smallest real runtime slice.",
    )
    task = service.create_task_for_goal(
        goal_id=goal.id,
        repo_id="ai-company-os",
        lane=WorkerLane.ENGINEERING,
        title="Implement the service layer",
        summary="Create a durable control-plane flow.",
        task_type="engineering_change",
        risk_level=RiskLevel.MEDIUM,
    )
    claimed = service.claim_task(lane=WorkerLane.ENGINEERING, worker_id="worker-eng-1")
    completed = service.submit_task_result(
        task_id=task.id,
        status=TaskStatus.COMPLETED,
        summary="Implemented and validated.",
        worker_id="worker-eng-1",
    )

    stored_goal = GoalStore().load(goal.id)
    stored_task = TaskStore().load(task.id)
    events = EventStore().list()

    assert claimed is not None
    assert claimed.id == task.id
    assert claimed.claimed_by == "worker-eng-1"
    assert completed.status is TaskStatus.COMPLETED
    assert stored_task.result_summary == "Implemented and validated."
    assert stored_goal.status is GoalStatus.COMPLETED
    assert [event.event_type for event in events] == [
        "goal_created",
        "task_created",
        "task_claimed",
        "task_completed",
    ]


def test_control_plane_service_requests_and_decides_approval(isolated_repo_root) -> None:
    service = ControlPlaneService()
    goal = service.create_goal(
        title="Prepare release review",
        summary="Create a task that needs approval.",
    )
    task = service.create_task_for_goal(
        goal_id=goal.id,
        repo_id="fishing-logbook-ios",
        lane=WorkerLane.APPSTORE,
        title="Prepare TestFlight state",
        summary="Set up release metadata and wait for approval.",
        task_type="appstore_release",
        requires_approval=True,
    )

    approval = service.request_approval(
        summary="Approve the prepared release state.",
        subject_type="task",
        subject_id=task.id,
        action="submit_testflight",
        approval_type="release_action",
        task_id=task.id,
    )
    decided = service.decide_approval(
        approval_id=approval.id,
        status=ApprovalStatus.APPROVED,
        decided_by="founder",
        decision_notes="Proceed.",
    )

    assert approval.status is ApprovalStatus.PENDING
    assert decided.status is ApprovalStatus.APPROVED
    assert decided.decided_by == "founder"
