from __future__ import annotations

import json
from pathlib import Path

import pytest

from engineering import repo_manager
from packages.db.repo_store import RepoStore
from packages.schemas.repo import RepoSyncStatus
from tests.python.factories.task_data import build_repo_config


def test_prepare_repo_raises_when_source_repo_is_missing(isolated_repo_root: Path) -> None:
    repo_config = build_repo_config(source_path=str(isolated_repo_root / "missing-source"))

    with pytest.raises(FileNotFoundError, match="Configured repo source path does not exist"):
        repo_manager.prepare_repo(repo_config)


def test_prepare_repo_writes_manifest_and_saves_ready_repo_record(
    isolated_repo_root: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source_root = isolated_repo_root / "products" / "source-repo"
    source_root.mkdir(parents=True)
    (source_root / "README.md").write_text("hello")
    repo_config = build_repo_config(
        repo_id="repo-123",
        source_path=str(source_root),
        managed_repo_name="managed-repo-123",
    )
    initialized_paths: list[Path] = []
    monkeypatch.setattr(
        repo_manager,
        "initialize_git_snapshot",
        lambda repo_path: initialized_paths.append(Path(repo_path)),
    )

    repo_record = repo_manager.prepare_repo(repo_config)

    managed_root = isolated_repo_root / "state" / "repos" / "managed-repo-123"
    manifest = json.loads((managed_root / "repo_manifest.json").read_text())
    saved = RepoStore().load("repo-123")

    assert (managed_root / "README.md").read_text() == "hello"
    assert initialized_paths == [managed_root]
    assert set(manifest) == {"name", "note", "prepared_at", "repo_id", "source_path"}
    assert manifest["repo_id"] == "repo-123"
    assert manifest["source_path"] == str(source_root)
    assert repo_record.managed_path == str(managed_root)
    assert repo_record.sync_status is RepoSyncStatus.READY
    assert saved.managed_path == str(managed_root)

