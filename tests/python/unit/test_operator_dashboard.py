from __future__ import annotations

from apps.api.control_plane import ControlPlaneService
from packages.dashboard.operator import build_operator_dashboard, render_html
from packages.schemas.approval import ApprovalStatus
from packages.schemas.task_packet import RiskLevel, WorkerLane


def test_operator_dashboard_summarizes_tasks_approvals_events(isolated_repo_root) -> None:
    service = ControlPlaneService()
    goal = service.create_goal(title="Run the company", summary="Operate the loop.")
    task = service.create_task_for_goal(
        goal_id=goal.id,
        repo_id="ai-company-os",
        lane=WorkerLane.ENGINEERING,
        title="Ship a fix",
        summary="Make the control plane visible.",
        task_type="engineering_change",
        risk_level=RiskLevel.LOW,
    )
    service.request_approval(
        summary="Approve production deploy.",
        subject_type="task",
        subject_id=task.id,
        action="deploy_production",
        approval_type="deploy",
        task_id=task.id,
    )

    view = build_operator_dashboard()

    assert view.queued_tasks == 1
    assert view.task_counts["pending"] == 1
    assert view.approval_counts[ApprovalStatus.PENDING.value] == 1
    assert view.lanes
    assert view.tasks[0].title == "Ship a fix"
    assert view.approvals[0].action == "deploy_production"
    assert view.events[0].event_type == "approval_requested"
    assert "Ship a fix" in render_html(view)

