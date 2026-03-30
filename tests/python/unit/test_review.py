from __future__ import annotations

import json
from pathlib import Path

from engineering.review import (
    build_summary,
    classify_result,
    create_approval_record,
    write_review_artifact,
)
from packages.db.approval_store import ApprovalStore
from packages.schemas.approval import ApprovalStatus
from packages.schemas.task_run import EngineeringResultClassification, GitStateSnapshot, ValidationCheck
from tests.python.factories.task_data import build_task


def test_classify_result_covers_all_review_outcomes() -> None:
    passed_checks = [ValidationCheck(name="tests", passed=True, details="ok")]
    failed_checks = [ValidationCheck(name="tests", passed=False, details="failed")]
    changed_state = GitStateSnapshot(status_lines=["M  app.py"], changed_files=["app.py"], diff_summary="")
    clean_state = GitStateSnapshot(status_lines=[], changed_files=[], diff_summary="")

    assert (
        classify_result(execution_exit_code=1, validation_checks=passed_checks, post_run_git_state=changed_state)
        is EngineeringResultClassification.EXECUTION_FAILED
    )
    assert (
        classify_result(execution_exit_code=0, validation_checks=failed_checks, post_run_git_state=changed_state)
        is EngineeringResultClassification.VALIDATION_FAILED
    )
    assert (
        classify_result(execution_exit_code=0, validation_checks=passed_checks, post_run_git_state=clean_state)
        is EngineeringResultClassification.NO_CHANGE
    )
    assert (
        classify_result(execution_exit_code=0, validation_checks=passed_checks, post_run_git_state=changed_state)
        is EngineeringResultClassification.SAFE_FOR_REVIEW
    )


def test_build_summary_returns_expected_message_for_each_classification() -> None:
    task = build_task()

    assert build_summary(task, EngineeringResultClassification.SAFE_FOR_REVIEW, ["a.py", "b.py"]) == (
        "Task task-123 completed successfully and changed 2 file(s). "
        "The worktree is ready for manual review."
    )
    assert (
        build_summary(task, EngineeringResultClassification.NO_CHANGE, [])
        == "Task task-123 completed but produced no tracked file changes."
    )
    assert (
        build_summary(task, EngineeringResultClassification.VALIDATION_FAILED, ["a.py"])
        == "Task task-123 executed but did not pass validation."
    )
    assert (
        build_summary(task, EngineeringResultClassification.EXECUTION_FAILED, ["a.py"])
        == "Task task-123 failed during Codex execution."
    )


def test_write_review_artifact_writes_expected_payload_shape(isolated_repo_root: Path) -> None:
    task = build_task()
    checks = [ValidationCheck(name="tests", passed=True, details="All checks passed")]

    review_path = write_review_artifact(
        task=task,
        worktree_path="/tmp/worktree",
        changed_files=["src/app.py"],
        validation_checks=checks,
        stdout_path="/tmp/stdout.log",
        stderr_path="/tmp/stderr.log",
        diff_path="/tmp/diff.patch",
        summary="Ready for review",
    )

    payload = json.loads(Path(review_path).read_text())

    assert set(payload) == {
        "changed_files",
        "created_at",
        "diff_path",
        "stderr_path",
        "stdout_path",
        "summary",
        "task_id",
        "validator_results",
        "worktree_path",
    }
    assert payload["task_id"] == "task-123"
    assert payload["changed_files"] == ["src/app.py"]
    assert payload["validator_results"] == [
        {"details": "All checks passed", "name": "tests", "passed": True}
    ]
    assert payload["stdout_path"] == "/tmp/stdout.log"
    assert payload["stderr_path"] == "/tmp/stderr.log"
    assert payload["diff_path"] == "/tmp/diff.patch"
    assert payload["summary"] == "Ready for review"


def test_create_approval_record_persists_pending_engineering_review(
    isolated_repo_root: Path,
) -> None:
    task = build_task()

    approval = create_approval_record(
        task=task,
        task_run_id="run-task-123",
        review_artifact_path="/tmp/review.json",
        summary="Ready for review",
    )
    saved = ApprovalStore().load(approval.id)

    assert approval.id == "approval-task-123"
    assert approval.status is ApprovalStatus.PENDING
    assert approval.approval_type == "engineering_review"
    assert approval.action == "review_engineering_task"
    assert saved.review_artifact_path == "/tmp/review.json"
    assert saved.subject_id == "run-task-123"

