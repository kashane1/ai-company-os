import json
from datetime import UTC, datetime
from pathlib import Path

from packages.config.settings import ensure_runtime_directories
from packages.db.approval_store import ApprovalStore
from packages.schemas.approval import ApprovalRecord, ApprovalStatus
from packages.schemas.task import Task
from packages.schemas.task_run import (
    EngineeringResultClassification,
    GitStateSnapshot,
    ValidationCheck,
)


def classify_result(
    execution_exit_code: int,
    validation_checks: list[ValidationCheck],
    post_run_git_state: GitStateSnapshot,
) -> EngineeringResultClassification:
    if execution_exit_code != 0:
        return EngineeringResultClassification.EXECUTION_FAILED

    if not all(check.passed for check in validation_checks):
        return EngineeringResultClassification.VALIDATION_FAILED

    if not post_run_git_state.changed_files:
        return EngineeringResultClassification.NO_CHANGE

    return EngineeringResultClassification.SAFE_FOR_REVIEW


def build_summary(
    task: Task,
    classification: EngineeringResultClassification,
    changed_files: list[str],
) -> str:
    if classification is EngineeringResultClassification.SAFE_FOR_REVIEW:
        return (
            f"Task {task.id} completed successfully and changed {len(changed_files)} file(s). "
            "The worktree is ready for manual review."
        )
    if classification is EngineeringResultClassification.NO_CHANGE:
        return f"Task {task.id} completed but produced no tracked file changes."
    if classification is EngineeringResultClassification.VALIDATION_FAILED:
        return f"Task {task.id} executed but did not pass validation."
    return f"Task {task.id} failed during Codex execution."


def write_review_artifact(
    task: Task,
    worktree_path: str,
    changed_files: list[str],
    validation_checks: list[ValidationCheck],
    stdout_path: str,
    stderr_path: str,
    diff_path: str,
    summary: str,
) -> str:
    paths = ensure_runtime_directories()
    artifact_dir = paths.engineering_artifacts_root / task.id
    artifact_dir.mkdir(parents=True, exist_ok=True)

    payload = {
        "task_id": task.id,
        "worktree_path": worktree_path,
        "changed_files": changed_files,
        "validator_results": [check.to_dict() for check in validation_checks],
        "stdout_path": stdout_path,
        "stderr_path": stderr_path,
        "diff_path": diff_path,
        "summary": summary,
        "created_at": datetime.now(UTC).isoformat(),
    }
    review_path = artifact_dir / "review_summary.json"
    with review_path.open("w") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)

    return str(review_path)


def create_approval_record(
    task: Task,
    task_run_id: str,
    review_artifact_path: str,
    summary: str,
) -> ApprovalRecord:
    approval = ApprovalRecord(
        id=f"approval-{task.id}",
        task_id=task.id,
        task_run_id=task_run_id,
        status=ApprovalStatus.PENDING,
        approval_type="engineering_review",
        summary=summary,
        review_artifact_path=review_artifact_path,
        created_at=datetime.now(UTC).isoformat(),
    )
    ApprovalStore().save(approval)
    return approval
