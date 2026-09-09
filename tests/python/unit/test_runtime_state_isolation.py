from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
from pathlib import Path

from apps.api.control_plane import ControlPlaneService
from packages.agency.outreach_lane import refresh_client_status
from packages.config.settings import TEST_REPO_ROOT_ENV_VAR, load_dotenv, load_runtime_paths
from packages.db.task_store import TaskStore
from packages.schemas.task_packet import TaskStatus, WorkerLane

COLLECTION_RUNTIME_ROOT = load_runtime_paths().repo_root


def _load_outreach_worker_main(repo_root: Path):
    module_path = repo_root / "apps" / "worker-outreach" / "main.py"
    spec = importlib.util.spec_from_file_location("outreach_worker_main_isolation", module_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _conftest_module(pytestconfig, repo_root: Path):
    conftest_path = repo_root / "tests" / "python" / "conftest.py"
    return next(
        plugin
        for plugin in pytestconfig.pluginmanager.get_plugins()
        if Path(getattr(plugin, "__file__", "")) == conftest_path
    )


def test_pytest_defaults_runtime_state_to_a_temporary_root(repo_root) -> None:
    """No test may default runtime writes to the checked-out repository."""
    assert load_runtime_paths().repo_root != repo_root


def test_collection_uses_the_temporary_runtime_root(repo_root) -> None:
    assert COLLECTION_RUNTIME_ROOT != repo_root


def test_outreach_refresh_cannot_modify_the_checked_out_ledger(repo_root) -> None:
    """The real ledger materialization must stay under pytest's runtime root."""
    source_ledger = repo_root / "state" / "prospects" / "outreach-lane" / "client-status.md"
    before = source_ledger.read_bytes() if source_ledger.exists() else None

    refresh_client_status()

    runtime_ledger = (
        load_runtime_paths().state_root / "prospects" / "outreach-lane" / "client-status.md"
    )
    assert runtime_ledger.exists()
    assert runtime_ledger != source_ledger
    assert (source_ledger.read_bytes() if source_ledger.exists() else None) == before


def test_subprocess_inherits_the_temporary_runtime_root(repo_root) -> None:
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "from packages.config.settings import load_runtime_paths; "
            "print(load_runtime_paths().repo_root)",
        ],
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=True,
    )

    assert result.stdout.strip() == str(load_runtime_paths().repo_root)


def test_a_test_can_deliberately_override_the_runtime_root(monkeypatch, tmp_path: Path) -> None:
    explicit_root = tmp_path / "explicit-runtime-root"
    monkeypatch.setenv(TEST_REPO_ROOT_ENV_VAR, str(explicit_root))

    assert load_runtime_paths().repo_root == explicit_root


def test_load_dotenv_uses_the_configured_runtime_root(monkeypatch, tmp_path: Path) -> None:
    configured_root = tmp_path / "configured-root"
    configured_root.mkdir()
    dotenv_key = "AI_COMPANY_OS_TEST_DOTENV"
    (configured_root / ".env").write_text(f"{dotenv_key}=from-test-root\n", encoding="utf-8")
    monkeypatch.setenv(TEST_REPO_ROOT_ENV_VAR, str(configured_root))
    monkeypatch.delenv(dotenv_key, raising=False)

    load_dotenv()

    assert os.environ[dotenv_key] == "from-test-root"


def test_state_snapshot_skips_nested_repositories_and_worktrees(
    monkeypatch, pytestconfig, repo_root, tmp_path: Path
) -> None:
    state_root = tmp_path / "state"
    tracked = state_root / "prospects" / "ledger.md"
    tracked.parent.mkdir(parents=True)
    tracked.write_text("operator state", encoding="utf-8")
    for directory in (state_root / "repos" / "managed", state_root / "worktrees" / "task"):
        directory.mkdir(parents=True)
        (directory / "private.dat").write_text("do not inspect", encoding="utf-8")
    conftest_module = _conftest_module(pytestconfig, repo_root)
    monkeypatch.setattr(conftest_module, "REPO_ROOT", tmp_path)

    snapshot = conftest_module._state_snapshot()

    assert set(snapshot) == {"prospects/ledger.md"}


def test_claimed_outreach_ledger_refresh_cannot_modify_the_checked_out_ledger(repo_root) -> None:
    worker = _load_outreach_worker_main(repo_root)
    service = ControlPlaneService()
    goal = service.create_goal(title="Refresh outreach ledger", summary="Use the real worker path.")
    task = service.create_task_for_goal(
        goal_id=goal.id,
        repo_id="ai-company-os",
        lane=WorkerLane.OUTREACH,
        title="Refresh ledger",
        summary="Refresh the isolated outreach ledger.",
        task_type="OUTREACH_LEDGER_REFRESH",
    )
    source_ledger = repo_root / "state" / "prospects" / "outreach-lane" / "client-status.md"
    before = source_ledger.read_bytes() if source_ledger.exists() else None

    result = worker.execute_claimed_task(worker_id="worker-outreach-test", service=service)

    runtime_ledger = (
        load_runtime_paths().state_root / "prospects" / "outreach-lane" / "client-status.md"
    )
    assert result is not None
    assert result.task_id == task.id
    assert result.status is TaskStatus.COMPLETED
    assert TaskStore().load(task.id).status is TaskStatus.COMPLETED
    assert runtime_ledger.exists()
    assert runtime_ledger != source_ledger
    assert (source_ledger.read_bytes() if source_ledger.exists() else None) == before
