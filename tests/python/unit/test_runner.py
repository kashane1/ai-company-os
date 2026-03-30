from __future__ import annotations

from pathlib import Path

import pytest

from engineering import runner
from packages.db.task_run_store import TaskRunStore
from packages.db.task_store import TaskStore
from packages.db.worktree_store import WorktreeStore
from packages.schemas.approval import ApprovalRecord, ApprovalStatus
from packages.schemas.task_packet import TaskStatus
from packages.schemas.task_run import (
    CodexExecutionRecord,
    EngineeringResultClassification,
    GitStateSnapshot,
    ValidationCheck,
)
from tests.python.factories.task_data import build_repo_config, build_repo_record, build_task, build_worktree_metadata


def build_execution_record() -> CodexExecutionRecord:
    return CodexExecutionRecord(
        command=["codex", "exec"],
        command_display="codex exec",
        cwd="/tmp/worktree",
        stdout_path="/tmp/stdout.log",
        stderr_path="/tmp/stderr.log",
        exit_code=0,
        started_at="2026-03-30T00:00:00+00:00",
        finished_at="2026-03-30T00:01:00+00:00",
        timed_out=False,
    )


def build_git_state(*, changed_files: list[str]) -> GitStateSnapshot:
    return GitStateSnapshot(status_lines=[f"M  {path}" for path in changed_files], changed_files=changed_files, diff_summary="")


