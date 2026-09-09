from __future__ import annotations

import hashlib
import json

import pytest
from fastapi.testclient import TestClient

from apps.api.main import LOCAL_OPERATOR_BEARER_TOKEN_ENV_VAR, app
from packages.config.settings import load_runtime_paths
from packages.db.task_run_store import TaskRunStore


def _persist_completion_evidence(task: dict[str, object]) -> None:
    paths = load_runtime_paths()
    task_id = str(task["id"])
    lane = str(task["lane"])
    worktree = paths.worktrees_root / "evidence-worktree"
    worktree.mkdir(parents=True, exist_ok=True)
    files = {
        "packet": worktree / "TASK_PACKET.md",
        "execution": worktree / "execution.json",
        "stdout": worktree / "stdout.log",
        "stderr": worktree / "stderr.log",
        "diff": worktree / "review.diff",
        "verification_stdout": worktree / "verification.stdout.log",
        "verification_stderr": worktree / "verification.stderr.log",
    }
    for name, path in files.items():
        path.write_text("diff --git a/a b/a\n" if name == "diff" else "evidence")
    review = paths.artifacts_root / lane / task_id / "review_summary.json"
    review.parent.mkdir(parents=True)
    testing_policy = {"tests_required": True, "test_lane": "python" if lane == "engineering" else "ios", "relevant_tests_changed": True, "failure_code": None}
    checks = [{"name": name, "passed": True, "details": "ok"} for name in ("verification_commands_passed", "tests_with_code_policy")]
    review.write_text(json.dumps({
        "task_id": task_id,
        "worktree_path": str(worktree),
        "stdout_path": str(files["stdout"]),
        "stderr_path": str(files["stderr"]),
        "diff_path": str(files["diff"]),
        "changed_files": ["source.py"],
        "validator_results": checks,
        "testing_policy": testing_policy,
        "failure_codes": [],
    }))
    artifact_paths = [str(path) for path in files.values()] + [str(review)]
    TaskRunStore().store.save(f"run-{task_id}", {
        "id": f"run-{task_id}", "task_id": task_id, "worker_lane": lane,
        "repo_id": task["repo_id"], "worktree_id": "evidence-worktree", "worktree_path": str(worktree),
        "packet_path": str(files["packet"]), "execution_result_path": str(files["execution"]),
        "execution": {"command": ["codex", "exec"], "command_display": "codex exec", "cwd": str(worktree), "stdout_path": str(files["stdout"]), "stderr_path": str(files["stderr"]), "exit_code": 0, "started_at": "2026-01-01T00:00:00+00:00", "finished_at": "2026-01-01T00:01:00+00:00", "timed_out": False},
        "pre_run_git_state": {"status_lines": [], "changed_files": [], "diff_summary": ""},
        "post_run_git_state": {"status_lines": [" M source.py"], "changed_files": ["source.py"], "diff_summary": ""},
        "diff_path": str(files["diff"]), "classification": "safe_for_review", "review_artifact_path": str(review),
        "approval_id": None, "status": "succeeded", "summary": "persisted summary",
        "started_at": "2026-01-01T00:00:00+00:00", "finished_at": "2026-01-01T00:01:00+00:00",
        "validation_checks": checks, "testing_policy": testing_policy,
        "failure_codes": [], "artifacts": artifact_paths,
        "verification_results": [{"command": ["pytest", "-q"], "cwd": str(worktree), "revision": "a" * 40, "exit_code": 0, "stdout_path": str(files["verification_stdout"]), "stderr_path": str(files["verification_stderr"]), "started_at": "2026-01-01T00:00:00+00:00", "finished_at": "2026-01-01T00:01:00+00:00", "timed_out": False, "diff_sha256": hashlib.sha256(files["diff"].read_bytes()).hexdigest()}],
    })


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
    # A listed, zero-byte-shaped review artifact is request prose, not the
    # persisted TaskRun evidence required to complete an engineering task.
    assert result_response.json()["status"] == "failed"

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
        "task_result_rejected",
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


@pytest.mark.parametrize("lane", ["engineering", "ios"])
def test_api_uses_bound_persisted_run_not_result_prose(isolated_repo_root, lane: str) -> None:
    client = TestClient(app)
    goal = client.post("/goals", json={"title": "Evidence", "summary": "Require it."}).json()
    task = client.post(
        f"/goals/{goal['id']}/tasks",
        json={"repo_id": "ai-company-os", "lane": lane, "title": "Evidence task", "summary": "Must be validated.", "task_type": "change"},
    ).json()
    assert client.post("/tasks/claim", json={"lane": lane, "worker_id": f"worker-{lane}"}).status_code == 200
    _persist_completion_evidence(task)

    response = client.post(
        f"/tasks/{task['id']}/result",
        json={"status": "completed", "summary": "untrusted prose", "worker_id": f"worker-{lane}", "artifacts": [], "events": []},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "completed"


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
