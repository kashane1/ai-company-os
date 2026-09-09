from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
from engineering.git_state import capture_git_state

from packages.tools.git_changes import GitChangeCaptureError, capture_review_diff


def _git(repo: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        text=True,
        capture_output=True,
    )


def _git_stdout(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        text=True,
        capture_output=True,
    ).stdout


def _repository(tmp_path: Path) -> Path:
    repo = tmp_path / "review repository"
    repo.mkdir()
    _git(repo, "init", "--quiet")
    _git(repo, "config", "user.name", "Test User")
    _git(repo, "config", "user.email", "test@example.invalid")
    (repo / "partially_staged.py").write_text("first\nsecond\nthird\n")
    (repo / "deleted.py").write_text("delete me\n")
    (repo / "rename before.py").write_text("rename me\n")
    _git(repo, "add", ".")
    _git(repo, "commit", "--quiet", "-m", "baseline")
    return repo


def test_capture_review_diff_includes_every_uncommitted_change_kind(tmp_path: Path) -> None:
    repo = _repository(tmp_path)

    partially_staged = repo / "partially_staged.py"
    partially_staged.write_text("staged\nsecond\nthird\n")
    _git(repo, "add", "partially_staged.py")
    partially_staged.write_text("staged\nunstaged\nthird\n")
    (repo / "deleted.py").unlink()
    _git(repo, "mv", "rename before.py", "rename after.py")
    untracked = repo / "new directory" / "new file.py"
    untracked.parent.mkdir()
    untracked.write_text("new file\n")
    binary = repo / "new directory" / "image.bin"
    binary.write_bytes(b"\x00\xff\x00\x01")
    non_ascii = repo / "new directory" / "naïve.py"
    non_ascii.write_text("non ascii\n")

    index_before = _git_stdout(repo, "diff", "--cached", "--binary")
    diff = capture_review_diff(repo)
    index_after = _git_stdout(repo, "diff", "--cached", "--binary")
    snapshot = capture_git_state(str(repo))

    assert "+staged" in diff
    assert "+unstaged" in diff
    assert "deleted.py" in diff
    assert "rename before.py" in diff
    assert "rename after.py" in diff
    assert "new directory/new file.py" in diff
    assert "new directory/image.bin" in diff
    assert "new directory/naïve.py" in diff
    assert set(snapshot.changed_files) == {
        "deleted.py",
        "new directory/image.bin",
        "new directory/new file.py",
        "new directory/naïve.py",
        "partially_staged.py",
        "rename before.py -> rename after.py",
    }
    assert "?? new directory/new file.py" in snapshot.status_lines
    assert "?? new directory/naïve.py" in snapshot.status_lines
    assert "R \trename before.py\trename after.py" in snapshot.status_lines
    assert index_after == index_before


def test_capture_review_diff_fails_when_git_cannot_inspect_repository(tmp_path: Path) -> None:
    with pytest.raises(GitChangeCaptureError):
        capture_review_diff(tmp_path)
