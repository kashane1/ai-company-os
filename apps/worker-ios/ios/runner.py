from dataclasses import asdict, replace
from datetime import UTC, datetime
from pathlib import Path
import sys
from typing import Callable

ROOT = Path(__file__).resolve().parents[3]
ENGINEERING_APP = ROOT / "apps" / "worker-engineering"
for entry in (ROOT, ENGINEERING_APP):
    if str(entry) not in sys.path:
        sys.path.insert(0, str(entry))

from engineering.git_state import capture_git_state
from engineering.repo_manager import prepare_repo
from engineering.worktree_manager import prepare_worktree
from packages.config.repositories import load_repo_configs
from packages.db.task_run_store import TaskRunStore
from packages.db.task_store import TaskStore
from packages.db.worktree_store import WorktreeStore
from packages.schemas.approval import ApprovalRecord
from packages.schemas.task_packet import TaskResult, TaskStatus
from packages.schemas.task_run import TaskRun, TaskRunStatus

from ios.codex_runner import execute_codex, render_task_packet
from ios.review import build_summary, classify_result, create_approval_record, write_review_artifact
from ios.validator import capture_diff, validate_run


def execute_task(
    task_id: str,
    *,
    update_task_status: bool = True,
    approval_factory: Callable[[str, str, str, str], ApprovalRecord] | None = None,
) -> TaskResult:
    started_at = datetime.now(UTC).isoformat()
    task_store = TaskStore()
    task = task_store.load(task_id)
    if update_task_status:
        task_store.set_status(task.id, TaskStatus.IN_PROGRESS, updated_at=started_at)

    repo_config = load_repo_configs()[task.repo_id]
    repo_record = prepare_repo(repo_config)
    worktree = prepare_worktree(task, repo_record)
    packet_path = render_task_packet(task, worktree)
    worktree = replace(worktree, packet_path=packet_path)
    WorktreeStore().save(worktree)
    pre_run_git_state = capture_git_state(worktree.root_path)
    execution_result_path, execution, summary_artifact_path, metadata_artifact_path = execute_codex(
        task, worktree, packet_path
    )
    post_run_git_state = capture_git_state(worktree.root_path)
    diff_path = capture_diff(worktree, task.id)
    validation_checks = validate_run(
        task,
        packet_path,
        worktree.root_path,
        execution_result_path,
        execution.exit_code,
        diff_path,
        post_run_git_state.status_lines,
    )
    validation_checks, testing_policy, testing_summary = validation_checks
    classification = classify_result(
        execution.exit_code,
        validation_checks,
        post_run_git_state,
    )
    failure_codes = [check.code for check in validation_checks if not check.passed and check.code]

    run_status = (
        TaskRunStatus.SUCCEEDED if all(check.passed for check in validation_checks) else TaskRunStatus.FAILED
    )
    finished_at = datetime.now(UTC).isoformat()
    summary = build_summary(task, classification, post_run_git_state.changed_files)
    review_artifact_path = write_review_artifact(
        task=task,
        worktree_path=worktree.root_path,
        changed_files=post_run_git_state.changed_files,
        validation_checks=validation_checks,
        testing_policy=testing_policy,
        testing_summary=testing_summary,
        failure_codes=failure_codes,
        stdout_path=execution.stdout_path,
        stderr_path=execution.stderr_path,
        diff_path=diff_path,
        summary=summary,
    )
    approval = None
    if classification.value == "safe_for_review":
        task_run_id = f"run-{task.id}"
        if approval_factory is not None:
            approval = approval_factory(task.id, task_run_id, review_artifact_path, summary)
        else:
            approval = create_approval_record(
                task=task,
                task_run_id=task_run_id,
                review_artifact_path=review_artifact_path,
                summary=summary,
            )

    task_run = TaskRun(
        id=f"run-{task.id}",
        task_id=task.id,
        worker_lane=task.lane,
        repo_id=repo_record.id,
        worktree_id=worktree.id,
        worktree_path=worktree.root_path,
        packet_path=packet_path,
        execution_result_path=execution_result_path,
        execution=execution,
        pre_run_git_state=pre_run_git_state,
        post_run_git_state=post_run_git_state,
        diff_path=diff_path,
        classification=classification,
        review_artifact_path=review_artifact_path,
        approval_id=approval.id if approval else None,
        status=run_status,
        summary=summary,
        started_at=started_at,
        finished_at=finished_at,
        validation_checks=validation_checks,
        testing_policy=testing_policy,
        failure_codes=failure_codes,
        artifacts=[
            packet_path,
            execution_result_path,
            execution.stdout_path,
            execution.stderr_path,
            diff_path,
            review_artifact_path,
            summary_artifact_path,
            metadata_artifact_path,
        ],
    )
    TaskRunStore().save(task_run)

    final_status = (
        TaskStatus.COMPLETED
        if classification.value in {"safe_for_review", "no_change"}
        else TaskStatus.FAILED
    )
    if update_task_status:
        task_store.set_status(task.id, final_status, updated_at=finished_at)

    return TaskResult(
        task_id=task.id,
        status=final_status,
        summary=summary,
        run_id=task_run.id,
        repo_id=repo_record.id,
        worktree_path=worktree.root_path,
        classification=classification.value,
        review_artifact_path=review_artifact_path,
        approval_id=approval.id if approval else None,
        artifacts=task_run.artifacts,
        validation_checks=[check.name for check in task_run.validation_checks if check.passed],
        failure_codes=failure_codes,
        next_actions=[
            "Inspect the iOS review artifact and diff before any git history mutation is introduced.",
            "Use the approval record as the future gate for commit, push, and PR phases.",
        ],
    )


def result_as_dict(result: TaskResult) -> dict[str, object]:
    payload = asdict(result)
    payload["status"] = result.status.value
    return payload
