from __future__ import annotations

import pytest

from apps.api.control_plane import ControlPlaneService
from packages.db.event_store import EventStore
from packages.db.goal_store import GoalStore
from packages.db.task_store import TaskStore
from packages.policies import worker_capabilities
from packages.queue import QueueClaimOwnershipError
from packages.schemas.approval import ApprovalStatus
from packages.schemas.goal import GoalStatus
from packages.schemas.task_packet import RiskLevel, TaskStatus, WorkerLane
from tests.python.factories.completion_evidence import persist_completion_evidence


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
    artifact = persist_completion_evidence(task)
    completed = service.submit_task_result(
        task_id=task.id,
        status=TaskStatus.COMPLETED,
        summary="Implemented and validated.",
        worker_id="worker-eng-1",
        artifacts=[artifact],
        events=["task_claimed"],
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


@pytest.mark.parametrize(
    "lane",
    [WorkerLane.GTM, WorkerLane.WEB, WorkerLane.WEBDEPLOY],
)
def test_control_plane_rejects_unconsumed_lane_before_enqueue(
    isolated_repo_root, lane: WorkerLane
) -> None:
    service = ControlPlaneService()
    goal = service.create_goal(title="Publish a landing page", summary="Route web work.")

    try:
        service.create_task_for_goal(
            goal_id=goal.id,
            repo_id="ai-company-os",
            lane=lane,
            title="Build marketing site",
            summary="Create the site.",
            task_type="web_build",
        )
    except ValueError as exc:
        assert "manual" in str(exc)
        assert "unsupported" in str(exc)
    else:
        raise AssertionError("unconsumed WEB task must not enter the queue")

    assert service.list_tasks_for_goal(goal.id) == []
    assert service.queue.size() == 0


def test_worker_capability_table_classifies_every_lane() -> None:
    LANE_CAPABILITIES = worker_capabilities.LANE_CAPABILITIES
    LaneExecutionMode = worker_capabilities.LaneExecutionMode
    assert set(LANE_CAPABILITIES) == set(WorkerLane)
    assert LANE_CAPABILITIES[WorkerLane.ENGINEERING].execution_mode is (
        LaneExecutionMode.SUPERVISED
    )
    assert LANE_CAPABILITIES[WorkerLane.GTM].execution_mode is (
        LaneExecutionMode.OPERATOR_INVOKED
    )
    assert not LANE_CAPABILITIES[WorkerLane.GTM].accepts_queued_tasks


def test_control_plane_rejects_completed_result_without_actual_evidence(
    isolated_repo_root,
) -> None:
    service = ControlPlaneService()
    goal = service.create_goal(title="Validate task result", summary="Require evidence.")
    task = service.create_task_for_goal(
        goal_id=goal.id,
        repo_id="ai-company-os",
        lane=WorkerLane.ENGINEERING,
        title="Produce review evidence",
        summary="A task with no artifact.",
        task_type="engineering_change",
    )
    service.claim_task(lane=WorkerLane.ENGINEERING, worker_id="worker-eng-1")

    rejected = service.submit_task_result(
        task_id=task.id,
        status=TaskStatus.COMPLETED,
        summary="Claimed completion without evidence.",
        worker_id="worker-eng-1",
        artifacts=["state/artifacts/engineering/missing/review_summary.json"],
        events=["task_claimed"],
    )

    assert rejected.status is TaskStatus.FAILED
    assert rejected.error_summary is not None
    assert "task_run_missing" in rejected.error_summary
    assert EventStore().list()[-1].event_type == "task_result_rejected"


def test_control_plane_rejects_completed_result_when_validator_is_unavailable(
    isolated_repo_root, monkeypatch
) -> None:
    import apps.api.control_plane as control_plane_module
    from packages.tools.skills.loader import SkillNotFound

    service = ControlPlaneService()
    goal = service.create_goal(title="Require validator", summary="Fail closed.")
    task = service.create_task_for_goal(
        goal_id=goal.id,
        repo_id="ai-company-os",
        lane=WorkerLane.ENGINEERING,
        title="Validator must run",
        summary="No validator bypass.",
        task_type="engineering_change",
    )
    service.claim_task(lane=WorkerLane.ENGINEERING, worker_id="worker-eng-1")
    artifact = persist_completion_evidence(task)
    monkeypatch.setattr(
        control_plane_module,
        "load_validator",
        lambda _: (_ for _ in ()).throw(SkillNotFound("not installed")),
    )

    rejected = service.submit_task_result(
        task_id=task.id,
        status=TaskStatus.COMPLETED,
        summary="Completion evidence exists.",
        worker_id="worker-eng-1",
        artifacts=[artifact],
        events=["task_completed"],
    )

    assert rejected.status is TaskStatus.FAILED
    assert "validator_unavailable" in (rejected.error_summary or "")


def test_control_plane_rejects_completed_result_when_validator_has_no_runner(
    isolated_repo_root, monkeypatch
) -> None:
    import apps.api.control_plane as control_plane_module

    service = ControlPlaneService()
    goal = service.create_goal(title="Require runnable validator", summary="Fail closed.")
    task = service.create_task_for_goal(
        goal_id=goal.id,
        repo_id="ai-company-os",
        lane=WorkerLane.ENGINEERING,
        title="Validator must be runnable",
        summary="No null validator bypass.",
        task_type="engineering_change",
    )
    service.claim_task(lane=WorkerLane.ENGINEERING, worker_id="worker-eng-1")
    artifact = persist_completion_evidence(task)
    monkeypatch.setattr(control_plane_module, "load_validator", lambda _: None)

    rejected = service.submit_task_result(
        task_id=task.id,
        status=TaskStatus.COMPLETED,
        summary="The validator loader returned no runner.",
        worker_id="worker-eng-1",
        artifacts=[artifact],
        events=["task_claimed"],
    )

    assert rejected.status is TaskStatus.FAILED
    assert "validator_unavailable" in (rejected.error_summary or "")


def test_control_plane_uses_persisted_events_instead_of_submission_events(isolated_repo_root) -> None:
    service = ControlPlaneService()
    goal = service.create_goal(title="Verify events", summary="Use durable evidence.")
    task = service.create_task_for_goal(
        goal_id=goal.id,
        repo_id="ai-company-os",
        lane=WorkerLane.ENGINEERING,
        title="Produce review evidence",
        summary="Persist a review artifact.",
        task_type="engineering_change",
    )
    service.claim_task(lane=WorkerLane.ENGINEERING, worker_id="worker-eng-1")
    artifact = persist_completion_evidence(task)

    completed = service.submit_task_result(
        task_id=task.id,
        status=TaskStatus.COMPLETED,
        summary="Named an event that was never persisted.",
        worker_id="worker-eng-1",
        artifacts=[artifact],
        events=["task_completed"],
    )

    assert completed.status is TaskStatus.COMPLETED


def test_control_plane_rejects_result_from_non_claiming_worker(isolated_repo_root) -> None:
    service = ControlPlaneService()
    goal = service.create_goal(title="Fence claims", summary="Only the owner finalizes.")
    task = service.create_task_for_goal(
        goal_id=goal.id,
        repo_id="ai-company-os",
        lane=WorkerLane.ENGINEERING,
        title="Owned task",
        summary="Claim then finalize.",
        task_type="engineering_change",
    )
    service.claim_task(lane=WorkerLane.ENGINEERING, worker_id="worker-owner")
    original_fail = service.tasks.fail
    fail_called = False

    def record_fail(*args, **kwargs):
        nonlocal fail_called
        fail_called = True
        return original_fail(*args, **kwargs)

    service.tasks.fail = record_fail  # type: ignore[method-assign]
    service.queue.assert_claim_owner = lambda *_args, **_kwargs: (_ for _ in ()).throw(
        QueueClaimOwnershipError("worker lost claim")
    )

    with pytest.raises(QueueClaimOwnershipError, match="lost claim"):
        service.submit_task_result(
            task_id=task.id,
            status=TaskStatus.FAILED,
            summary="A different worker tried to finalize.",
            worker_id="worker-owner",
        )

    assert TaskStore().load(task.id).status is TaskStatus.IN_PROGRESS
    assert not fail_called


def test_control_plane_service_requests_and_decides_approval(isolated_repo_root) -> None:
    service = ControlPlaneService()
    goal = service.create_goal(
        title="Prepare release review",
        summary="Create a task that needs approval.",
    )
    task = service.create_task_for_goal(
        goal_id=goal.id,
        repo_id="catchbook-ios",
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
