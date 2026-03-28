from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from packages.schemas.task_packet import TaskPacket, TaskResult, TaskStatus


def execute(task: TaskPacket) -> TaskResult:
    return TaskResult(
        task_id=task.id,
        status=TaskStatus.PENDING,
        summary=(
            "iOS worker scaffold only. Next step is Xcode-aware task execution with simulator and "
            "build validation."
        ),
        next_actions=[
            "Create a per-task worktree.",
            "Prepare iOS-specific Codex context.",
            "Run simulator, build, and artifact checks.",
        ],
    )
