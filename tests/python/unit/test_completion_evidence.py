from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from packages.db.task_run_store import TaskRunStore
from packages.policies.completion_evidence import validate_completion_evidence
from packages.schemas.task_packet import WorkerLane
from tests.python.factories.task_data import build_task


def _write(path: Path, content: str = "evidence") -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return str(path)


def _persist_complete_run(tmp_path: Path, lane: WorkerLane) -> tuple[object, dict[str, object]]:
    task = build_task(task_id=f"task-{lane.value}", lane=lane)
    worktree = tmp_path / "worktree"
    worktree.mkdir()
    packet = _write(worktree / "TASK_PACKET.md")
    execution_result = _write(worktree / "execution.json")
    stdout = _write(worktree / "stdout.log")
    stderr = _write(worktree / "stderr.log")
    diff = _write(worktree / "review.diff", "diff --git a/a b/a\n")
    verification_stdout = _write(worktree / "verification" / "01.stdout.log")
    verification_stderr = _write(worktree / "verification" / "01.stderr.log")
    review = tmp_path / "state" / "artifacts" / lane.value / task.id / "review_summary.json"
    testing_policy = {"tests_required": True, "test_lane": "python" if lane is WorkerLane.ENGINEERING else "ios", "relevant_tests_changed": True, "failure_code": None}
    checks = [{"name": name, "passed": True, "details": "ok"} for name in ("verification_commands_passed", "tests_with_code_policy")]
    review_payload = {
        "task_id": task.id,
        "worktree_path": str(worktree),
        "stdout_path": stdout,
        "stderr_path": stderr,
        "diff_path": diff,
        "changed_files": ["source.py"],
        "validator_results": checks,
        "testing_policy": testing_policy,
        "failure_codes": [],
    }
    _write(review, json.dumps(review_payload))
    diff_hash = hashlib.sha256(Path(diff).read_bytes()).hexdigest()
    payload: dict[str, object] = {
        "id": f"run-{task.id}", "task_id": task.id, "worker_lane": lane.value,
        "repo_id": task.repo_id, "worktree_id": "worktree-1", "worktree_path": str(worktree),
        "packet_path": packet, "execution_result_path": execution_result,
        "execution": {"command": ["codex", "exec"], "command_display": "codex exec", "cwd": str(worktree), "stdout_path": stdout, "stderr_path": stderr, "exit_code": 0, "started_at": "2026-01-01T00:00:00+00:00", "finished_at": "2026-01-01T00:01:00+00:00", "timed_out": False},
        "pre_run_git_state": {"status_lines": [], "changed_files": [], "diff_summary": ""},
        "post_run_git_state": {"status_lines": [" M source.py"], "changed_files": ["source.py"], "diff_summary": ""},
        "diff_path": diff, "classification": "safe_for_review", "review_artifact_path": str(review),
        "approval_id": None, "status": "succeeded", "summary": "persisted summary",
        "started_at": "2026-01-01T00:00:00+00:00", "finished_at": "2026-01-01T00:01:00+00:00",
        "validation_checks": checks,
        "testing_policy": testing_policy, "failure_codes": [],
        "artifacts": [packet, execution_result, stdout, stderr, diff, str(review), verification_stdout, verification_stderr],
        "verification_results": [{"command": ["pytest", "-q"], "cwd": str(worktree), "revision": "a" * 40, "exit_code": 0, "stdout_path": verification_stdout, "stderr_path": verification_stderr, "started_at": "2026-01-01T00:00:00+00:00", "finished_at": "2026-01-01T00:01:00+00:00", "timed_out": False, "diff_sha256": diff_hash}],
    }
    TaskRunStore().store.save(f"run-{task.id}", payload)
    return task, payload


@pytest.mark.parametrize("lane", [WorkerLane.ENGINEERING, WorkerLane.IOS])
def test_accepts_bound_persisted_evidence(tmp_path: Path, lane: WorkerLane) -> None:
    task, _ = _persist_complete_run(tmp_path, lane)

    outcome = validate_completion_evidence(task)

    assert outcome.ok
    assert outcome.task_run_id == f"run-{task.id}"


@pytest.mark.parametrize(
    ("mutate", "failure_code"),
    [
        (lambda payload: payload.__setitem__("task_id", "other-task"), "task_run_task_mismatch"),
        (lambda payload: payload["validation_checks"][0].__setitem__("passed", "false"), "validation_check_malformed"),
        (lambda payload: payload.__setitem__("verification_results", []), "verification_missing"),
        (lambda payload: payload["verification_results"][0].__setitem__("exit_code", 1), "verification_failed"),
    ],
)
def test_rejects_malformed_or_failed_persisted_evidence(tmp_path: Path, mutate, failure_code: str) -> None:
    task, payload = _persist_complete_run(tmp_path, WorkerLane.ENGINEERING)
    mutate(payload)
    TaskRunStore().store.save(f"run-{task.id}", payload)

    outcome = validate_completion_evidence(task)

    assert not outcome.ok
    assert outcome.failure_code == failure_code
