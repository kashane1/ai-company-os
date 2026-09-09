from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from apps.api.main import LOCAL_OPERATOR_BEARER_TOKEN_ENV_VAR, app
from packages.config.settings import load_runtime_paths


def test_api_supports_goal_task_claim_and_approval_flow(isolated_repo_root, monkeypatch) -> None:
    client = TestClient(app)
    monkeypatch.setenv(LOCAL_OPERATOR_BEARER_TOKEN_ENV_VAR, "test-local-operator-token")

    goal_response = client.post(
        "/goals",
        json={
            "title": "Run the company control plane",
            "summary": "Create a real goal/task lifecycle.",
            "description": "Minimal HTTP surface.",
        },
    )
    assert goal_response.status_code == 200
    goal = goal_response.json()

    task_response = client.post(
        f"/goals/{goal['id']}/tasks",
        json={
            "repo_id": "ai-company-os",
            "lane": "engineering",
            "title": "Wire the queue",
            "summary": "Create the queue-backed task claim shape.",
            "task_type": "engineering_change",
            "risk_level": "medium",
            "constraints": ["keep it lean"],
        },
    )
    assert task_response.status_code == 200
    task = task_response.json()

    listed_tasks = client.get(f"/goals/{goal['id']}/tasks")
    assert listed_tasks.status_code == 200
    assert [item["id"] for item in listed_tasks.json()] == [task["id"]]

    claim_response = client.post(
        "/tasks/claim",
        json={"lane": "engineering", "worker_id": "worker-eng-1"},
    )
    assert claim_response.status_code == 200
    claimed = claim_response.json()
    assert claimed["id"] == task["id"]
    assert claimed["claimed_by"] == "worker-eng-1"

    approval_response = client.post(
        "/approvals",
        json={
            "summary": "Review the claimed task.",
            "subject_type": "task",
            "subject_id": task["id"],
            "action": "review_task",
            "approval_type": "engineering_review",
            "task_id": task["id"],
            "reviewed_revision": "sha256:reviewed-task-inputs",
        },
    )
    assert approval_response.status_code == 200
    approval = approval_response.json()

    artifact = (
        load_runtime_paths().artifacts_root
        / "engineering"
        / task["id"]
        / "review_summary.json"
    )
    artifact.parent.mkdir(parents=True)
    artifact.write_text("{}", encoding="utf-8")

    result_response = client.post(
        f"/tasks/{task['id']}/result",
        json={
            "status": "completed",
            "summary": "Done.",
            "worker_id": "worker-eng-1",
            "approval_id": approval["id"],
            "artifacts": [str(artifact)],
            "events": ["task_claimed"],
        },
    )
    assert result_response.status_code == 200
    assert result_response.json()["status"] == "completed"

    decision_response = client.post(
        f"/approvals/{approval['id']}/decision",
        json={
            "status": "approved",
            "decided_by": "founder",
            "decision_notes": "Ship it.",
        },
        headers={"Authorization": "Bearer test-local-operator-token"},
    )
    assert decision_response.status_code == 200
    assert decision_response.json()["status"] == "approved"
    assert approval_response.json()["reviewed_revision"] == "sha256:reviewed-task-inputs"

    events_response = client.get("/events")
    assert events_response.status_code == 200
    assert [event["event_type"] for event in events_response.json()] == [
        "goal_created",
        "task_created",
        "task_claimed",
        "approval_requested",
        "task_completed",
        "approval_decided",
    ]


def test_api_rejects_completed_result_when_evidence_is_omitted(isolated_repo_root) -> None:
    client = TestClient(app)
    goal = client.post("/goals", json={"title": "Evidence", "summary": "Require it."}).json()
    task = client.post(
        f"/goals/{goal['id']}/tasks",
        json={
            "repo_id": "ai-company-os",
            "lane": "engineering",
            "title": "Evidence task",
            "summary": "Must be validated.",
            "task_type": "engineering_change",
        },
    ).json()
    assert client.post(
        "/tasks/claim", json={"lane": "engineering", "worker_id": "worker-eng-1"}
    ).status_code == 200

    response = client.post(
        f"/tasks/{task['id']}/result",
        json={"status": "completed", "summary": "Done.", "worker_id": "worker-eng-1"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "failed"


@pytest.mark.parametrize("lane", ["gtm", "web", "webdeploy"])
def test_api_returns_actionable_error_without_queueing_unsupported_lane(
    isolated_repo_root, lane: str
) -> None:
    client = TestClient(app)
    goal = client.post(
        "/goals", json={"title": "Manual work", "summary": "Do not strand it."}
    ).json()

    response = client.post(
        f"/goals/{goal['id']}/tasks",
        json={
            "repo_id": "ai-company-os",
            "lane": lane,
            "title": "Unsupported queued work",
            "summary": "Use the documented manual path.",
            "task_type": "manual_operation",
        },
    )

    assert response.status_code == 422
    assert "manual" in response.json()["detail"]
    assert client.get(f"/goals/{goal['id']}/tasks").json() == []


def test_approval_decision_requires_configured_local_operator_capability(
    isolated_repo_root, monkeypatch
) -> None:
    client = TestClient(app)
    approval = client.post(
        "/approvals",
        json={
            "summary": "Review a local change.",
            "subject_type": "task",
            "subject_id": "task-1",
            "action": "review_task",
            "approval_type": "engineering_review",
        },
    ).json()

    unavailable = client.post(
        f"/approvals/{approval['id']}/decision",
        json={"status": "approved", "decided_by": "founder"},
    )
    assert unavailable.status_code == 503

    monkeypatch.setenv(LOCAL_OPERATOR_BEARER_TOKEN_ENV_VAR, "test-local-operator-token")
    wrong_token = client.post(
        f"/approvals/{approval['id']}/decision",
        json={"status": "approved", "decided_by": "founder"},
        headers={"Authorization": "Bearer wrong-token"},
    )
    assert wrong_token.status_code == 401

    accepted = client.post(
        f"/approvals/{approval['id']}/decision",
        json={"status": "approved", "decided_by": "founder"},
        headers={"Authorization": "Bearer test-local-operator-token"},
    )
    assert accepted.status_code == 200
    assert accepted.json()["status"] == "approved"


def test_generic_decision_route_cannot_approve_p0_action(isolated_repo_root, monkeypatch) -> None:
    client = TestClient(app)
    monkeypatch.setenv(LOCAL_OPERATOR_BEARER_TOKEN_ENV_VAR, "test-local-operator-token")
    approval = client.post(
        "/approvals",
        json={
            "summary": "Submit this release.",
            "subject_type": "release",
            "subject_id": "catchbook-1.0",
            "action": "submit_appstore",
            "approval_type": "app_store_submission",
        },
    ).json()
    headers = {"Authorization": "Bearer test-local-operator-token"}

    direct_approval = client.post(
        f"/approvals/{approval['id']}/decision",
        json={"status": "approved", "decided_by": "founder"},
        headers=headers,
    )
    assert direct_approval.status_code == 409

    rejection = client.post(
        f"/approvals/{approval['id']}/decision",
        json={"status": "rejected", "decided_by": "founder"},
        headers=headers,
    )
    assert rejection.status_code == 200
    assert rejection.json()["status"] == "rejected"
