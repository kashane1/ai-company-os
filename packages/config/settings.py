from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class RuntimePaths:
    repo_root: Path
    state_root: Path
    repos_root: Path
    worktrees_root: Path
    artifacts_root: Path
    checkpoints_root: Path
    logs_root: Path
    cache_root: Path
    platform_state_root: Path
    tasks_root: Path
    task_runs_root: Path
    approvals_root: Path
    repo_records_root: Path
    worktree_records_root: Path
    engineering_artifacts_root: Path
    engineering_logs_root: Path


def load_runtime_paths(repo_root: Path | None = None) -> RuntimePaths:
    root = repo_root or Path(__file__).resolve().parents[2]
    state_root = root / "state"
    checkpoints_root = state_root / "checkpoints"
    platform_state_root = checkpoints_root / "platform"
    artifacts_root = state_root / "artifacts"
    logs_root = state_root / "logs"
    return RuntimePaths(
        repo_root=root,
        state_root=state_root,
        repos_root=state_root / "repos",
        worktrees_root=state_root / "worktrees",
        artifacts_root=artifacts_root,
        checkpoints_root=checkpoints_root,
        logs_root=logs_root,
        cache_root=state_root / "cache",
        platform_state_root=platform_state_root,
        tasks_root=platform_state_root / "tasks",
        task_runs_root=platform_state_root / "task_runs",
        approvals_root=platform_state_root / "approvals",
        repo_records_root=platform_state_root / "repos",
        worktree_records_root=platform_state_root / "worktrees",
        engineering_artifacts_root=artifacts_root / "engineering",
        engineering_logs_root=logs_root / "engineering",
    )


def ensure_runtime_directories(repo_root: Path | None = None) -> RuntimePaths:
    paths = load_runtime_paths(repo_root)
    directories = [
        paths.repos_root,
        paths.worktrees_root,
        paths.artifacts_root,
        paths.checkpoints_root,
        paths.logs_root,
        paths.cache_root,
        paths.platform_state_root,
        paths.tasks_root,
        paths.task_runs_root,
        paths.approvals_root,
        paths.repo_records_root,
        paths.worktree_records_root,
        paths.engineering_artifacts_root,
        paths.engineering_logs_root,
    ]
    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)
    return paths
