from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from engineering import worktree_manager
from packages.db.worktree_store import WorktreeStore
from packages.tools.worktrees import task_worktree_path
from tests.python.factories.task_data import build_repo_record, build_task


def test_prepare_worktree_derives_path_and_writes_managed_files(
    isolated_repo_root: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    task = build_task(task_id="task-prepare", repo_id="repo-123")
    repo = build_repo_record(
        repo_id="repo-123",
        source_path=str(isolated_repo_root / "products" / "source"),
        managed_path=str(isolated_repo_root / "state" / "repos" / "managed-repo"),
    )

    def fake_clone(command: list[str], **kwargs) -> subprocess.CompletedProcess[str]:
        destination = Path(command[-1])
        (destination / ".git" / "info").mkdir(parents=True, exist_ok=True)
        return subprocess.CompletedProcess(args=command, returncode=0, stdout="", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_clone)

    worktree = worktree_manager.prepare_worktree(task, repo)

    expected_root = task_worktree_path(task.id, repo.id)
    exclude_lines = (expected_root / ".git" / "info" / "exclude").read_text().splitlines()
    context_lines = (expected_root / "workspace_context.txt").read_text().splitlines()
    saved = WorktreeStore().load(worktree.id)

    assert worktree.root_path == str(expected_root)
    assert exclude_lines == [
        "codex_execution.json",
        "codex_last_message.md",
        "TASK_PACKET.md",
        "workspace_context.txt",
    ]
    assert context_lines == [
        f"task_id={task.id}",
        f"repo_id={repo.id}",
        f"source_path={repo.source_path}",
        f"managed_path={repo.managed_path}",
        "note=This is a managed isolated workspace for the engineering task flow.",
    ]
    assert saved.status.value == "prepared"
    assert saved.validated_at == ""
