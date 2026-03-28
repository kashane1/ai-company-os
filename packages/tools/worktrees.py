from pathlib import Path

from packages.config.settings import load_runtime_paths


def task_worktree_path(task_id: str, repo_name: str) -> Path:
    paths = load_runtime_paths()
    return paths.worktrees_root / repo_name / task_id
