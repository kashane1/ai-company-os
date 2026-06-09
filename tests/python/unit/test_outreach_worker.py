from __future__ import annotations

import importlib.util
from pathlib import Path
import sys

from packages.schemas.task import Task
from packages.schemas.task_packet import TaskStatus, WorkerLane


def load_outreach_runner():
    module_path = (
        Path(__file__).resolve().parents[3]
        / "apps"
        / "worker-outreach"
        / "outreach"
        / "runner.py"
    )
    spec = importlib.util.spec_from_file_location("worker_outreach_runner_test", module_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _task(task_type: str) -> Task:
    return Task(
        id="task-1",
        repo_id="local",
        lane=WorkerLane.OUTREACH,
        title="Outreach task",
        summary="Run outreach operation",
        task_type=task_type,
    )


def test_outreach_worker_fails_closed_on_send_task_type() -> None:
    runner = load_outreach_runner()

    result = runner.execute_task(_task("OUTREACH_SEND_EMAIL"))

    assert result.status == TaskStatus.FAILED
    assert "manual-gated" in result.summary
    assert "outreach_send_forbidden" in result.failure_codes


def test_outreach_worker_accepts_refresh_task_type() -> None:
    runner = load_outreach_runner()

    result = runner.execute_task(_task("OUTREACH_LEDGER_REFRESH"))

    assert result.status == TaskStatus.COMPLETED
    assert "client-status" in result.summary