def test_execute_task_marks_safe_for_review_runs_completed_and_creates_approval(
    isolated_repo_root: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    task = build_task(task_id="task-safe", repo_id="repo-safe")
    TaskStore().save(task)
    worktree_root = isolated_repo_root / "state" / "worktrees" / "repo-safe" / "task-safe"
    worktree_root.mkdir(parents=True)
    approval = ApprovalRecord(
        id="approval-task-safe",
        task_id=task.id,
        status=ApprovalStatus.PENDING,
        summary="Ready for review",
        created_at="2026-03-30T00:02:00+00:00",
        subject_id="run-task-safe",
        action="review_engineering_task",
    )
    prepare_worktree_result = build_worktree_metadata(str(worktree_root))
    repo_record = build_repo_record(repo_id="repo-safe", managed_path=str(isolated_repo_root / "state" / "repos" / "repo-safe"))

    monkeypatch.setattr(runner, "load_repo_configs", lambda: {"repo-safe": build_repo_config(repo_id="repo-safe")})
    monkeypatch.setattr(runner, "prepare_repo", lambda repo_config: repo_record)
    monkeypatch.setattr(runner, "prepare_worktree", lambda task_arg, repo_arg: prepare_worktree_result)
    monkeypatch.setattr(runner, "render_task_packet", lambda task_arg, worktree_arg: str(worktree_root / "codex_task_packet.md"))
    monkeypatch.setattr(
        runner,
        "capture_git_state",
        lambda root_path, _states=iter(
            [build_git_state(changed_files=[]), build_git_state(changed_files=["src/app.py"])]
        ): next(_states),
    )
    monkeypatch.setattr(
        runner,
        "execute_codex",
        lambda task_arg, worktree_arg, packet_path: (
            str(worktree_root / "codex_last_message.md"),
            build_execution_record(),
            str(isolated_repo_root / "state" / "artifacts" / task.id / "summary.txt"),
            str(worktree_root / "codex_execution.json"),
        ),
    )
    monkeypatch.setattr(runner, "capture_diff", lambda worktree_arg, task_id: str(worktree_root / "changes.diff"))
    monkeypatch.setattr(
        runner,
        "validate_run",
        lambda *args: [ValidationCheck(name="tests", passed=True, details="ok")],
    )
    monkeypatch.setattr(
        runner, "classify_result", lambda *args: EngineeringResultClassification.SAFE_FOR_REVIEW
    )
    monkeypatch.setattr(runner, "build_summary", lambda *args: "Ready for review")
    monkeypatch.setattr(
        runner,
        "write_review_artifact",
        lambda **kwargs: str(isolated_repo_root / "state" / "artifacts" / task.id / "review_summary.json"),
    )
    monkeypatch.setattr(runner, "create_approval_record", lambda **kwargs: approval)

    result = runner.execute_task(task.id)
    saved_task = TaskStore().load(task.id)
    saved_run = TaskRunStore().load("run-task-safe")
    saved_worktree = WorktreeStore().load("worktree-123")

    assert result.status is TaskStatus.COMPLETED
    assert result.classification == "safe_for_review"
    assert result.approval_id == "approval-task-safe"
    assert saved_task.status is TaskStatus.COMPLETED
    assert saved_run.classification is EngineeringResultClassification.SAFE_FOR_REVIEW
    assert saved_run.approval_id == "approval-task-safe"
    assert saved_run.artifacts == [
        str(worktree_root / "codex_task_packet.md"),
        str(worktree_root / "codex_last_message.md"),
        "/tmp/stdout.log",
        "/tmp/stderr.log",
        str(worktree_root / "changes.diff"),
        str(isolated_repo_root / "state" / "artifacts" / task.id / "review_summary.json"),
        str(isolated_repo_root / "state" / "artifacts" / task.id / "summary.txt"),
        str(worktree_root / "codex_execution.json"),
    ]
    assert saved_worktree.packet_path == str(worktree_root / "codex_task_packet.md")


def test_execute_task_marks_no_change_runs_completed_without_approval(
    isolated_repo_root: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    task = build_task(task_id="task-no-change", repo_id="repo-no-change")
    TaskStore().save(task)
    worktree_root = isolated_repo_root / "state" / "worktrees" / "repo-no-change" / "task-no-change"
    worktree_root.mkdir(parents=True)
    repo_record = build_repo_record(repo_id="repo-no-change")

    monkeypatch.setattr(runner, "load_repo_configs", lambda: {"repo-no-change": build_repo_config(repo_id="repo-no-change")})
    monkeypatch.setattr(runner, "prepare_repo", lambda repo_config: repo_record)
    monkeypatch.setattr(runner, "prepare_worktree", lambda task_arg, repo_arg: build_worktree_metadata(str(worktree_root)))
    monkeypatch.setattr(runner, "render_task_packet", lambda task_arg, worktree_arg: str(worktree_root / "codex_task_packet.md"))
    monkeypatch.setattr(
        runner,
        "capture_git_state",
        lambda root_path: build_git_state(changed_files=[]),
    )
    monkeypatch.setattr(
        runner,
        "execute_codex",
        lambda task_arg, worktree_arg, packet_path: (
            str(worktree_root / "codex_last_message.md"),
            build_execution_record(),
            str(isolated_repo_root / "state" / "artifacts" / task.id / "summary.txt"),
            str(worktree_root / "codex_execution.json"),
        ),
    )
    monkeypatch.setattr(runner, "capture_diff", lambda worktree_arg, task_id: str(worktree_root / "changes.diff"))
    monkeypatch.setattr(
        runner,
        "validate_run",
        lambda *args: [ValidationCheck(name="tests", passed=True, details="ok")],
    )
    monkeypatch.setattr(runner, "classify_result", lambda *args: EngineeringResultClassification.NO_CHANGE)
    monkeypatch.setattr(runner, "build_summary", lambda *args: "No tracked changes")
    monkeypatch.setattr(
        runner,
        "write_review_artifact",
        lambda **kwargs: str(isolated_repo_root / "state" / "artifacts" / task.id / "review_summary.json"),
    )

    result = runner.execute_task(task.id)
    saved_task = TaskStore().load(task.id)
    saved_run = TaskRunStore().load("run-task-no-change")

    assert result.status is TaskStatus.COMPLETED
    assert result.approval_id is None
    assert saved_task.status is TaskStatus.COMPLETED
    assert saved_run.approval_id is None
    assert saved_run.classification is EngineeringResultClassification.NO_CHANGE


def test_execute_task_marks_validation_failures_failed_without_approval(
    isolated_repo_root: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    task = build_task(task_id="task-validation-failed", repo_id="repo-validation")
    TaskStore().save(task)
    worktree_root = isolated_repo_root / "state" / "worktrees" / "repo-validation" / "task-validation-failed"
    worktree_root.mkdir(parents=True)
    repo_record = build_repo_record(repo_id="repo-validation")

    monkeypatch.setattr(runner, "load_repo_configs", lambda: {"repo-validation": build_repo_config(repo_id="repo-validation")})
    monkeypatch.setattr(runner, "prepare_repo", lambda repo_config: repo_record)
    monkeypatch.setattr(runner, "prepare_worktree", lambda task_arg, repo_arg: build_worktree_metadata(str(worktree_root)))
    monkeypatch.setattr(runner, "render_task_packet", lambda task_arg, worktree_arg: str(worktree_root / "codex_task_packet.md"))
    monkeypatch.setattr(
        runner,
        "capture_git_state",
        lambda root_path, _states=iter(
            [build_git_state(changed_files=[]), build_git_state(changed_files=["src/app.py"])]
        ): next(_states),
    )
    monkeypatch.setattr(
        runner,
        "execute_codex",
        lambda task_arg, worktree_arg, packet_path: (
            str(worktree_root / "codex_last_message.md"),
            build_execution_record(),
            str(isolated_repo_root / "state" / "artifacts" / task.id / "summary.txt"),
            str(worktree_root / "codex_execution.json"),
        ),
    )
    monkeypatch.setattr(runner, "capture_diff", lambda worktree_arg, task_id: str(worktree_root / "changes.diff"))
    monkeypatch.setattr(
        runner,
        "validate_run",
        lambda *args: [ValidationCheck(name="tests", passed=False, details="failed")],
    )
    monkeypatch.setattr(
        runner, "classify_result", lambda *args: EngineeringResultClassification.VALIDATION_FAILED
    )
    monkeypatch.setattr(runner, "build_summary", lambda *args: "Validation failed")
    monkeypatch.setattr(
        runner,
        "write_review_artifact",
        lambda **kwargs: str(isolated_repo_root / "state" / "artifacts" / task.id / "review_summary.json"),
    )

    result = runner.execute_task(task.id)
    saved_task = TaskStore().load(task.id)
    saved_run = TaskRunStore().load("run-task-validation-failed")

    assert result.status is TaskStatus.FAILED
    assert result.approval_id is None
    assert saved_task.status is TaskStatus.FAILED
    assert saved_run.status.value == "failed"
    assert saved_run.approval_id is None


def test_result_as_dict_serializes_enum_backed_status() -> None:
    payload = runner.result_as_dict(
        runner.TaskResult(
            task_id="task-123",
            status=TaskStatus.COMPLETED,
            summary="done",
        )
    )

    assert payload["status"] == "completed"

