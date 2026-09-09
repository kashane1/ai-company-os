from __future__ import annotations

from dataclasses import replace

import pytest
from fastapi.testclient import TestClient

from apps.api.control_plane import ControlPlaneService
from apps.api.main import LOCAL_OPERATOR_BEARER_TOKEN_ENV_VAR, app
from packages.db.approval_store import ApprovalStore
from packages.db.event_store import EventStore
from packages.db.release_store import ReleaseStore
from packages.db.task_store import TaskStore
from packages.schemas.approval import ApprovalStatus
from packages.schemas.release import ReleaseStatus
from packages.schemas.task_packet import TaskStatus, WorkerLane
from tests.python.unit.test_appstore_worker_runtime import (
    create_release_record,
    load_appstore_worker_main,
)
from tests.python.unit.test_release_readiness import _seed_p0_token_and_approve, _write_checklist


def _blocked_submission_task(
    service: ControlPlaneService,
    worker,
    *,
    release_id: str,
    action: str = "submit_appstore",
):
    create_release_record(release_id)
    release_store = ReleaseStore()
    release_store.save_release_record(
        replace(release_store.load_release_record(release_id), status=ReleaseStatus.READY_FOR_REVIEW)
    )
    goal = service.create_goal(title="Resume App Store submission", summary="Synthetic approval path.")
    task = service.create_task_for_goal(
        goal_id=goal.id,
        repo_id="catchbook-ios",
        lane=WorkerLane.APPSTORE,
        title="Submit release",
        summary="Require signed approval before local state transition.",
        task_type="appstore_release",
        constraints=[f"release_id={release_id}", f"release_action={action}"],
    )
    blocked = worker.execute_claimed_task(worker_id="worker-appstore", service=service)
    assert blocked is not None
    assert blocked.status is TaskStatus.BLOCKED
    return task, blocked.approval_id


@pytest.mark.parametrize(
    "action",
    ["submit_testflight", "submit_appstore", "release_to_store"],
)
def test_signed_approval_resumes_once_through_a_linked_replacement(
    isolated_repo_root,
    action: str,
) -> None:
    worker = load_appstore_worker_main()
    service = ControlPlaneService()
    _write_checklist(isolated_repo_root, unchecked=0)
    original, approval_id = _blocked_submission_task(
        service, worker, release_id=f"release-resume-happy-{action}", action=action
    )
    assert approval_id is not None
    persisted = TaskStore().load(original.id)
    assert persisted.approval_id == approval_id

    _seed_p0_token_and_approve(
        approval_id,
        f"release-resume-happy-{action}",
        service=service,
        action=action,
    )
    replacement = service.resume_blocked_appstore_task(task_id=original.id)

    old = TaskStore().load(original.id)
    assert old.status is TaskStatus.FAILED
    assert old.approval_id == approval_id
    assert replacement.status is TaskStatus.PENDING
    assert replacement.id != original.id
    assert f"approval_id={approval_id}" in replacement.constraints
    assert f"approval_source_task_id={original.id}" in replacement.constraints

    completed = worker.execute_claimed_task(worker_id="worker-appstore", service=service)
    assert completed is not None
    assert completed.status is TaskStatus.COMPLETED
    assert TaskStore().load(replacement.id).status is TaskStatus.COMPLETED
    events = EventStore().list()
    assert sum(event.event_type == "task_completed" for event in events) == 1
    assert sum(event.event_type == "appstore_task_resumed" for event in events) == 1

    with pytest.raises(ValueError, match="blocked App Store"):
        service.resume_blocked_appstore_task(task_id=original.id)
    assert service.queue.size(WorkerLane.APPSTORE) == 0


@pytest.mark.parametrize("status", [ApprovalStatus.PENDING, ApprovalStatus.REJECTED])
def test_unapproved_appstore_task_cannot_be_resumed(isolated_repo_root, status: ApprovalStatus) -> None:
    worker = load_appstore_worker_main()
    service = ControlPlaneService()
    original, approval_id = _blocked_submission_task(
        service, worker, release_id=f"release-resume-{status.value}"
    )
    assert approval_id is not None
    if status is ApprovalStatus.REJECTED:
        service.decide_approval(
            approval_id=approval_id,
            status=ApprovalStatus.REJECTED,
            decided_by="founder",
        )

    with pytest.raises(ValueError, match="approval"):
        service.resume_blocked_appstore_task(task_id=original.id)
    assert TaskStore().load(original.id).status is TaskStatus.BLOCKED
    assert service.queue.size(WorkerLane.APPSTORE) == 0


def test_changed_release_after_approval_cannot_be_resumed(isolated_repo_root) -> None:
    worker = load_appstore_worker_main()
    service = ControlPlaneService()
    _write_checklist(isolated_repo_root, unchecked=0)
    original, approval_id = _blocked_submission_task(
        service, worker, release_id="release-resume-changed"
    )
    assert approval_id is not None
    _seed_p0_token_and_approve(approval_id, "release-resume-changed", service=service)
    release_store = ReleaseStore()
    release_store.save_release_record(
        replace(
            release_store.load_release_record("release-resume-changed"),
            status=ReleaseStatus.DRAFT,
        )
    )

    with pytest.raises(ValueError, match="reviewed revision"):
        service.resume_blocked_appstore_task(task_id=original.id)
    assert TaskStore().load(original.id).status is TaskStatus.BLOCKED


