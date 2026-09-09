import json
import sys
import time
from dataclasses import asdict, replace
from datetime import UTC, datetime
from pathlib import Path
from threading import Event

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from apps.api.control_plane import ControlPlaneService
from packages.config.settings import load_runtime_paths
from packages.db.approval_store import ApprovalStore
from packages.db.release_store import ReleaseStore
from packages.db.task_store import TaskStore
from packages.policies.approvals import (
    APPROVAL_REQUIRED_RELEASE_ACTIONS,
    SAFE_RELEASE_ACTIONS,
    PolicyViolation,
    requires_release_action_approval,
)
from packages.policies.release_readiness import (
    APP_STORE_SUBMISSION_APPROVAL_TYPE,
    approve_app_store_submission,
)
from packages.schemas.approval import ApprovalStatus
from packages.schemas.release import ReleaseRecord, ReleaseStatus, StoreChannelStatus
from packages.schemas.task_packet import TaskPacket, TaskResult, TaskStatus, WorkerLane
from packages.tools.worker_loop import (
    WorkerLoopStats,
    redacted_error_message,
    worker_exit_code,
)
from packages.tools.worker_loop import run_worker_loop as shared_worker_loop


def inspect_release(release_id: str) -> ReleaseRecord:
    return ReleaseStore().load_release_record(release_id)


def _approval_type_for_action(action: str) -> str:
    if action == "submit_appstore":
        return APP_STORE_SUBMISSION_APPROVAL_TYPE
    return "release_action"


def execute_release_action(release_id: str, action: str, approval_id: str | None = None) -> TaskResult:
    if action not in SAFE_RELEASE_ACTIONS | APPROVAL_REQUIRED_RELEASE_ACTIONS:
        return TaskResult(
            task_id=release_id,
            status=TaskStatus.BLOCKED,
            summary=f"Unsupported release action {action} is blocked.",
            next_actions=["Use a supported App Store release action."],
        )

    release_store = ReleaseStore()
    release = release_store.load_release_record(release_id)
    needs_approval = requires_release_action_approval(action)

    if needs_approval:
        if not approval_id:
            return TaskResult(
                task_id=release_id,
                status=TaskStatus.BLOCKED,
                summary=f"Release action {action} is blocked pending approval.",
                next_actions=[
                    "Create or approve the release approval record.",
                    "Retry the action once approval is granted.",
                ],
            )
        try:
            approval = ApprovalStore().load(approval_id)
        except FileNotFoundError:
            return TaskResult(
                task_id=release_id,
                status=TaskStatus.BLOCKED,
                summary=(
                    f"Release action {action} is blocked because its approval record "
                    "is unavailable."
                ),
                next_actions=["Create and approve the matching release approval record."],
            )
        if (
            approval.status is not ApprovalStatus.APPROVED
            or approval.approval_type != _approval_type_for_action(action)
            or approval.subject_type != "release"
            or approval.subject_id != release_id
            or approval.action != action
        ):
            return TaskResult(
                task_id=release_id,
                status=TaskStatus.BLOCKED,
                summary=f"Release action {action} is blocked because its approval does not match.",
                next_actions=["Approve the matching release action before retrying."],
            )

    validation_checks: list[str] = []
    if action == "submit_appstore":
        assert approval_id is not None  # guarded by the approval-required branch above
        try:
            approve_app_store_submission(
                release_id,
                approval_id,
                product_id=release.product_id,
                expected_action=action,
            )
        except PolicyViolation as exc:
            return TaskResult(
                task_id=release_id,
                status=TaskStatus.BLOCKED,
                summary=f"Release action {action} is blocked by release readiness: {exc.code}: {exc}",
                next_actions=[
                    "Complete the local submission checklist and signed P0 approval flow.",
                    "Retry the local state transition after readiness passes.",
                ],
                failure_codes=[exc.code],
            )
        validation_checks.append("release_readiness:passed")

    updated = release
    if action == "prepare_testflight":
        updated = replace(
            release,
            testflight_status=StoreChannelStatus.READY,
            status=ReleaseStatus.READY_FOR_REVIEW,
        )
    elif action == "submit_testflight":
        updated = replace(
            release,
            testflight_status=StoreChannelStatus.APPROVED,
            status=ReleaseStatus.READY_FOR_REVIEW,
        )
    elif action == "submit_appstore":
        updated = replace(
            release,
            appstore_status=StoreChannelStatus.APPROVED,
            status=ReleaseStatus.READY_FOR_REVIEW,
        )
    elif action == "release_to_store":
        updated = replace(
            release,
            appstore_status=StoreChannelStatus.APPROVED,
            status=ReleaseStatus.READY_FOR_REVIEW,
        )

    release_store.save_release_record(updated)
    return TaskResult(
        task_id=release_id,
        status=TaskStatus.COMPLETED,
        summary=f"Prepared release state for action {action}.",
        approval_id=approval_id if needs_approval else None,
        validation_checks=validation_checks,
        next_actions=[
            "Inspect the updated release record.",
            "Keep App Store Connect submission manual for now.",
        ],
    )


def _constraint_value(task: TaskPacket, prefix: str) -> str | None:
    for constraint in task.constraints:
        if constraint.startswith(prefix):
            return constraint.split("=", 1)[1]
    return None


