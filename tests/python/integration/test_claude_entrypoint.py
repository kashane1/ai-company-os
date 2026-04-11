"""Phase 3.3 — SupervisorSession integration tests."""

from __future__ import annotations

import pytest

from apps.api.control_plane import ControlPlaneService
from packages.policies.approvals import PolicyViolation
from packages.schemas.task_packet import TaskStatus, WorkerLane
from packages.tools.supervisor.claude_entrypoint import (
    STRATEGIC_TASK_TYPES,
    StrategicTaskDef,
    SupervisorSession,
)
from packages.tools.supervisor.enqueue import EngineeringTaskDef


def _goal(service: ControlPlaneService):
    return service.create_goal(title="claude goal", summary="claude sum")


def test_open_enqueue_close_cycle(isolated_repo_root) -> None:
    service = ControlPlaneService()
    goal = _goal(service)

    session = SupervisorSession("claude-test-1", service=service)
    with session as handle:
        task = handle.enqueue_engineering(
            task_def=EngineeringTaskDef(
                goal_id=goal.id,
                repo_id="ai-company-os",
                title="apply a docs edit",
                summary="Do a small docs edit.",
            )
        )
        assert task.lane is WorkerLane.ENGINEERING
        handle.append_event(event_type="note", payload={"msg": "midpoint"})
        summary = handle.close(summary_md="# done\nok")

    assert summary.enqueued_task_ids == (task.id,)
    assert summary.events_appended >= 3  # open + note + close

    # Fire-and-forget: the read_result is non-blocking and returns None
    # until the worker completes. We simulate a worker completion here to
    # prove the cross-session read path.
    service.claim_task(lane=WorkerLane.ENGINEERING, worker_id="w1")
    service.submit_task_result(
        task_id=task.id,
        status=TaskStatus.COMPLETED,
        summary="ok",
        worker_id="w1",
    )

    next_session = SupervisorSession("claude-test-2", service=service)
    with next_session as handle:
        completed = handle.read_result(task_id=task.id)
        assert completed is not None
        assert completed.status is TaskStatus.COMPLETED
        handle.close(summary_md="read-back ok")


def test_strategic_task_type_must_be_known(isolated_repo_root) -> None:
    service = ControlPlaneService()
    goal = _goal(service)

    with SupervisorSession("claude-test-3", service=service) as handle:
        with pytest.raises(PolicyViolation) as exc:
            handle.create_strategic_task(
                task_def=StrategicTaskDef(
                    goal_id=goal.id,
                    repo_id="ai-company-os",
                    title="bogus",
                    summary="nope",
                    task_type="NOT_A_REAL_TYPE",
                    lane=WorkerLane.SUPERVISOR,
                )
            )
        assert exc.value.code == "invalid_strategic_task_type"
        handle.close(summary_md="no strategic tasks")


def test_strategic_task_validated_on_close(isolated_repo_root) -> None:
    service = ControlPlaneService()
    goal = _goal(service)

    with SupervisorSession("claude-test-4", service=service) as handle:
        # All STRATEGIC_TASK_TYPES entries are valid on creation
        task_type = next(iter(STRATEGIC_TASK_TYPES))
        strategic = handle.create_strategic_task(
            task_def=StrategicTaskDef(
                goal_id=goal.id,
                repo_id="ai-company-os",
                title="refresh metadata",
                summary="refresh",
                task_type=task_type,
                lane=WorkerLane.SUPERVISOR,
            )
        )
        assert strategic.task_type == task_type
        summary = handle.close(summary_md="strategic ok")
        assert summary.strategic_task_ids == (strategic.id,)


def test_request_approval_threads_through_service(isolated_repo_root) -> None:
    service = ControlPlaneService()
    goal = _goal(service)

    with SupervisorSession("claude-test-5", service=service) as handle:
        approval = handle.request_approval(
            subject_type="release",
            subject_id="release-catchbook-v0.1.0",
            action="submit_appstore",
            approval_type="app_store_submission",
            summary="approve submit",
        )
        summary = handle.close(summary_md="approval threaded")

    assert approval.id in summary.approval_ids
    # Verify it landed in the control plane store
    loaded = service.approvals.load(approval.id)
    assert loaded.action == "submit_appstore"