def test_changed_release_after_resume_is_blocked_before_execution(isolated_repo_root) -> None:
    worker = load_appstore_worker_main()
    service = ControlPlaneService()
    _write_checklist(isolated_repo_root, unchecked=0)
    original, approval_id = _blocked_submission_task(
        service, worker, release_id="release-resume-changed-after-resume"
    )
    assert approval_id is not None
    _seed_p0_token_and_approve(
        approval_id,
        "release-resume-changed-after-resume",
        service=service,
    )
    replacement = service.resume_blocked_appstore_task(task_id=original.id)
    release_store = ReleaseStore()
    release_store.save_release_record(
        replace(
            release_store.load_release_record("release-resume-changed-after-resume"),
            updated_at="changed-after-resume",
        )
    )

    result = worker.execute_claimed_task(worker_id="worker-appstore", service=service)
    assert result is not None
    assert result.status is TaskStatus.BLOCKED
    assert result.failure_codes == ["approval_reviewed_revision_mismatch"]
    assert TaskStore().load(replacement.id).status is TaskStatus.BLOCKED


def test_redis_resume_refuses_before_mutating_blocked_attempt(isolated_repo_root) -> None:
    worker = load_appstore_worker_main()
    service = ControlPlaneService()
    _write_checklist(isolated_repo_root, unchecked=0)
    original, approval_id = _blocked_submission_task(
        service, worker, release_id="release-resume-redis"
    )
    assert approval_id is not None
    _seed_p0_token_and_approve(approval_id, "release-resume-redis", service=service)

    class RedisProbe:
        name = "redis"

    service.queue.backend = RedisProbe()
    with pytest.raises(ValueError, match="database queue backend"):
        service.resume_blocked_appstore_task(task_id=original.id)
    assert TaskStore().load(original.id).status is TaskStatus.BLOCKED


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("subject_id", "another-release"),
        ("action", "release_to_store"),
        ("task_id", "another-task"),
    ],
)
def test_mismatched_approved_binding_cannot_resume(
    isolated_repo_root,
    field: str,
    value: str,
) -> None:
    worker = load_appstore_worker_main()
    service = ControlPlaneService()
    original, approval_id = _blocked_submission_task(
        service, worker, release_id=f"release-resume-binding-{field}"
    )
    assert approval_id is not None
    approval = ApprovalStore().load(approval_id)
    ApprovalStore().save(replace(approval, status=ApprovalStatus.APPROVED, **{field: value}))

    with pytest.raises(ValueError, match="does not match"):
        service.resume_blocked_appstore_task(task_id=original.id)
    assert TaskStore().load(original.id).status is TaskStatus.BLOCKED


def test_resume_endpoint_requires_the_local_operator_capability(
    isolated_repo_root,
    monkeypatch,
) -> None:
    worker = load_appstore_worker_main()
    service = ControlPlaneService()
    _write_checklist(isolated_repo_root, unchecked=0)
    original, approval_id = _blocked_submission_task(
        service, worker, release_id="release-resume-api"
    )
    assert approval_id is not None
    client = TestClient(app)
    assert client.post(f"/tasks/{original.id}/resume-appstore").status_code == 503

    monkeypatch.setenv(LOCAL_OPERATOR_BEARER_TOKEN_ENV_VAR, "test-local-operator-token")
    assert (
        client.post(
            f"/tasks/{original.id}/resume-appstore",
            headers={"Authorization": "Bearer wrong-token"},
        ).status_code
        == 401
    )
    _seed_p0_token_and_approve(approval_id, "release-resume-api", service=service)
    resumed = client.post(
        f"/tasks/{original.id}/resume-appstore",
        headers={"Authorization": "Bearer test-local-operator-token"},
    )
    assert resumed.status_code == 200
    assert resumed.json()["status"] == "pending"


def test_resume_endpoint_reports_readiness_conflict_without_mutating_task(isolated_repo_root, monkeypatch):
    worker = load_appstore_worker_main()
    service = ControlPlaneService()
    _write_checklist(isolated_repo_root, unchecked=1)
    original, approval_id = _blocked_submission_task(service, worker, release_id='release-not-ready')
    _seed_p0_token_and_approve(approval_id, 'release-not-ready', service=service)
    monkeypatch.setenv(LOCAL_OPERATOR_BEARER_TOKEN_ENV_VAR, 'test-local-operator-token')
    client = TestClient(app, raise_server_exceptions=False)
    response = client.post(f'/tasks/{original.id}/resume-appstore', headers={'Authorization': 'Bearer test-local-operator-token'})
    assert response.status_code == 409
    assert 'submission_checklist_incomplete' in response.json()['detail']
    assert TaskStore().load(original.id).status is TaskStatus.BLOCKED
    assert len(TaskStore().list_for_goal(original.goal_id)) == 1
