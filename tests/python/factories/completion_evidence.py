from __future__ import annotations

import hashlib
import json

from packages.config.settings import load_runtime_paths
from packages.db.task_run_store import TaskRunStore
from packages.schemas.task import Task


def persist_completion_evidence(task: Task) -> str:
    """Write a minimal, internally consistent worker TaskRun for API tests."""
    paths = load_runtime_paths()
    worktree = paths.worktrees_root / f"evidence-{task.id}"
    worktree.mkdir(parents=True, exist_ok=True)
    files = {name: worktree / filename for name, filename in {
        "packet": "TASK_PACKET.md", "execution": "execution.json", "stdout": "stdout.log",
        "stderr": "stderr.log", "diff": "review.diff", "verification_stdout": "verification.stdout.log",
        "verification_stderr": "verification.stderr.log",
    }.items()}
    for name, path in files.items():
        path.write_text("diff --git a/a b/a\n" if name == "diff" else "evidence")
    review = paths.artifacts_root / task.lane.value / task.id / "review_summary.json"
    review.parent.mkdir(parents=True)
    testing_policy = {"tests_required": True, "test_lane": "python" if task.lane.value == "engineering" else "ios", "relevant_tests_changed": True, "failure_code": None}
    checks = [{"name": name, "passed": True, "details": "ok"} for name in ("verification_commands_passed", "tests_with_code_policy")]
    review.write_text(json.dumps({"task_id": task.id, "worktree_path": str(worktree), "stdout_path": str(files["stdout"]), "stderr_path": str(files["stderr"]), "diff_path": str(files["diff"]), "changed_files": ["source.py"], "validator_results": checks, "testing_policy": testing_policy, "failure_codes": []}))
    artifacts = [str(path) for path in files.values()] + [str(review)]
    TaskRunStore().store.save(f"run-{task.id}", {"id": f"run-{task.id}", "task_id": task.id, "worker_lane": task.lane.value, "repo_id": task.repo_id, "worktree_id": f"evidence-{task.id}", "worktree_path": str(worktree), "packet_path": str(files["packet"]), "execution_result_path": str(files["execution"]), "execution": {"command": ["codex", "exec"], "command_display": "codex exec", "cwd": str(worktree), "stdout_path": str(files["stdout"]), "stderr_path": str(files["stderr"]), "exit_code": 0, "started_at": "2026-01-01T00:00:00+00:00", "finished_at": "2026-01-01T00:01:00+00:00", "timed_out": False}, "pre_run_git_state": {"status_lines": [], "changed_files": [], "diff_summary": ""}, "post_run_git_state": {"status_lines": [" M source.py"], "changed_files": ["source.py"], "diff_summary": ""}, "diff_path": str(files["diff"]), "classification": "safe_for_review", "review_artifact_path": str(review), "approval_id": None, "status": "succeeded", "summary": "persisted summary", "started_at": "2026-01-01T00:00:00+00:00", "finished_at": "2026-01-01T00:01:00+00:00", "validation_checks": checks, "testing_policy": testing_policy, "failure_codes": [], "artifacts": artifacts, "verification_results": [{"command": ["pytest", "-q"], "cwd": str(worktree), "revision": "a" * 40, "exit_code": 0, "stdout_path": str(files["verification_stdout"]), "stderr_path": str(files["verification_stderr"]), "started_at": "2026-01-01T00:00:00+00:00", "finished_at": "2026-01-01T00:01:00+00:00", "timed_out": False, "diff_sha256": hashlib.sha256(files["diff"].read_bytes()).hexdigest()}]})
    return str(review)