def execute(task: TaskPacket) -> TaskResult:
    release_id = _constraint_value(task, "release_id=")
    release_action = _constraint_value(task, "release_action=") or "prepare_testflight"
    approval_id = _constraint_value(task, "approval_id=")

    if not release_id:
        return TaskResult(
            task_id=task.id,
            status=TaskStatus.BLOCKED,
            summary=(
                "App Store worker is blocked because the task has no release_id "
                "constraint to inspect or prepare release state."
            ),
            next_actions=[
                "Create a release record first.",
                "Pass release_id and release_action constraints to the App Store worker.",
            ],
            failure_codes=["missing_release_id"],
        )

    return execute_release_action(release_id, release_action, approval_id=approval_id)


def _task_packet_from_record(task_id: str) -> TaskPacket:
    task = TaskStore().load(task_id)
    return TaskPacket(
        id=task.id,
        goal_id=task.goal_id or "",
        lane=task.lane,
        title=task.title,
        summary=task.summary,
        risk_level=task.risk_level,
        requires_approval=task.requires_approval,
        constraints=task.constraints,
    )


def execute_claimed_task(*, worker_id: str, service: ControlPlaneService | None = None) -> TaskResult | None:
    control_plane = service or ControlPlaneService()
    task = control_plane.claim_task(lane=WorkerLane.APPSTORE, worker_id=worker_id)
    if task is None:
        return None

    packet = _task_packet_from_record(task.id)
    release_id = _constraint_value(packet, "release_id=")
    release_action = _constraint_value(packet, "release_action=") or "prepare_testflight"
    approval_id = _constraint_value(packet, "approval_id=")

    try:
        if release_id and requires_release_action_approval(release_action) and not approval_id:
            approval = control_plane.request_approval(
                summary=f"Approve App Store release action {release_action} for release {release_id}.",
                subject_type="release",
                subject_id=release_id,
                action=release_action,
                approval_type=_approval_type_for_action(release_action),
                task_id=task.id,
            )
            result = TaskResult(
                task_id=task.id,
                status=TaskStatus.BLOCKED,
                summary=f"Release action {release_action} is blocked pending approval.",
                approval_id=approval.id,
                next_actions=[
                    "Approve the release action through the control plane.",
                    "Retry the App Store task after approval is granted.",
                ],
            )
        else:
            result = execute(packet)
    except Exception as exc:
        summary = f"App Store worker execution failed: {redacted_error_message(exc)}"
        control_plane.submit_task_result(
            task_id=task.id,
            status=TaskStatus.FAILED,
            summary=summary,
            worker_id=worker_id,
        )
        return TaskResult(task_id=task.id, status=TaskStatus.FAILED, summary=summary)

    release_id = _constraint_value(packet, "release_id=") or ""
    release_action = _constraint_value(packet, "release_action=") or "prepare_testflight"
    artifact_file = (
        load_runtime_paths().artifacts_root
        / "appstore"
        / task.id
        / "submission_summary.json"
    )
    artifact_path = str(artifact_file)
    artifact_file.parent.mkdir(parents=True, exist_ok=True)
    artifact_file.write_text(
        json.dumps(
            {
                "task_id": task.id,
                "release_id": release_id,
                "action": release_action,
                "status": result.status.value,
                "summary": result.summary,
                "validation_checks": result.validation_checks,
                "failure_codes": result.failure_codes,
                "written_at": datetime.now(UTC).isoformat(),
            }
        ),
        encoding="utf-8",
    )

    submitted = control_plane.submit_task_result(
        task_id=task.id,
        status=result.status,
        summary=result.summary,
        worker_id=worker_id,
        approval_id=result.approval_id,
        artifacts=[artifact_path],
        events=["task_claimed"] if result.status is TaskStatus.COMPLETED else [],
    )
    if submitted.status is not result.status:
        return replace(
            result,
            status=submitted.status,
            summary=submitted.error_summary or result.summary,
            failure_codes=[*result.failure_codes, "post_run_validation_failed"],
        )
    return result


def run_worker_loop(
    *,
    worker_id: str,
    service: ControlPlaneService | None = None,
    poll_interval_seconds: float = 2.0,
    stop_event: Event | None = None,
    sleep_fn=time.sleep,
    max_iterations: int | None = None,
) -> WorkerLoopStats:
    control_plane = service or ControlPlaneService()
    return shared_worker_loop(
        worker_id=worker_id,
        work_once=lambda: execute_claimed_task(worker_id=worker_id, service=control_plane),
        poll_interval_seconds=poll_interval_seconds,
        stop_event=stop_event,
        sleep_fn=sleep_fn,
        max_iterations=max_iterations,
        sleep_after_result=True,
    )


if __name__ == "__main__":
    try:
        stats = run_worker_loop(worker_id="worker-appstore")
    except KeyboardInterrupt:
        stats = WorkerLoopStats(
            worker_id="worker-appstore",
            processed_count=0,
            idle_cycles=0,
            stop_reason="interrupted",
        )
    print(json.dumps({"stats": asdict(stats)}, default=str))
    raise SystemExit(worker_exit_code(stats))
