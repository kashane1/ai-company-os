"""Regression coverage for the employer-facing evaluator command."""

from __future__ import annotations

import json
import os
import shlex
import shutil
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]


def _evaluator_subprocess_env(**overrides: str) -> dict[str, str]:
    """Keep a nested evaluator run out of its parent's coverage session."""
    env = {
        key: value
        for key, value in os.environ.items()
        if not key.startswith("COV_CORE_") and key != "COVERAGE_PROCESS_START"
    }
    env.update(overrides)
    return env


def test_evaluator_subprocess_env_does_not_inherit_pytest_coverage(monkeypatch) -> None:
    monkeypatch.setenv("COV_CORE_DATAFILE", "/tmp/parent-coverage")
    monkeypatch.setenv("COV_CORE_BRANCH", "enabled")
    monkeypatch.setenv("COVERAGE_PROCESS_START", "/tmp/coverage-config")

    env = _evaluator_subprocess_env(PYTHON_BIN="python3")

    assert "COV_CORE_DATAFILE" not in env
    assert "COV_CORE_BRANCH" not in env
    assert "COVERAGE_PROCESS_START" not in env
    assert env["PYTHON_BIN"] == "python3"


def _evaluator_fixture(tmp_path: Path) -> Path:
    """Build an isolated, runnable evaluator view without rewriting docs."""
    root = tmp_path / "repo with spaces"
    root.mkdir()
    (root / "state").mkdir()
    shutil.copy2(REPO / "state/README.md", root / "state/README.md")
    shutil.copytree(REPO / "scripts", root / "scripts")
    # Only generated examples are mutable. Share the other read-only inputs
    # instead of copying the entire screenshot archive for every smoke check.
    (root / "docs").mkdir()
    for source in (REPO / "docs").iterdir():
        target = root / "docs" / source.name
        if source.name == "examples":
            shutil.copytree(source, target)
        else:
            target.symlink_to(source, target_is_directory=source.is_dir())
    for relative in (
        "packages",
        "apps",
        "products",
        "skills",
        "tests",
        ".github",
        "LICENSE",
        "README.md",
        "CONTRIBUTING.md",
        "REPO_MAP.md",
        "AGENTS.md",
        "CLAUDE.md",
        "infra",
        "uv.lock",
        "Makefile",
        "start",
        "repo-manifest.yaml",
        "SECURITY.md",
        "todos",
    ):
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.symlink_to(REPO / relative, target_is_directory=(REPO / relative).is_dir())
    shutil.copy2(REPO / "pyproject.toml", root / "pyproject.toml")
    return root


def test_evaluator_fast_check_runs_from_another_working_directory(tmp_path: Path) -> None:
    root = _evaluator_fixture(tmp_path)
    python_with_spaces = tmp_path / "python with spaces"
    # A new symlink can lose the interpreter's pyvenv.cfg association (notably
    # with uv-managed Python). A launcher preserves the selected environment.
    python_with_spaces.write_text(
        f'#!/bin/sh\nexec {shlex.quote(sys.executable)} "$@"\n', encoding="utf-8"
    )
    python_with_spaces.chmod(0o755)
    env = _evaluator_subprocess_env(PYTHON_BIN=str(python_with_spaces))

    result = subprocess.run(
        [str(root / "scripts" / "evaluator_check.sh"), "--with-tests"],
        cwd=tmp_path,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "Evaluator check passed." in result.stdout


def test_evaluator_rejects_stale_samples_before_regenerating_them(tmp_path: Path) -> None:
    root = _evaluator_fixture(tmp_path)
    sample = root / "docs" / "examples" / "sample-task-run.json"
    payload = json.loads(sample.read_text())
    payload["classification"] = "not-a-real-classification"
    sample.write_text(json.dumps(payload))

    result = subprocess.run(
        [str(root / "scripts" / "evaluator_check.sh")],
        cwd=tmp_path,
        env=_evaluator_subprocess_env(PYTHON_BIN=sys.executable),
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode != 0
    assert "sample-task-run.json does not match its schema" in result.stderr
    assert "==> Running zero-setup fixture walkthrough" not in result.stdout
    assert json.loads(sample.read_text())["classification"] == "not-a-real-classification"
