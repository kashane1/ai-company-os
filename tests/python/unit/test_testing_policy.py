from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from packages.db.task_store import TaskStore
from packages.policies import testing
from packages.schemas.task_packet import TaskStatus, WorkerLane
from packages.schemas.testing import NoTestReasonCode, ValidationFailureCode
from packages.schemas.testing import TestLane as LaneEnum
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


def test_worker_web_lane_uses_web_testing_policy() -> None:
    assert testing.test_lane_for_worker_lane(WorkerLane.WEB) is LaneEnum.WEB


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


def test_approved_web_followup_test_task_must_match_product(
    isolated_repo_root: Path,
) -> None:
    current_task = build_task(
        task_id="task-web",
        repo_id="repo-123",
        lane=WorkerLane.WEB,
        product_id="better-business-web",
    )
    followup_task = build_task(
        task_id="task-web-tests",
        repo_id="repo-123",
        lane=WorkerLane.WEB,
        product_id="pokemon-tcg-search",
        task_type="followup_tests",
        status=TaskStatus.PENDING,
    )
    store = TaskStore()
    store.save(current_task)
    store.save(followup_task)
    changes = testing.parse_name_status_lines(
        ["M\tproducts/better-business-web/site/src/pages/index.astro"]
    )

    result = testing.evaluate_testing_policy(
        lane=LaneEnum.WEB,
        changes=changes,
        testing_metadata=metadata(
            "no_test_reason_code=approved_followup_test_task\n"
            "followup_task_id=task-web-tests"
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


def test_check_tests_with_code_script_checks_web_source_changes(tmp_path: Path) -> None:
    changed_files = tmp_path / "changed.txt"
    changed_files.write_text(
        "M\tproducts/better-business-web/site/src/pages/index.astro\n"
    )
    metadata_path = tmp_path / "metadata.md"
    metadata_path.write_text("## Testing\n\n- Ran existing checks\n")

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
    assert "web: missing_tests_for_logic_change" in completed.stdout


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
    assert "No mapped logic-bearing source changes detected." in completed.stdout


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


def test_logic_paths_for_lane_counts_python_and_shell_scripts() -> None:
    changes = testing.parse_name_status_lines(
        [
            "M\tscripts/control_plane_db.py",
            "M\tscripts/evaluator_check.sh",
            "M\tscripts/agency/README.md",
        ]
    )

    assert testing.logic_paths_for_lane(changes, LaneEnum.PYTHON) == [
        "scripts/control_plane_db.py",
        "scripts/evaluator_check.sh",
    ]


def test_ios_logic_and_tests_are_mapped_for_each_product() -> None:
    changes = testing.parse_name_status_lines(
        [
            "M\tproducts/after-plans-ios/Sources/App/AfterPlansApp.swift",
            "M\tproducts/catchbook-ios/Sources/App/CatchbookApp.swift",
            "M\tproducts/life-clock-ios/Sources/App/LifeClockApp.swift",
            "M\tproducts/life-clock-ios/Sources/Assets.xcassets/Contents.json",
        ]
    )

    assert testing.logic_paths_for_lane(changes, LaneEnum.IOS) == [
        "products/after-plans-ios/Sources/App/AfterPlansApp.swift",
        "products/catchbook-ios/Sources/App/CatchbookApp.swift",
        "products/life-clock-ios/Sources/App/LifeClockApp.swift",
    ]


def test_ios_test_from_another_product_does_not_satisfy_logic_change() -> None:
    changes = testing.parse_name_status_lines(
        [
            "M\tproducts/life-clock-ios/Sources/App/LifeClockApp.swift",
            "M\tproducts/catchbook-ios/Tests/App/AppTabTests.swift",
        ]
    )

    result = testing.evaluate_testing_policy(
        lane=LaneEnum.IOS,
        changes=changes,
        testing_metadata=metadata("- Updated Catchbook tests"),
    )

    assert result.relevant_tests_changed is False
    assert result.failure_code is ValidationFailureCode.MISSING_TESTS_FOR_LOGIC_CHANGE


def test_ios_test_in_affected_product_satisfies_logic_change() -> None:
    changes = testing.parse_name_status_lines(
        [
            "M\tproducts/life-clock-ios/Sources/App/LifeClockApp.swift",
            "M\tproducts/life-clock-ios/UITests/LifeClockUITests.swift",
        ]
    )

    result = testing.evaluate_testing_policy(
        lane=LaneEnum.IOS,
        changes=changes,
        testing_metadata=metadata("- Updated Life Clock UI coverage"),
    )

    assert result.relevant_tests_changed is True
    assert result.failure_code is None


def test_each_affected_ios_product_requires_its_own_test_change() -> None:
    changes = testing.parse_name_status_lines(
        [
            "M\tproducts/after-plans-ios/Sources/App/AfterPlansApp.swift",
            "M\tproducts/life-clock-ios/Sources/App/LifeClockApp.swift",
            "M\tproducts/after-plans-ios/Tests/App/ContinuationLoopTests.swift",
        ]
    )

    result = testing.evaluate_testing_policy(
        lane=LaneEnum.IOS,
        changes=changes,
        testing_metadata=metadata("- Updated After Plans tests"),
    )

    assert result.relevant_tests_changed is False
    assert result.failure_code is ValidationFailureCode.MISSING_TESTS_FOR_LOGIC_CHANGE
    assert "life_clock_ios" in result.details


def test_after_plans_source_accepts_after_plans_test() -> None:
    changes = testing.parse_name_status_lines(
        [
            "M\tproducts/after-plans-ios/Sources/App/AfterPlansApp.swift",
            "M\tproducts/after-plans-ios/Tests/App/ContinuationLoopTests.swift",
        ]
    )

    result = testing.evaluate_testing_policy(
        lane=LaneEnum.IOS,
        changes=changes,
        testing_metadata=metadata("- Updated After Plans tests"),
    )

    assert result.relevant_tests_changed is True
    assert result.failure_code is None


def test_web_logic_boundary_includes_source_and_excludes_generated_assets() -> None:
    changes = testing.parse_name_status_lines(
        [
            "M\tproducts/better-business-web/site/src/pages/index.astro",
            "M\tproducts/better-business-web/site/netlify/functions/website-review.mjs",
            "M\tproducts/better-business-web/portfolio/synapsex/src/App.tsx",
            "M\tproducts/better-business-web/site/src/styles/global.css",
            "M\tproducts/better-business-web/site/public/favicon.svg",
            "M\tproducts/better-business-web/portfolio/fish_tacos/dist/index.html",
        ]
    )

    assert testing.logic_paths_for_lane(changes, LaneEnum.WEB) == [
        "products/better-business-web/site/src/pages/index.astro",
        "products/better-business-web/site/netlify/functions/website-review.mjs",
        "products/better-business-web/portfolio/synapsex/src/App.tsx",
        "products/better-business-web/site/src/styles/global.css",
    ]


def test_python_test_does_not_satisfy_web_logic_change() -> None:
    changes = testing.parse_name_status_lines(
        [
            "M\tproducts/better-business-web/site/src/lib/pricing.mjs",
            "M\ttests/python/unit/test_platform.py",
        ]
    )

    result = testing.evaluate_testing_policy(
        lane=LaneEnum.WEB,
        changes=changes,
        testing_metadata=metadata("- Updated platform tests"),
    )

    assert result.relevant_tests_changed is False
    assert result.failure_code is ValidationFailureCode.MISSING_TESTS_FOR_LOGIC_CHANGE


def test_web_test_in_product_test_area_satisfies_web_logic_change() -> None:
    changes = testing.parse_name_status_lines(
        [
            "M\tproducts/better-business-web/site/src/lib/pricing.mjs",
            "A\tproducts/better-business-web/site/tests/pricing.test.mjs",
        ]
    )

    result = testing.evaluate_testing_policy(
        lane=LaneEnum.WEB,
        changes=changes,
        testing_metadata=metadata("- Added pricing tests"),
    )

    assert result.relevant_tests_changed is True
    assert result.failure_code is None


def test_web_test_from_another_product_does_not_satisfy_logic_change() -> None:
    changes = testing.parse_name_status_lines(
        [
            "M\tproducts/pokemon-tcg-search/web/app.js",
            "A\tproducts/better-business-web/site/tests/app.test.mjs",
        ]
    )

    result = testing.evaluate_testing_policy(
        lane=LaneEnum.WEB,
        changes=changes,
        testing_metadata=metadata("- Added Better Business Web tests"),
    )

    assert result.relevant_tests_changed is False
    assert result.failure_code is ValidationFailureCode.MISSING_TESTS_FOR_LOGIC_CHANGE
    assert "pokemon_tcg_web" in result.details


def test_pokemon_web_source_accepts_product_test() -> None:
    changes = testing.parse_name_status_lines(
        [
            "M\tproducts/pokemon-tcg-search/web/app.js",
            "M\tproducts/pokemon-tcg-search/tests/test_web.py",
        ]
    )

    result = testing.evaluate_testing_policy(
        lane=LaneEnum.WEB,
        changes=changes,
        testing_metadata=metadata("- Updated Pokemon web contract tests"),
    )

    assert result.relevant_tests_changed is True
    assert result.failure_code is None


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
    assert "No mapped logic-bearing source changes detected." in completed.stdout


def _run_check_script(
    tmp_path: Path,
    changed_lines: list[str],
    metadata_text: str,
    *,
    event_name: str | None = None,
) -> subprocess.CompletedProcess[str]:
    """Invoke scripts/ci/check_tests_with_code.py the way CI does.

    `event_name=None` omits the flag, exercising the script's default
    (fail-closed `pull_request` enforcement).
    """
    changed_files = tmp_path / "changed.txt"
    changed_files.write_text("\n".join(changed_lines) + "\n")
    metadata_path = tmp_path / "metadata.md"
    metadata_path.write_text(metadata_text)
    cmd = [
        sys.executable,
        "scripts/ci/check_tests_with_code.py",
        "--changed-files",
        str(changed_files),
        "--metadata-file",
        str(metadata_path),
    ]
    if event_name is not None:
        cmd += ["--event-name", event_name]
    return subprocess.run(
        cmd,
        cwd=Path(__file__).resolve().parents[3],
        text=True,
        capture_output=True,
    )


def test_check_tests_with_code_push_logic_change_without_pr_body_requires_matching_tests(
    tmp_path: Path,
) -> None:
    """A push lacks a review body but cannot bypass matching-test evidence."""
    result = _run_check_script(
        tmp_path,
        ["M\tpackages/policies/testing.py"],
        "",
        event_name="push",
    )

    assert result.returncode == 1
    assert "python: missing_tests_for_logic_change" in result.stdout


def test_check_tests_with_code_push_reports_matching_tests_in_diff(
    tmp_path: Path,
) -> None:
    """On a `push`, the script still reports lane-matching tests visible in
    the pushed diff even though it cannot read a PR body."""
    result = _run_check_script(
        tmp_path,
        [
            "M\tpackages/policies/testing.py",
            "M\ttests/python/unit/test_testing_policy.py",
        ],
        "",
        event_name="push",
    )

    assert result.returncode == 0, result.stdout
    assert "matching tests in every affected area" in result.stdout


def test_check_tests_with_code_push_requires_tests_for_each_affected_ios_product(
    tmp_path: Path,
) -> None:
    result = _run_check_script(
        tmp_path,
        [
            "M\tproducts/life-clock-ios/Sources/App/LifeClockApp.swift",
            "M\tproducts/catchbook-ios/Tests/App/CatchbookAppTests.swift",
        ],
        "",
        event_name="push",
    )

    assert result.returncode == 1
    assert "ios: missing_tests_for_logic_change" in result.stdout


@pytest.mark.parametrize("reason", ["comments_only", "config_no_behavior_change"])
def test_check_tests_with_code_push_honors_explicit_reviewed_exception(
    tmp_path: Path,
    reason: str,
) -> None:
    result = _run_check_script(
        tmp_path,
        ["M\tpackages/policies/testing.py"],
        f"## Testing\n\nno_test_reason_code={reason}\n- reviewed exception\n",
        event_name="push",
    )

    assert result.returncode == 0, result.stdout
    assert "python: pass" in result.stdout


def test_check_tests_with_code_push_docs_only_passes(tmp_path: Path) -> None:
    """A docs-only `push` has no logic-bearing changes and passes."""
    result = _run_check_script(
        tmp_path, ["M\tapps/api/README.md"], "", event_name="push"
    )

    assert result.returncode == 0
    assert "No mapped logic-bearing source changes detected." in result.stdout


def test_check_tests_with_code_pull_request_logic_without_testing_section_fails(
    tmp_path: Path,
) -> None:
    """PR enforcement preserved: a logic change whose PR body has no
    `## Testing` section still fails on a `pull_request` event."""
    result = _run_check_script(
        tmp_path,
        ["M\tpackages/policies/testing.py"],
        "## Summary\n\n- no testing section here\n",
        event_name="pull_request",
    )

    assert result.returncode == 1
    assert "python: missing_testing_metadata" in result.stdout


def test_check_tests_with_code_pull_request_logic_with_tests_and_section_passes(
    tmp_path: Path,
) -> None:
    """PR enforcement preserved: a logic change with matching tests and a
    `## Testing` section passes on a `pull_request` event."""
    result = _run_check_script(
        tmp_path,
        [
            "M\tpackages/policies/testing.py",
            "M\ttests/python/unit/test_testing_policy.py",
        ],
        "## Testing\n\n- added policy tests\n",
        event_name="pull_request",
    )

    assert result.returncode == 0
    assert "python: pass" in result.stdout


def test_check_tests_with_code_pull_request_honors_no_test_exception(
    tmp_path: Path,
) -> None:
    """PR no-test exceptions still behave: a valid `no_test_reason_code` in
    the `## Testing` section lets a logic change pass without tests."""
    result = _run_check_script(
        tmp_path,
        ["M\tpackages/policies/testing.py"],
        "## Testing\n\nno_test_reason_code=comments_only\n- comment-only edit\n",
        event_name="pull_request",
    )

    assert result.returncode == 0
    assert "python: pass" in result.stdout
