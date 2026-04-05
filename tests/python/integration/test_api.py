from __future__ import annotations

from fastapi.testclient import TestClient

from apps.api.main import app


def test_api_supports_goal_task_claim_and_approval_flow(isolated_repo_root) -> None:
    client = TestClient(app)

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
        },
    )
    assert approval_response.status_code == 200
    approval = approval_response.json()

    result_response = client.post(
        f"/tasks/{task['id']}/result",
        json={
            "status": "completed",
            "summary": "Done.",
            "worker_id": "worker-eng-1",
            "approval_id": approval["id"],
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
    )
    assert decision_response.status_code == 200
    assert decision_response.json()["status"] == "approved"

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
