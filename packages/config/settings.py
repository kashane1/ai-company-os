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
    products_root: Path
    releases_root: Path
    repo_records_root: Path
    worktree_records_root: Path
    build_candidates_root: Path
    metadata_drafts_root: Path
    screenshot_sets_root: Path
    release_records_root: Path
    engineering_artifacts_root: Path
    ios_artifacts_root: Path
    engineering_logs_root: Path
    ios_logs_root: Path


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
        products_root=platform_state_root / "products",
        releases_root=platform_state_root / "releases",
        repo_records_root=platform_state_root / "repos",
        worktree_records_root=platform_state_root / "worktrees",
        build_candidates_root=platform_state_root / "releases" / "build_candidates",
        metadata_drafts_root=platform_state_root / "releases" / "metadata_drafts",
        screenshot_sets_root=platform_state_root / "releases" / "screenshot_sets",
        release_records_root=platform_state_root / "releases" / "release_records",
        engineering_artifacts_root=artifacts_root / "engineering",
        ios_artifacts_root=artifacts_root / "ios",
        engineering_logs_root=logs_root / "engineering",
        ios_logs_root=logs_root / "ios",
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
        paths.products_root,
        paths.releases_root,
        paths.repo_records_root,
        paths.worktree_records_root,
        paths.build_candidates_root,
        paths.metadata_drafts_root,
        paths.screenshot_sets_root,
        paths.release_records_root,
        paths.engineering_artifacts_root,
        paths.ios_artifacts_root,
        paths.engineering_logs_root,
        paths.ios_logs_root,
    ]
    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)
    return paths
