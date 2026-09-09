"""Fail-closed evidence checks for completed engineering and iOS task runs."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from packages.db.task_run_store import TaskRunStore
from packages.schemas.task import Task
from packages.schemas.task_packet import WorkerLane

SUPPORTED_LANES = frozenset({WorkerLane.ENGINEERING, WorkerLane.IOS})


@dataclass(frozen=True)
class CompletionEvidenceResult:
    ok: bool
    failure_code: str = ""
    reason: str = ""
    task_run_id: str = ""
    summary: str = ""
    artifacts: tuple[str, ...] = ()
    failure_codes: tuple[str, ...] = ()


def _fail(code: str, reason: str, *, run_id: str = "") -> CompletionEvidenceResult:
    return CompletionEvidenceResult(False, code, reason, task_run_id=run_id)


def _regular_file(path: object) -> bool:
    return isinstance(path, str) and bool(path) and Path(path).is_file()


def _record(value: object) -> dict[str, Any] | None:
    return value if isinstance(value, dict) else None


def _string(value: object) -> bool:
    return isinstance(value, str) and bool(value)


def _all_strings(value: object, *, nonempty: bool = False) -> bool:
    return (
        isinstance(value, list)
        and (not nonempty or bool(value))
        and all(isinstance(item, str) and item for item in value)
    )


def _all_passed_checks(checks: object) -> tuple[bool, str]:
    if not isinstance(checks, list) or not checks:
        return False, "validation_checks_missing"
    names: set[str] = set()
    for check in checks:
        item = _record(check)
        if item is None or not _string(item.get("name")) or type(item.get("passed")) is not bool:
            return False, "validation_check_malformed"
        if item["passed"] is not True:
            return False, "validation_check_failed"
        names.add(item["name"])
    if not {"verification_commands_passed", "tests_with_code_policy"} <= names:
        return False, "validation_checks_incomplete"
    return True, ""


def _review_matches_run(
    review_path: str,
    *,
    task_id: str,
    worktree_path: str,
    stdout_path: str,
    stderr_path: str,
    diff_path: str,
    changed_files: list[str],
    testing_policy: dict[str, Any],
) -> tuple[bool, str]:
    if not _regular_file(review_path) or Path(review_path).stat().st_size == 0:
        return False, "review_artifact_missing"
    try:
        payload = json.loads(Path(review_path).read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return False, "review_artifact_malformed"
    review = _record(payload)
    if review is None:
        return False, "review_artifact_malformed"
    expected = {
        "task_id": task_id,
        "worktree_path": worktree_path,
        "stdout_path": stdout_path,
        "stderr_path": stderr_path,
        "diff_path": diff_path,
        "changed_files": changed_files,
    }
    if any(review.get(key) != value for key, value in expected.items()):
        return False, "review_identity_mismatch"
    passed, _ = _all_passed_checks(review.get("validator_results"))
    if (
        not passed
        or review.get("failure_codes") != []
        or review.get("testing_policy") != testing_policy
    ):
        return False, "review_validation_mismatch"
    return True, ""


def validate_completion_evidence(task: Task) -> CompletionEvidenceResult:
    """Read and validate the deterministic persisted run for ``task``.

    The TaskRun JSON is inspected before schema coercion. This prevents values
    such as ``"false"`` or ``"0"`` from becoming trusted booleans/integers
    while deserializing a worker-controlled record.
    """
    if task.lane not in SUPPORTED_LANES:
        return _fail("completion_evidence_not_required", "lane has no TaskRun completion contract")

    run_id = f"run-{task.id}"
    try:
        raw = TaskRunStore().store.load(run_id)
    except FileNotFoundError:
        return _fail("task_run_missing", f"persisted TaskRun {run_id} was not found", run_id=run_id)
    except (OSError, json.JSONDecodeError, TypeError, ValueError) as exc:
        return _fail(
            "task_run_malformed",
            f"could not read persisted TaskRun: {type(exc).__name__}",
            run_id=run_id,
        )

    run = _record(raw)
    if run is None:
        return _fail("task_run_malformed", "persisted TaskRun is not a mapping", run_id=run_id)
    if run.get("id") != run_id:
        return _fail(
            "task_run_id_mismatch", "persisted TaskRun id does not match task", run_id=run_id
        )
    if run.get("task_id") != task.id:
        return _fail(
            "task_run_task_mismatch", "persisted TaskRun belongs to another task", run_id=run_id
        )
    if run.get("repo_id") != task.repo_id:
        return _fail(
            "task_run_repo_mismatch", "persisted TaskRun belongs to another repo", run_id=run_id
        )
    if run.get("worker_lane") != task.lane.value:
        return _fail(
            "task_run_lane_mismatch", "persisted TaskRun belongs to another lane", run_id=run_id
        )
    if run.get("status") != "succeeded":
        return _fail("task_run_not_succeeded", "persisted TaskRun did not succeed", run_id=run_id)
    classification = run.get("classification")
    if classification not in {"safe_for_review", "no_change"}:
        return _fail(
            "task_run_classification_invalid", "persisted TaskRun is not reviewable", run_id=run_id
        )
    if run.get("failure_codes") != []:
        return _fail(
            "task_run_failure_codes_present", "persisted TaskRun recorded failures", run_id=run_id
        )

    checks_ok, check_code = _all_passed_checks(run.get("validation_checks"))
    if not checks_ok:
        return _fail(
            check_code, "persisted validation checks are incomplete or failed", run_id=run_id
        )

    artifacts = run.get("artifacts")
    if not _all_strings(artifacts):
        return _fail(
            "task_run_artifacts_malformed", "persisted artifact list is malformed", run_id=run_id
        )
    execution = _record(run.get("execution"))
    if execution is None:
        return _fail(
            "execution_record_malformed", "persisted execution record is malformed", run_id=run_id
        )
    if (
        not _all_strings(execution.get("command"), nonempty=True)
        or type(execution.get("exit_code")) is not int
        or execution["exit_code"] != 0
        or execution.get("timed_out") is not False
    ):
        return _fail(
            "execution_not_successful", "persisted execution did not succeed", run_id=run_id
        )
    worktree_path = run.get("worktree_path")
    if not _string(worktree_path) or not Path(worktree_path).is_dir():
        return _fail("worktree_path_invalid", "persisted worktree path is invalid", run_id=run_id)
    testing_policy = _record(run.get("testing_policy"))
    expected_test_lane = "python" if task.lane is WorkerLane.ENGINEERING else "ios"
    if (
        testing_policy is None
        or type(testing_policy.get("tests_required")) is not bool
        or type(testing_policy.get("relevant_tests_changed")) is not bool
        or testing_policy.get("failure_code") is not None
    ):
        return _fail(
            "testing_policy_invalid",
            "persisted testing policy is incomplete or failed",
            run_id=run_id,
        )
    if testing_policy["tests_required"] and testing_policy.get("test_lane") != expected_test_lane:
        return _fail("testing_policy_invalid", "required tests use the wrong lane", run_id=run_id)
    if not testing_policy["tests_required"] and testing_policy.get("test_lane") != "none":
        return _fail("testing_policy_invalid", "no-test policy must use lane none", run_id=run_id)

    execution_result = run.get("execution_result_path")
    stdout_path, stderr_path = execution.get("stdout_path"), execution.get("stderr_path")
    if not all(
        _regular_file(path) and path in artifacts
        for path in (execution_result, stdout_path, stderr_path)
    ):
        return _fail(
            "execution_logs_missing",
            "execution result or logs are absent from persisted evidence",
            run_id=run_id,
        )

    diff_path = run.get("diff_path")
    if not _regular_file(diff_path) or diff_path not in artifacts:
        return _fail("review_diff_missing", "persisted review diff is missing", run_id=run_id)
    try:
        diff_bytes = Path(diff_path).read_bytes()
    except OSError:
        return _fail(
            "review_diff_unreadable", "persisted review diff cannot be read", run_id=run_id
        )
    if classification == "safe_for_review" and not diff_bytes:
        return _fail("review_diff_empty", "reviewable change has an empty diff", run_id=run_id)
    post_state = _record(run.get("post_run_git_state"))
    if post_state is None or not _all_strings(post_state.get("changed_files")):
        return _fail(
            "post_run_git_state_malformed",
            "persisted post-run Git state is malformed",
            run_id=run_id,
        )
    if classification == "no_change" and (diff_bytes or post_state["changed_files"]):
        return _fail(
            "no_change_evidence_mismatch",
            "no-change result has a diff or changed files",
            run_id=run_id,
        )

    verification_results = run.get("verification_results")
    if not isinstance(verification_results, list) or not verification_results:
        return _fail(
            "verification_missing", "no configured verification command was recorded", run_id=run_id
        )
    diff_hash = hashlib.sha256(
        diff_bytes.decode("utf-8", errors="surrogateescape").encode(
            "utf-8", errors="surrogateescape"
        )
    ).hexdigest()
    for result in verification_results:
        verification = _record(result)
        if (
            verification is None
            or not _all_strings(verification.get("command"), nonempty=True)
            or not _string(verification.get("revision"))
            or not _string(verification.get("cwd"))
            or not Path(verification["cwd"]).resolve().is_relative_to(Path(worktree_path).resolve())
        ):
            return _fail(
                "verification_malformed", "verification record is malformed", run_id=run_id
            )
        if (
            type(verification.get("exit_code")) is not int
            or verification["exit_code"] != 0
            or verification.get("timed_out") is not False
        ):
            return _fail(
                "verification_failed", "a recorded verification command did not pass", run_id=run_id
            )
        if verification.get("diff_sha256") != diff_hash:
            return _fail(
                "verification_diff_mismatch",
                "verification did not run against the review diff",
                run_id=run_id,
            )
        for log_path in (verification.get("stdout_path"), verification.get("stderr_path")):
            if not _regular_file(log_path) or log_path not in artifacts:
                return _fail(
                    "verification_logs_missing",
                    "verification log is absent from persisted evidence",
                    run_id=run_id,
                )

    review_path = run.get("review_artifact_path")
    if not isinstance(review_path, str) or review_path not in artifacts:
        return _fail(
            "review_artifact_missing",
            "review artifact is absent from persisted evidence",
            run_id=run_id,
        )
    review_ok, review_code = _review_matches_run(
        review_path,
        task_id=task.id,
        worktree_path=worktree_path,
        stdout_path=stdout_path,
        stderr_path=stderr_path,
        diff_path=diff_path,
        changed_files=post_state["changed_files"],
        testing_policy=testing_policy,
    )
    if not review_ok:
        return _fail(
            review_code, "review artifact does not bind to persisted run evidence", run_id=run_id
        )

    return CompletionEvidenceResult(
        True,
        task_run_id=run_id,
        summary=str(run.get("summary", "")),
        artifacts=tuple(artifacts),
        failure_codes=tuple(run["failure_codes"]),
    )
