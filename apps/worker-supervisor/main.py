from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from packages.policies.approvals import requires_human_approval
from packages.schemas.testing import NoTestReasonCode, TestLane
from packages.schemas.task_packet import Goal, RiskLevel, TaskPacket, WorkerLane
from packages.tools.learning.worker_signals import augment_packet_constraints


def plan_goal(goal: Goal) -> list[TaskPacket]:
    summary = goal.summary.lower()

    if "app store" in summary or "testflight" in summary or "submission" in summary:
        lane = WorkerLane.APPSTORE
        risk = RiskLevel.HIGH
    elif any(
        keyword in summary
        for keyword in (
            "deploy",
            "publish",
            "go live",
            "ship the site",
            "netlify",
            "production site",
        )
    ):
        # Putting a site in front of the public is high-blast-radius and gated
        # in packages/policies/deploy_readiness.py — route it to its own lane,
        # separate from building (mirrors the IOS → APPSTORE split).
        lane = WorkerLane.WEBDEPLOY
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
    elif any(
        keyword in summary
        for keyword in (
            "website",
            "web app",
            "web page",
            "webpage",
            "landing page",
            "waitlist",
            "marketing site",
            "frontend",
            "front-end",
            "astro",
            "next.js",
            "nextjs",
        )
    ):
        lane = WorkerLane.WEB
        risk = RiskLevel.MEDIUM
    else:
        lane = WorkerLane.ENGINEERING
        risk = RiskLevel.LOW

    base_constraints = [
        "Use an isolated worktree for repo mutations.",
        "Report structured results back to the platform.",
        "Do not bypass shared policy.",
    ]
    task = TaskPacket(
        id=f"{goal.id}-001",
        goal_id=goal.id,
        lane=lane,
        title=goal.title,
        summary=goal.summary,
        risk_level=risk,
        constraints=augment_packet_constraints(
            lane=lane.value,
            base_constraints=base_constraints,
        ),
        tests_required=lane in {WorkerLane.ENGINEERING, WorkerLane.IOS, WorkerLane.WEB},
        test_lane=(
            TestLane.IOS
            if lane is WorkerLane.IOS
            else TestLane.PYTHON
            if lane is WorkerLane.ENGINEERING
            else TestLane.WEB
            if lane is WorkerLane.WEB
            else TestLane.NONE
        ),
        allowed_no_test_reason_codes=[
            NoTestReasonCode.COMMENTS_ONLY,
            NoTestReasonCode.CONFIG_NO_BEHAVIOR_CHANGE,
            NoTestReasonCode.APPROVED_FOLLOWUP_TEST_TASK,
        ]
        if lane is WorkerLane.ENGINEERING
        # iOS and WEB are both UI lanes: visual-only, non-logic changes are a
        # legitimate no-test reason (a copy/styling tweak needn't ship a test).
        else [
            NoTestReasonCode.COMMENTS_ONLY,
            NoTestReasonCode.VISUAL_ONLY_NON_LOGIC,
            NoTestReasonCode.CONFIG_NO_BEHAVIOR_CHANGE,
            NoTestReasonCode.APPROVED_FOLLOWUP_TEST_TASK,
        ]
        if lane in {WorkerLane.IOS, WorkerLane.WEB}
        else [],
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
            tests_required=task.tests_required,
            test_lane=task.test_lane,
            allowed_no_test_reason_codes=task.allowed_no_test_reason_codes,
        )

    return [task]


if __name__ == "__main__":
    demo_goal = Goal(
        id="goal-001",
        title="Prepare an App Store submission",
        summary="Prepare release metadata and submission state for an iOS patch.",
    )
    print(plan_goal(demo_goal))
