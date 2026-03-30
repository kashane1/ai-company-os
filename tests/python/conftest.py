from __future__ import annotations

from pathlib import Path
import shutil
import sys

import pytest

from packages.config.settings import TEST_REPO_ROOT_ENV_VAR, ensure_runtime_directories


@pytest.fixture
def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


@pytest.fixture(autouse=True)
def configure_worker_paths(repo_root: Path) -> None:
    engineering_app = repo_root / "apps" / "worker-engineering"
    ios_app = repo_root / "apps" / "worker-ios"
    for path in (engineering_app, ios_app):
        resolved = str(path)
        if resolved not in sys.path:
            sys.path.insert(0, resolved)


@pytest.fixture
def isolated_repo_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, repo_root: Path) -> Path:
    test_root = tmp_path / "isolated-repo"
    test_root.mkdir()

    shutil.copytree(repo_root / "infra", test_root / "infra")
    shutil.copytree(repo_root / "docs", test_root / "docs")
    (test_root / "products" / "fishing-logbook-ios").mkdir(parents=True)

    monkeypatch.setenv(TEST_REPO_ROOT_ENV_VAR, str(test_root))
    ensure_runtime_directories()
    return test_root
