"""Typed enqueue wrappers for Claude-driven supervisor sessions (Phase 1.3).

Claude opens a :class:`SupervisorSession` (Phase 3.3) and calls these thin
wrappers. Results are **not** awaited here — the existing worker-engineering,
worker-ios, and worker-gtm loops claim tasks from the control plane and
execute. Claude reads results back via ``SessionHandle.read_result`` on the
next session.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from apps.api.control_plane import ControlPlaneService
from packages.schemas.task import Task
from packages.schemas.task_packet import RiskLevel, WorkerLane


@dataclass(frozen=True)
class EngineeringTaskDef:
    goal_id: str
    repo_id: str
    title: str
    summary: str
    task_type: str = "engineering_change"
    product_id: str | None = None
    risk_level: RiskLevel = RiskLevel.LOW
    requires_approval: bool = False
    constraints: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class IOSTaskDef:
    goal_id: str
    repo_id: str
    title: str
    summary: str
    task_type: str = "ios_change"
    product_id: str | None = None
    risk_level: RiskLevel = RiskLevel.LOW
    requires_approval: bool = False
    constraints: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class GTMTaskDef:
    goal_id: str
    repo_id: str
    title: str
    summary: str
    task_type: str  # one of CONTENT_DRAFT / SOCIAL_POST_SCHEDULE / ...
    product_id: str | None = None
    requires_approval: bool = False
    constraints: list[str] = field(default_factory=list)


def enqueue_engineering(
    task: EngineeringTaskDef,
    *,
    service: ControlPlaneService | None = None,
) -> Task:
    return _enqueue(task, lane=WorkerLane.ENGINEERING, service=service)


def enqueue_ios(
    task: IOSTaskDef,
    *,
    service: ControlPlaneService | None = None,
) -> Task:
    return _enqueue(task, lane=WorkerLane.IOS, service=service)


def enqueue_gtm(
    task: GTMTaskDef,
    *,
    service: ControlPlaneService | None = None,
) -> Task:
    # Worker lane "gtm" is added by Phase 2.1 registration; fall back to the
    # underlying lane value if the enum hasn't grown yet.
    try:
        lane = WorkerLane("gtm")  # type: ignore[call-arg]
    except ValueError:
        lane = WorkerLane.SUPERVISOR
    return _enqueue(task, lane=lane, service=service)


def _enqueue(
    task: EngineeringTaskDef | IOSTaskDef | GTMTaskDef,
    *,
    lane: WorkerLane,
    service: ControlPlaneService | None,
) -> Task:
    control_plane = service or ControlPlaneService()
    return control_plane.create_task_for_goal(
        goal_id=task.goal_id,
        repo_id=task.repo_id,
        lane=lane,
        title=task.title,
        summary=task.summary,
        task_type=task.task_type,
        risk_level=getattr(task, "risk_level", RiskLevel.LOW),
        product_id=task.product_id,
        requires_approval=task.requires_approval,
        constraints=list(task.constraints),
    )
