from datetime import UTC, datetime
from dataclasses import asdict, dataclass, replace
import json
from pathlib import Path
import time
import sys
from threading import Event

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from apps.api.control_plane import ControlPlaneService
from packages.db.task_store import TaskStore
from packages.db.approval_store import ApprovalStore
from packages.db.release_store import ReleaseStore
from packages.policies.approvals import requires_release_action_approval
from packages.schemas.approval import ApprovalRecord, ApprovalStatus
from packages.schemas.release import ReleaseRecord, ReleaseStatus, StoreChannelStatus
from packages.schemas.task_packet import RiskLevel, TaskPacket, TaskResult, TaskStatus, WorkerLane


@dataclass(frozen=True)
class WorkerLoopStats:
    worker_id: str
    processed_count: int
    idle_cycles: int
    stop_reason: str


def inspect_release(release_id: str) -> ReleaseRecord:
    return ReleaseStore().load_release_record(release_id)


def execute_release_action(release_id: str, action: str, approval_id: str | None = None) -> TaskResult:
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
        approval = ApprovalStore().load(approval_id)
        if approval.status is not ApprovalStatus.APPROVED:
            return TaskResult(
                task_id=release_id,
                status=TaskStatus.BLOCKED,
                summary=f"Release action {action} is still waiting for approval.",
                next_actions=["Approve the release action before retrying."],
            )

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
            status=TaskStatus.PENDING,
            summary="App Store worker requires a release_id constraint to inspect or prepare release state.",
            next_actions=[
                "Create a release record first.",
                "Pass release_id and release_action constraints to the App Store worker.",
            ],
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
                approval_type="release_action",
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
        summary = f"App Store worker execution failed: {exc}"
        control_plane.submit_task_result(
            task_id=task.id,
            status=TaskStatus.FAILED,
            summary=summary,
            worker_id=worker_id,
        )
        raise

    release_id = _constraint_value(packet, "release_id=") or ""
    release_action = _constraint_value(packet, "release_action=") or "prepare_testflight"
    artifact_path = f"state/artifacts/appstore/{task.id}/submission_summary.json"
    artifact_file = Path(artifact_path)
    artifact_file.parent.mkdir(parents=True, exist_ok=True)
    artifact_file.write_text(
        json.dumps(
            {
                "task_id": task.id,
                "release_id": release_id,
                "action": release_action,
                "status": "completed",
                "summary": result.summary,
                "written_at": datetime.now(UTC).isoformat(),
            }
        ),
        encoding="utf-8",
    )

    control_plane.submit_task_result(
        task_id=task.id,
        status=result.status,
        summary=result.summary,
        worker_id=worker_id,
        approval_id=result.approval_id,
        artifacts=[artifact_path],
        events=["task_completed"],
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
    stop_signal = stop_event or Event()
    processed_count = 0
    idle_cycles = 0
    iterations = 0
    stop_reason = "stopped"

    while not stop_signal.is_set():
        try:
            result = execute_claimed_task(worker_id=worker_id, service=control_plane)
        except KeyboardInterrupt:
            stop_reason = "interrupted"
            break
        except Exception:
            processed_count += 1
            stop_reason = "failed"
            iterations += 1
            if max_iterations is not None and iterations >= max_iterations:
                break
            continue

        iterations += 1
        if result is None:
            idle_cycles += 1
            stop_reason = "idle"
            try:
                sleep_fn(poll_interval_seconds)
            except KeyboardInterrupt:
                stop_reason = "interrupted"
                break
            if max_iterations is not None and iterations >= max_iterations:
                break
            continue

        processed_count += 1
        stop_reason = "processed"
        try:
            sleep_fn(poll_interval_seconds)
        except KeyboardInterrupt:
            stop_reason = "interrupted"
            break
        if max_iterations is not None and iterations >= max_iterations:
            break

    if stop_signal.is_set():
        stop_reason = "stop_requested"

    return WorkerLoopStats(
        worker_id=worker_id,
        processed_count=processed_count,
        idle_cycles=idle_cycles,
        stop_reason=stop_reason,
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
