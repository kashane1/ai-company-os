import json
from datetime import UTC, datetime
from pathlib import Path

from engineering.file_sync import clear_directory, sync_tree
from engineering.git_state import initialize_git_snapshot
from packages.config.settings import ensure_runtime_directories
from packages.db.repo_store import RepoStore
from packages.schemas.repo import RepoConfig, RepoRecord, RepoSyncStatus


def prepare_repo(repo_config: RepoConfig) -> RepoRecord:
    paths = ensure_runtime_directories()
    source_path = Path(repo_config.source_path)
    if not source_path.exists():
        raise FileNotFoundError(f"Configured repo source path does not exist: {source_path}")

    managed_path = paths.repos_root / repo_config.managed_repo_name
    managed_path.mkdir(parents=True, exist_ok=True)
    clear_directory(managed_path)
    sync_tree(source_path, managed_path)
    initialize_git_snapshot(managed_path)

    manifest = {
        "repo_id": repo_config.id,
        "name": repo_config.name,
        "source_path": str(source_path),
        "prepared_at": datetime.now(UTC).isoformat(),
        "note": "Managed repo snapshot for the engineering lane.",
    }
    with (managed_path / "repo_manifest.json").open("w") as handle:
        json.dump(manifest, handle, indent=2, sort_keys=True)

    repo_record = RepoRecord(
        id=repo_config.id,
        name=repo_config.name,
        source_path=str(source_path),
        managed_path=str(managed_path),
        default_branch=repo_config.default_branch,
        sync_status=RepoSyncStatus.READY,
        last_synced_at=datetime.now(UTC).isoformat(),
    )
    RepoStore().save(repo_record)
    return repo_record
