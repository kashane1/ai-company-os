from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from packages.policies.approvals import requires_human_approval
from packages.schemas.task_packet import Goal, RiskLevel, TaskPacket, WorkerLane


def plan_goal(goal: Goal) -> list[TaskPacket]:
    summary = goal.summary.lower()

    if "app store" in summary or "testflight" in summary or "submission" in summary:
        lane = WorkerLane.APPSTORE
        risk = RiskLevel.HIGH
    elif any(
        keyword in summary
        for keyword in (
            "ios",
            "iphone",
            "xcode",
            "swift",
            "swiftui",
            "widget",
            "cloudkit",
            "activitykit",
            "app intent",
        )
    ):
        lane = WorkerLane.IOS
        risk = RiskLevel.MEDIUM
    else:
        lane = WorkerLane.ENGINEERING
        risk = RiskLevel.LOW

    task = TaskPacket(
        id=f"{goal.id}-001",
        goal_id=goal.id,
        lane=lane,
        title=goal.title,
        summary=goal.summary,
        risk_level=risk,
        constraints=[
            "Use an isolated worktree for repo mutations.",
            "Report structured results back to the platform.",
            "Do not bypass shared policy.",
        ],
    )

    if requires_human_approval(task):
        task = TaskPacket(
            id=task.id,
            goal_id=task.goal_id,
            lane=task.lane,
            title=task.title,
            summary=task.summary,
            risk_level=task.risk_level,
            requires_approval=True,
            constraints=task.constraints,
        )

    return [task]


if __name__ == "__main__":
    demo_goal = Goal(
        id="goal-001",
        title="Prepare an App Store submission",
        summary="Prepare release metadata and submission state for an iOS patch.",
    )
    print(plan_goal(demo_goal))
