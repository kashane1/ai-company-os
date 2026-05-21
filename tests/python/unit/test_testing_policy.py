from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from packages.db.task_store import TaskStore
from packages.policies import testing
from packages.schemas.task_packet import TaskStatus, WorkerLane
from packages.schemas.testing import NoTestReasonCode, TestLane as LaneEnum, ValidationFailureCode
from tests.python.factories.task_data import build_task


def metadata(text: str) -> testing.TestingMetadata:
    parsed = testing.parse_testing_metadata(f"## Testing\n\n{text}\n")
    assert parsed is not None
    return parsed


def test_evaluate_testing_policy_passes_for_lane_matching_python_test_changes() -> None:
    changes = testing.parse_name_status_lines(
        [
            "M\tapps/api/platform.py",
            "M\ttests/python/unit/test_platform.py",
        ]
    )

    result = testing.evaluate_testing_policy(
        lane=LaneEnum.PYTHON,
        changes=changes,
        testing_metadata=metadata("- Added platform task tests"),
    )

    assert result.tests_required is True
    assert result.relevant_tests_changed is True
    assert result.failure_code is None


def test_evaluate_testing_policy_passes_for_lane_matching_ios_test_changes() -> None:
    changes = testing.parse_name_status_lines(
        [
            "M\tproducts/catchbook-ios/Sources/Features/Trips/TripsView.swift",
            "A\tproducts/catchbook-ios/Tests/Features/Trips/TripEditingLogicTests.swift",
        ]
    )

    result = testing.evaluate_testing_policy(
        lane=LaneEnum.IOS,
        changes=changes,
        testing_metadata=metadata("- Added TripEditingLogic tests"),
    )

    assert result.tests_required is True
    assert result.relevant_tests_changed is True
    assert result.failure_code is None


def test_evaluate_testing_policy_requires_lane_matching_tests_for_mixed_changes() -> None:
    changes = testing.parse_name_status_lines(
        [
            "M\tapps/api/platform.py",
            "M\tproducts/catchbook-ios/Sources/Features/Trips/TripsView.swift",
            "M\ttests/python/unit/test_platform.py",
        ]
    )

    python_result = testing.evaluate_testing_policy(
        lane=LaneEnum.PYTHON,
        changes=changes,
        testing_metadata=metadata("- Added Python coverage only"),
    )
    ios_result = testing.evaluate_testing_policy(
        lane=LaneEnum.IOS,
        changes=changes,
        testing_metadata=metadata("- Added Python coverage only"),
    )

    assert python_result.failure_code is None
    assert ios_result.failure_code is ValidationFailureCode.MISSING_TESTS_FOR_LOGIC_CHANGE


def test_evaluate_testing_policy_accepts_docs_only_when_no_logic_files_changed() -> None:
    changes = testing.parse_name_status_lines(["M\tREADME.md"])

    result = testing.evaluate_testing_policy(
        lane=LaneEnum.PYTHON,
        changes=changes,
        testing_metadata=metadata("no_test_reason_code=docs_only\n- docs only"),
    )

    assert result.tests_required is False
    assert result.test_lane is LaneEnum.NONE
    assert result.no_test_reason_code is NoTestReasonCode.DOCS_ONLY
    assert result.failure_code is None


def test_evaluate_testing_policy_requires_testing_metadata_for_logic_changes() -> None:
    changes = testing.parse_name_status_lines(["M\tapps/api/platform.py"])

    result = testing.evaluate_testing_policy(
        lane=LaneEnum.PYTHON,
        changes=changes,
        testing_metadata=None,
    )

    assert result.failure_code is ValidationFailureCode.MISSING_TESTING_METADATA


def test_evaluate_testing_policy_rejects_invalid_reason_codes() -> None:
    changes = testing.parse_name_status_lines(["M\tapps/api/platform.py"])

    result = testing.evaluate_testing_policy(
        lane=LaneEnum.PYTHON,
        changes=changes,
        testing_metadata=metadata("no_test_reason_code=not_real"),
    )

    assert result.failure_code is ValidationFailureCode.INVALID_NO_TEST_REASON_CODE


def test_evaluate_testing_policy_fails_logic_changes_without_matching_tests() -> None:
    changes = testing.parse_name_status_lines(["M\tapps/api/platform.py"])

    result = testing.evaluate_testing_policy(
        lane=LaneEnum.PYTHON,
        changes=changes,
        testing_metadata=metadata("- Ran existing tests only"),
    )

    assert result.failure_code is ValidationFailureCode.MISSING_TESTS_FOR_LOGIC_CHANGE


def test_approved_followup_test_task_requires_open_lane_matched_task(
    isolated_repo_root: Path,
) -> None:
    current_task = build_task(task_id="task-123", repo_id="repo-123", lane=WorkerLane.ENGINEERING)
    followup_task = build_task(
        task_id="task-tests",
        repo_id="repo-123",
        lane=WorkerLane.ENGINEERING,
        task_type="followup_tests",
        status=TaskStatus.PENDING,
    )
    store = TaskStore()
    store.save(current_task)
    store.save(followup_task)
    changes = testing.parse_name_status_lines(["M\tapps/api/platform.py"])

    result = testing.evaluate_testing_policy(
        lane=LaneEnum.PYTHON,
        changes=changes,
        testing_metadata=metadata(
            "no_test_reason_code=approved_followup_test_task\nfollowup_task_id=task-tests"
        ),
        current_task=current_task,
        task_store=store,
    )

    assert result.failure_code is None
    assert result.followup_task_id == "task-tests"


