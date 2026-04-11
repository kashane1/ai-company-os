"""Phase 0.2 — sanity tests for scripts/cleanup_agent_worktrees.sh."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT = REPO_ROOT / "scripts" / "cleanup_agent_worktrees.sh"


def _git(*args, cwd: Path) -> str:
    env = os.environ.copy()
    env.setdefault("GIT_AUTHOR_NAME", "test")
    env.setdefault("GIT_AUTHOR_EMAIL", "test@example.com")
    env.setdefault("GIT_COMMITTER_NAME", "test")
    env.setdefault("GIT_COMMITTER_EMAIL", "test@example.com")
    result = subprocess.run(
        ["git", *args], cwd=cwd, capture_output=True, text=True, env=env
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr)
    return result.stdout


def test_script_is_executable_and_syntactically_valid():
    assert SCRIPT.exists(), SCRIPT
    assert os.access(SCRIPT, os.X_OK)
    result = subprocess.run(
        ["bash", "-n", str(SCRIPT)], capture_output=True, text=True
    )
    assert result.returncode == 0, result.stderr


def test_script_refuses_when_index_lock_present(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    _git("init", "-q", cwd=repo)
    (repo / "README.md").write_text("hello\n")
    _git("add", "README.md", cwd=repo)
    _git("commit", "-q", "-m", "init", cwd=repo)
    (repo / ".git" / "index.lock").write_text("")

    # Copy the script into a scripts/ dir so $REPO_ROOT resolves.
    scripts_dir = repo / "scripts"
    scripts_dir.mkdir()
    target = scripts_dir / "cleanup_agent_worktrees.sh"
    target.write_bytes(SCRIPT.read_bytes())
    target.chmod(0o755)

    result = subprocess.run(
        ["bash", str(target)], capture_output=True, text=True
    )
    assert result.returncode == 10, (result.stdout, result.stderr)
    assert "index.lock" in result.stderr
