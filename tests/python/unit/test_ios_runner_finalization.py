from __future__ import annotations

from pathlib import Path

import pytest
from engineering import runner as engineering_runner
from ios import runner as ios_runner

from packages.db.task_run_store import TaskRunStore
from packages.db.task_store import TaskStore
from packages.db.worktree_store import WorktreeStore
from packages.schemas.task_packet import TaskStatus, WorkerLane
from packages.schemas.task_run import (
    EngineeringResultClassification,
    TaskRunStatus,
    ValidationCheck,
)
from packages.schemas.worktree import WorktreeStatus
from tests.python.factories.task_data import (
    build_repo_config,
    build_repo_record,
    build_task,
    build_worktree_metadata,
)
from tests.python.unit.test_runner import (
    build_execution_record,
    build_git_state,
    build_testing_policy,
)


@pytest.mark.parametrize("runner,lane", [(ios_runner, WorkerLane.IOS), (engineering_runner, WorkerLane.ENGINEERING)])
@pytest.mark.parametrize(
    ("classification", "validation_passed", "task_status", "run_status", "worktree_status"),
    [
        (
            EngineeringResultClassification.NO_CHANGE,
            True,
            TaskStatus.COMPLETED,
            TaskRunStatus.SUCCEEDED,
            WorktreeStatus.COMPLETED,
        ),
        (
            EngineeringResultClassification.SAFE_FOR_REVIEW,
            True,
            TaskStatus.COMPLETED,
            TaskRunStatus.SUCCEEDED,
            WorktreeStatus.COMPLETED,
        ),
        (
            EngineeringResultClassification.VALIDATION_FAILED,
            False,
            TaskStatus.FAILED,
            TaskRunStatus.FAILED,
            WorktreeStatus.FAILED,
        ),
        (
            EngineeringResultClassification.EXECUTION_FAILED,
            False,
            TaskStatus.FAILED,
            TaskRunStatus.FAILED,
            WorktreeStatus.FAILED,
        ),
    ],
)
def test_ios_runner_finalizes_worktree_with_terminal_task_status(
    isolated_repo_root: Path,
    monkeypatch: pytest.MonkeyPatch,
    classification: EngineeringResultClassification,
    validation_passed: bool,
    task_status: TaskStatus,
    run_status: TaskRunStatus,
    worktree_status: WorktreeStatus,
    runner,
    lane,
) -> None:
    task = build_task(task_id="task-123", repo_id="repo-ios", lane=lane)
    TaskStore().save(task)
    worktree_root = isolated_repo_root / "state" / "worktrees" / "repo-ios" / task.id
    worktree_root.mkdir(parents=True)
    worktree = build_worktree_metadata(str(worktree_root))
    repo_record = build_repo_record(repo_id="repo-ios")

    monkeypatch.setattr(runner, "load_repo_configs", lambda: {"repo-ios": build_repo_config(repo_id="repo-ios")})
    monkeypatch.setattr(runner, "prepare_repo", lambda _: repo_record)
    monkeypatch.setattr(runner, "prepare_worktree", lambda *_: worktree)
    monkeypatch.setattr(runner, "render_task_packet", lambda *_: str(worktree_root / "TASK_PACKET.md"))
    monkeypatch.setattr(
        runner,
        "capture_git_state",
        lambda *_: build_git_state(changed_files=[]),
    )
    monkeypatch.setattr(
        runner,
        "execute_codex",
        lambda *_: (
            str(worktree_root / "codex_last_message.md"),
            build_execution_record(),
            str(isolated_repo_root / "state/artifacts/ios/task-123/build_summary.json"),
            str(worktree_root / "codex_execution.json"),
        ),
    )
    monkeypatch.setattr(runner, "capture_diff", lambda *_: str(worktree_root / "changes.diff"))
    monkeypatch.setattr(
        runner,
        "validate_run",
        lambda *_: (
            [
                ValidationCheck(
                    name="tests",
                    passed=validation_passed,
                    details="ok" if validation_passed else "failed",
                    code=None if validation_passed else "ios_validation_failed",
                )
            ],
            build_testing_policy(),
            "tests passed" if validation_passed else "tests failed",
        ),
    )
    monkeypatch.setattr(runner, "classify_result", lambda *_: classification)
    monkeypatch.setattr(runner, "build_summary", lambda *_: "No changes required")
    monkeypatch.setattr(
        runner,
        "write_review_artifact",
        lambda **_: str(isolated_repo_root / "state/artifacts/ios/task-123/review_summary.json"),
    )

    result = runner.execute_task(task.id)
    saved_task = TaskStore().load(task.id)
    saved_run = TaskRunStore().load(f"run-{task.id}")
    saved_worktree = WorktreeStore().load(worktree.id)

    assert result.status is task_status
    assert saved_task.status is task_status
    assert saved_run.status is run_status
    assert saved_worktree.status is worktree_status
    assert saved_worktree.validated_at == saved_run.finished_at
