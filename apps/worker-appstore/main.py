from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from packages.schemas.task_packet import TaskPacket, TaskResult, TaskStatus


def execute(task: TaskPacket) -> TaskResult:
    return TaskResult(
        task_id=task.id,
        status=TaskStatus.BLOCKED if task.requires_approval else TaskStatus.PENDING,
        summary=(
            "App Store worker scaffold only. Final submission and review actions must remain "
            "approval-gated."
        ),
        next_actions=[
            "Prepare release metadata.",
            "Track TestFlight and submission state.",
            "Pause for approval before irreversible actions.",
        ],
    )
