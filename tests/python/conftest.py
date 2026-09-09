from __future__ import annotations

import os
import shutil
import stat
import sys
import tempfile
from pathlib import Path

import pytest

from packages.config.settings import (
    DATABASE_URL_ENV_VAR,
    QUEUE_BACKEND_ENV_VAR,
    REDIS_URL_ENV_VAR,
    TEST_REPO_ROOT_ENV_VAR,
    ensure_runtime_directories,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
ENGINEERING_APP = REPO_ROOT / "apps" / "worker-engineering"
IOS_APP = REPO_ROOT / "apps" / "worker-ios"
for path in (ENGINEERING_APP, IOS_APP):
    resolved = str(path)
    if resolved not in sys.path:
        sys.path.insert(0, resolved)


@pytest.fixture
def repo_root() -> Path:
    return REPO_ROOT


def pytest_configure(config: pytest.Config) -> None:
    session_root = Path(tempfile.mkdtemp(prefix="ai-company-os-pytest-"))
    config._ai_company_os_session_root = session_root  # type: ignore[attr-defined]
    os.environ[TEST_REPO_ROOT_ENV_VAR] = str(session_root)
    os.environ.pop(DATABASE_URL_ENV_VAR, None)
    os.environ[QUEUE_BACKEND_ENV_VAR] = "database"
    os.environ.pop(REDIS_URL_ENV_VAR, None)
    ensure_runtime_directories()


def pytest_unconfigure(config: pytest.Config) -> None:
    session_root = getattr(config, "_ai_company_os_session_root", None)
    if session_root is not None:
        shutil.rmtree(session_root, ignore_errors=True)


def _state_snapshot() -> dict[str, tuple[int, int]]:
    """Capture checkout-state metadata without descending into nested repositories."""
    state_root = REPO_ROOT / "state"
    snapshot: dict[str, tuple[int, int]] = {}
    for current, directories, filenames in os.walk(state_root):
        current_path = Path(current)
        if current_path == state_root:
            directories[:] = [name for name in directories if name not in {"repos", "worktrees"}]
        for filename in filenames:
            path = current_path / filename
            metadata = path.lstat()
            if stat.S_ISREG(metadata.st_mode):
                snapshot[str(path.relative_to(state_root))] = (
                    metadata.st_size,
                    metadata.st_mtime_ns,
                )
    return snapshot


@pytest.fixture(scope="session", autouse=True)
def preserve_operator_runtime_state() -> None:
    """Fail if a test writes any file below the checkout's operator state."""
    before = _state_snapshot()
    yield
    assert _state_snapshot() == before, "tests modified checkout state/ files"


@pytest.fixture(autouse=True)
def isolated_runtime_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Route every test's default runtime writes to its own temporary root.

    A test may deliberately override one of these settings with ``monkeypatch``
    after this fixture runs. Child processes inherit the same environment.
    """
    runtime_root = tmp_path / "runtime-root"
    monkeypatch.setenv(TEST_REPO_ROOT_ENV_VAR, str(runtime_root))
    monkeypatch.delenv(DATABASE_URL_ENV_VAR, raising=False)
    monkeypatch.setenv(QUEUE_BACKEND_ENV_VAR, "database")
    monkeypatch.delenv(REDIS_URL_ENV_VAR, raising=False)
    ensure_runtime_directories()
    return runtime_root


@pytest.fixture(autouse=True)
def configure_worker_paths(repo_root: Path) -> None:
    for path in (ENGINEERING_APP, IOS_APP):
        resolved = str(path)
        if resolved not in sys.path:
            sys.path.insert(0, resolved)


@pytest.fixture
def isolated_repo_root(isolated_runtime_root: Path, repo_root: Path) -> Path:
    """Materialize only immutable fixture inputs needed by legacy callers.

    Runtime state is already isolated by ``isolated_runtime_root``. Copying the
    whole docs tree here made every opt-in caller duplicate roughly 244 MiB.
    """
    test_root = isolated_runtime_root
    shutil.copytree(repo_root / "infra", test_root / "infra")
    shutil.copytree(
        repo_root / "docs" / "products" / "catchbook",
        test_root / "docs" / "products" / "catchbook",
    )
    checklist_path = test_root / "docs" / "products" / "catchbook" / "submission-checklist.md"
    if checklist_path.exists():
        checklist_path.unlink()
    (test_root / "products" / "catchbook-ios").mkdir(parents=True)
    return test_root
