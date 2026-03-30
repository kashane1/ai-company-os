from pathlib import Path
from types import SimpleNamespace

from engineering import validator
from packages.schemas.testing import ValidationFailureCode
from tests.python.factories import build_worktree_metadata
from tests.python.factories.task_data import build_task


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
    packet_path = tmp_path / "packet.md"
    worktree_path = tmp_path / "worktree"
    execution_result_path = tmp_path / "execution.md"
    diff_path = tmp_path / "diff.patch"

    packet_path.write_text("# packet")
    worktree_path.mkdir()
    execution_result_path.write_text("## Testing\n\n- Added tests/python/unit/test_platform.py\n")
    diff_path.write_text("diff")

    checks, testing_policy, testing_summary = validator.validate_run(
        build_task(),
        str(packet_path),
        str(worktree_path),
        str(execution_result_path),
        exit_code=0,
        diff_path=str(diff_path),
        status_lines=["M  apps/api/platform.py", "M  tests/python/unit/test_platform.py"],
    )

    assert all(check.passed for check in checks)
    assert testing_policy.failure_code is None
    assert "Added tests/python/unit/test_platform.py" in testing_summary
    assert [check.name for check in checks] == [
        "worktree_exists",
        "packet_exists",
        "execution_result_exists",
        "codex_exit_code_zero",
        "diff_artifact_exists",
        "tests_with_code_policy",
    ]


def test_validate_run_reports_missing_tests_for_logic_change(tmp_path: Path) -> None:
    packet_path = tmp_path / "packet.md"
    worktree_path = tmp_path / "worktree"
    execution_result_path = tmp_path / "execution.md"
    diff_path = tmp_path / "diff.patch"

    packet_path.write_text("# packet")
    worktree_path.mkdir()
    execution_result_path.write_text("## Testing\n\n- Ran existing checks only\n")
    diff_path.write_text("diff")

    checks, testing_policy, _ = validator.validate_run(
        build_task(),
        str(packet_path),
        str(worktree_path),
        str(execution_result_path),
        exit_code=0,
        diff_path=str(diff_path),
        status_lines=["M  apps/api/platform.py"],
    )

    failed_check = next(check for check in checks if check.name == "tests_with_code_policy")

    assert failed_check.passed is False
    assert failed_check.code == ValidationFailureCode.MISSING_TESTS_FOR_LOGIC_CHANGE.value
    assert testing_policy.failure_code is ValidationFailureCode.MISSING_TESTS_FOR_LOGIC_CHANGE