def test_approved_followup_test_task_rejects_closed_or_wrong_lane_tasks(
    isolated_repo_root: Path,
) -> None:
    current_task = build_task(task_id="task-123", repo_id="repo-123", lane=WorkerLane.ENGINEERING)
    closed_followup = build_task(
        task_id="task-tests",
        repo_id="repo-123",
        lane=WorkerLane.IOS,
        task_type="followup_tests",
        status=TaskStatus.COMPLETED,
        summary="Future iOS tests",
    )
    store = TaskStore()
    store.save(current_task)
    store.save(closed_followup)
    changes = testing.parse_name_status_lines(["M\tapps/api/platform.py"])

    result = testing.evaluate_testing_policy(
        lane=LaneEnum.PYTHON,
        changes=changes,
        testing_metadata=metadata(
            "no_test_reason_code=approved_followup_test_task\nfollowup_task_id=task-tests"
        ),
        current_task=current_task,
        task_store=store,
    )

    assert result.failure_code is ValidationFailureCode.INVALID_FOLLOWUP_TEST_TASK_REFERENCE


def test_check_tests_with_code_script_handles_explicit_changed_file_lists(
    tmp_path: Path,
) -> None:
    changed_files = tmp_path / "changed.txt"
    changed_files.write_text(
        "\n".join(
            [
                "M\tapps/api/platform.py",
                "M\tproducts/catchbook-ios/Sources/Features/Trips/TripsView.swift",
                "M\ttests/python/unit/test_platform.py",
            ]
        )
        + "\n"
    )
    metadata_path = tmp_path / "metadata.md"
    metadata_path.write_text("## Testing\n\n- Added Python tests only\n")

    completed = subprocess.run(
        [
            sys.executable,
            "scripts/ci/check_tests_with_code.py",
            "--changed-files",
            str(changed_files),
            "--metadata-file",
            str(metadata_path),
        ],
        cwd=Path(__file__).resolve().parents[3],
        text=True,
        capture_output=True,
    )

    assert completed.returncode == 1
    assert "ios: missing_tests_for_logic_change" in completed.stdout


def test_check_tests_with_code_script_passes_docs_only_changes(tmp_path: Path) -> None:
    changed_files = tmp_path / "changed.txt"
    changed_files.write_text("M\tREADME.md\n")
    metadata_path = tmp_path / "metadata.md"
    metadata_path.write_text("")

    completed = subprocess.run(
        [
            sys.executable,
            "scripts/ci/check_tests_with_code.py",
            "--changed-files",
            str(changed_files),
            "--metadata-file",
            str(metadata_path),
        ],
        cwd=Path(__file__).resolve().parents[3],
        text=True,
        capture_output=True,
    )

    assert completed.returncode == 0
    assert "No logic-bearing Python or iOS source changes detected." in completed.stdout


def test_logic_paths_for_lane_ignores_apps_readme_markdown() -> None:
    """Regression (PR #54): docs-only README files under apps/ are not
    Python logic-bearing changes. Before the fix, every non-test file
    under apps/ or packages/ was misclassified as Python logic."""
    changes = testing.parse_name_status_lines(
        [
            "A\tapps/api/README.md",
            "A\tapps/worker-ios/README.md",
        ]
    )

    assert testing.logic_paths_for_lane(changes, LaneEnum.PYTHON) == []


def test_logic_paths_for_lane_counts_real_python_under_apps() -> None:
    """An actual .py file under apps/ is still logic-bearing for the Python lane."""
    changes = testing.parse_name_status_lines(["M\tapps/api/platform.py"])

    assert testing.logic_paths_for_lane(changes, LaneEnum.PYTHON) == ["apps/api/platform.py"]


def test_logic_paths_for_lane_counts_real_python_under_packages() -> None:
    """An actual .py file under packages/ is still logic-bearing for the Python lane."""
    changes = testing.parse_name_status_lines(["M\tpackages/policies/testing.py"])

    assert testing.logic_paths_for_lane(changes, LaneEnum.PYTHON) == [
        "packages/policies/testing.py"
    ]


def test_check_tests_with_code_script_passes_apps_readme_only_changes(
    tmp_path: Path,
) -> None:
    """End-to-end regression (PR #54): a docs-only PR touching only
    apps/**/README.md exits 0 instead of failing missing_tests_for_logic_change."""
    changed_files = tmp_path / "changed.txt"
    changed_files.write_text(
        "\n".join(
            [
                "M\tapps/README.md",
                "A\tapps/api/README.md",
                "A\tapps/worker-ios/README.md",
            ]
        )
        + "\n"
    )
    metadata_path = tmp_path / "metadata.md"
    metadata_path.write_text("## Testing\n\n- docs-only worker READMEs\n")

    completed = subprocess.run(
        [
            sys.executable,
            "scripts/ci/check_tests_with_code.py",
            "--changed-files",
            str(changed_files),
            "--metadata-file",
            str(metadata_path),
        ],
        cwd=Path(__file__).resolve().parents[3],
        text=True,
        capture_output=True,
    )

    assert completed.returncode == 0
    assert "No logic-bearing Python or iOS source changes detected." in completed.stdout
