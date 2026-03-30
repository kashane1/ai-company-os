from pathlib import Path
import subprocess

from packages.config.settings import ensure_runtime_directories
from packages.policies.testing import evaluate_testing_policy, parse_git_status_lines, parse_testing_metadata
from packages.schemas.task import Task
from packages.schemas.testing import TestLane, TestingPolicyResult
from packages.schemas.task_run import ValidationCheck
from packages.schemas.worktree import WorktreeMetadata
from packages.tools.ios_tools.xcode import detect_project_reference, default_build_command


def capture_diff(worktree: WorktreeMetadata, task_id: str) -> str:
    paths = ensure_runtime_directories()
    diff_path = paths.ios_artifacts_root / task_id / "worktree.diff"
    completed = subprocess.run(
        [
            "git",
            "-C",
            worktree.root_path,
            "diff",
            "--stat",
            "--patch",
        ],
        text=True,
        capture_output=True,
    )
    diff_path.parent.mkdir(parents=True, exist_ok=True)
    diff_path.write_text(completed.stdout)
    return str(diff_path)


def build_validation_note(worktree_path: str) -> str | None:
    project_reference = detect_project_reference(Path(worktree_path))
    if not project_reference:
        return None
    return default_build_command(project_reference)


def validate_run(
    task: Task,
    packet_path: str,
    worktree_path: str,
    execution_result_path: str,
    exit_code: int,
    diff_path: str,
    status_lines: list[str],
) -> tuple[list[ValidationCheck], TestingPolicyResult, str]:
    execution_result = Path(execution_result_path)
    testing_metadata = (
        parse_testing_metadata(execution_result.read_text()) if execution_result.exists() else None
    )
    testing_policy = evaluate_testing_policy(
        lane=TestLane.IOS,
        changes=parse_git_status_lines(status_lines),
        testing_metadata=testing_metadata,
        current_task=task,
    )
    checks = [
        ValidationCheck(
            name="worktree_exists",
            passed=Path(worktree_path).exists(),
            details=f"Expected worktree at {worktree_path}.",
        ),
        ValidationCheck(
            name="packet_exists",
            passed=Path(packet_path).exists(),
            details=f"Expected task packet at {packet_path}.",
        ),
        ValidationCheck(
            name="execution_result_exists",
            passed=Path(execution_result_path).exists(),
            details=f"Expected execution result at {execution_result_path}.",
        ),
        ValidationCheck(
            name="codex_exit_code_zero",
            passed=exit_code == 0,
            details=f"Expected Codex exit code 0 but received {exit_code}.",
        ),
        ValidationCheck(
            name="diff_artifact_exists",
            passed=Path(diff_path).exists(),
            details=f"Expected diff artifact at {diff_path}.",
        ),
        ValidationCheck(
            name="tests_with_code_policy",
            passed=testing_policy.failure_code is None,
            details=testing_policy.details,
            code=testing_policy.failure_code.value if testing_policy.failure_code else None,
        ),
    ]
    xcode_note = build_validation_note(worktree_path)
    if xcode_note:
        checks.append(
            ValidationCheck(
                name="xcodebuild_command_available",
                passed=True,
                details=f"Future build validation command: {xcode_note}",
            )
        )
    testing_summary = testing_metadata.summary if testing_metadata else ""
    return checks, testing_policy, testing_summary
