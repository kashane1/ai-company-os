import subprocess

import pytest

from engineering import git_state


def completed(stdout: str) -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(args=["git"], returncode=0, stdout=stdout, stderr="")


def test_capture_git_state_returns_empty_snapshot_when_git_is_clean(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        git_state,
        "run_git_command",
        lambda repo_path, *args: completed("" if args[0] == "status" else ""),
    )

    snapshot = git_state.capture_git_state("/tmp/repo")

    assert snapshot.status_lines == []
    assert snapshot.changed_files == []
    assert snapshot.diff_summary == ""


def test_capture_git_state_preserves_modified_file_paths(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_run_git_command(repo_path: str, *args: str) -> subprocess.CompletedProcess[str]:
        if args[0] == "status":
            return completed("M  src/app.py\nA  docs/readme.md\n")
        return completed(" src/app.py | 2 ++\n docs/readme.md | 1 +\n")

    monkeypatch.setattr(git_state, "run_git_command", fake_run_git_command)

    snapshot = git_state.capture_git_state("/tmp/repo")

    assert snapshot.status_lines == ["M  src/app.py", "A  docs/readme.md"]
    assert snapshot.changed_files == ["src/app.py", "docs/readme.md"]
    assert snapshot.diff_summary == "src/app.py | 2 ++\n docs/readme.md | 1 +"


def test_capture_git_state_preserves_git_rename_path_output(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_run_git_command(repo_path: str, *args: str) -> subprocess.CompletedProcess[str]:
        if args[0] == "status":
            return completed("R  old/path.py -> new/path.py\n")
        return completed(" old/path.py => new/path.py | 0\n")

    monkeypatch.setattr(git_state, "run_git_command", fake_run_git_command)

    snapshot = git_state.capture_git_state("/tmp/repo")

    assert snapshot.status_lines == ["R  old/path.py -> new/path.py"]
    assert snapshot.changed_files == ["old/path.py -> new/path.py"]
    assert snapshot.diff_summary == "old/path.py => new/path.py | 0"

