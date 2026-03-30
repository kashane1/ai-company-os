from pathlib import Path
from types import SimpleNamespace

from engineering import validator
from tests.python.factories import build_worktree_metadata


def test_capture_diff_writes_diff_artifact(
    isolated_repo_root: Path,
    monkeypatch,
    tmp_path: Path,
) -> None:
    worktree_root = tmp_path / "worktree"
    worktree_root.mkdir()
    worktree = build_worktree_metadata(str(worktree_root))

    monkeypatch.setattr(
        validator.subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(stdout="diff --git a/file b/file\n"),
    )

    diff_path = validator.capture_diff(worktree, "task-123")

    assert Path(diff_path).exists()
    assert Path(diff_path).read_text() == "diff --git a/file b/file\n"


def test_validate_run_reports_expected_checks(tmp_path: Path) -> None:
    packet_path = tmp_path / "packet.json"
    worktree_path = tmp_path / "worktree"
    execution_result_path = tmp_path / "execution.json"
    diff_path = tmp_path / "diff.patch"

    packet_path.write_text("{}")
    worktree_path.mkdir()
    execution_result_path.write_text("{}")
    diff_path.write_text("diff")

    checks = validator.validate_run(
        str(packet_path),
        str(worktree_path),
        str(execution_result_path),
        exit_code=0,
        diff_path=str(diff_path),
    )

    assert all(check.passed for check in checks)
    assert [check.name for check in checks] == [
        "worktree_exists",
        "packet_exists",
        "execution_result_exists",
        "codex_exit_code_zero",
        "diff_artifact_exists",
    ]
