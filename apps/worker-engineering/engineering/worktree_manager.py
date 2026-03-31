import subprocess
from datetime import UTC, datetime
from pathlib import Path

from engineering.file_sync import clear_directory
from packages.db.worktree_store import WorktreeStore
from packages.schemas.repo import RepoRecord
from packages.schemas.task import Task
from packages.schemas.worktree import WorktreeMetadata, WorktreeStatus
from packages.tools.worktrees import task_worktree_path


def prepare_worktree(task: Task, repo: RepoRecord) -> WorktreeMetadata:
    root_path = task_worktree_path(task.id, repo.id)
    root_path.mkdir(parents=True, exist_ok=True)
    clear_directory(root_path)
    subprocess.run(
        ["git", "clone", "--quiet", repo.managed_path, str(root_path)],
        text=True,
        capture_output=True,
        check=True,
    )

    exclude_path = root_path / ".git" / "info" / "exclude"
    exclude_path.parent.mkdir(parents=True, exist_ok=True)
    exclude_path.write_text(
        "\n".join(
            [
                "codex_execution.json",
                "codex_last_message.md",
                "TASK_PACKET.md",
                "workspace_context.txt",
            ]
        )
        + "\n"
    )

    context_lines = [
        f"task_id={task.id}",
        f"repo_id={repo.id}",
        f"source_path={repo.source_path}",
        f"managed_path={repo.managed_path}",
        "note=This is a managed isolated workspace for the engineering task flow.",
    ]
    (root_path / "workspace_context.txt").write_text("\n".join(context_lines) + "\n")

    worktree = WorktreeMetadata(
        id=f"worktree-{task.id}",
        task_id=task.id,
        repo_id=repo.id,
        root_path=str(root_path),
        status=WorktreeStatus.PREPARED,
        created_at=datetime.now(UTC).isoformat(),
    )
    WorktreeStore().save(worktree)
    return worktree
