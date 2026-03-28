from dataclasses import replace
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from packages.db.approval_store import ApprovalStore
from packages.db.release_store import ReleaseStore
from packages.policies.approvals import requires_release_action_approval
from packages.schemas.approval import ApprovalStatus
from packages.schemas.release import ReleaseRecord, ReleaseStatus, StoreChannelStatus
from packages.schemas.task_packet import TaskPacket, TaskResult, TaskStatus


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
