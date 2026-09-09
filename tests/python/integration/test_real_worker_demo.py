from __future__ import annotations

import json
import os
import subprocess
import sys

import pytest


@pytest.mark.parametrize("failure", [False, True])
def test_real_worker_demo_produces_inspectable_validated_work(tmp_path, repo_root, failure):
    output = tmp_path / "actual worker output"
    operator = tmp_path / "operator"
    operator.mkdir()
    sentinel = operator / "private-ledger.json"
    sentinel.write_text("preserve this local data")
    env = dict(os.environ, AI_COMPANY_OS_REPO_ROOT=str(operator))
    command = [sys.executable, str(repo_root / "scripts/worker_demo.py"), "--output", str(output)]
    if failure:
        command.append("--exercise-failure")
    result = subprocess.run(command, env=env, cwd=tmp_path, capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr
    report = json.loads((output / "execution-report.json").read_text())
    assert report["task"]["status"] == "completed"
    assert report["goal"]["status"] == "completed"
    assert report["validation"]["verdict"] == "ok"
    assert report["network_and_subprocess_calls_blocked"] is True
    assert report["external_model_invoked"] is False
    assert [event["event_type"] for event in report["events"]][-1] == "task_completed"
    ledger = json.loads((output / "state/prospects/outreach-lane/client-status.json").read_text())
    assert len(ledger["rows"]) == 1
    assert ledger["rows"][0]["business_name"] == "Example Bicycle Workshop (synthetic)"
    if failure:
        assert report["failed_attempt"]["task"]["status"] == "failed"
        assert report["failed_attempt"]["goal"]["status"] == "failed"
        assert report["failed_attempt"]["task"]["id"] != report["task"]["id"]
    assert sentinel.read_text() == "preserve this local data"


def test_worker_demo_refuses_to_overwrite_an_existing_directory(tmp_path, repo_root):
    result = subprocess.run(
        [sys.executable, str(repo_root / "scripts/worker_demo.py"), "--output", str(tmp_path)],
        capture_output=True, text=True,
    )
    assert result.returncode != 0
    assert "output already exists" in result.stderr
    assert not (tmp_path / "execution-report.json").exists()
