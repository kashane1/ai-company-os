from __future__ import annotations

import sys
from pathlib import Path

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from apps.api.approval_endpoint import router as approval_router  # noqa: E402
from apps.api.control_plane import ControlPlaneService, as_payload  # noqa: E402
from apps.api.dashboard_endpoint import router as dashboard_router  # noqa: E402
from apps.api.discovery_endpoint import router as discovery_router  # noqa: E402
from apps.api.outreach_endpoint import router as outreach_router  # noqa: E402
from apps.api.stripe_endpoint import router as stripe_router  # noqa: E402
from packages.schemas.approval import ApprovalStatus  # noqa: E402
from packages.schemas.task_packet import RiskLevel, TaskStatus, WorkerLane  # noqa: E402

app = FastAPI(title="ai-company-os control plane", version="0.1.0")
# Phase 3.1 — magic-link approval endpoint, mounted under /magic/approvals to
# avoid colliding with the existing JSON /approvals surface.
app.include_router(approval_router, prefix="/magic")
# D3 — operator dashboard's first panel: the read-only discovery view.
app.include_router(discovery_router)
app.include_router(dashboard_router)
# Outreach action panel — per-prospect launch buttons, human-gated sends.
app.include_router(outreach_router)
# G1 — local receiver for Stripe events forwarded by the Netlify webhook.
app.include_router(stripe_router)


class CreateGoalRequest(BaseModel):
    title: str
    summary: str
    description: str = ""
    parent_goal_id: str | None = None


class CreateTaskRequest(BaseModel):
    repo_id: str
    lane: WorkerLane
    title: str
    summary: str
    task_type: str
    risk_level: RiskLevel = RiskLevel.LOW
    product_id: str | None = None
    requires_approval: bool = False
    constraints: list[str] = Field(default_factory=list)


class ClaimTaskRequest(BaseModel):
    lane: WorkerLane
    worker_id: str


class SubmitTaskResultRequest(BaseModel):
    status: TaskStatus
    summary: str
    worker_id: str
    approval_id: str | None = None


class RequestApprovalBody(BaseModel):
    summary: str
    subject_type: str
    subject_id: str
    action: str
    approval_type: str
    task_id: str | None = None
    task_run_id: str | None = None
    review_artifact_path: str | None = None


class DecideApprovalBody(BaseModel):
    status: ApprovalStatus
    decided_by: str
    decision_notes: str = ""


def get_service() -> ControlPlaneService:
    return ControlPlaneService()


@app.get("/health")
def health() -> dict[str, object]:
    return get_service().health()


@app.post("/goals")
def create_goal(body: CreateGoalRequest) -> dict[str, object]:
    goal = get_service().create_goal(**body.model_dump())
    return as_payload(goal)


@app.get("/goals")
def list_goals() -> list[dict[str, object]]:
    return [as_payload(goal) for goal in get_service().list_goals()]


@app.post("/goals/{goal_id}/tasks")
def create_task(goal_id: str, body: CreateTaskRequest) -> dict[str, object]:
    try:
        task = get_service().create_task_for_goal(goal_id=goal_id, **body.model_dump())
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=f"Goal not found: {goal_id}") from exc
    return as_payload(task)


@app.get("/goals/{goal_id}/tasks")
def list_tasks(goal_id: str) -> list[dict[str, object]]:
    try:
        tasks = get_service().list_tasks_for_goal(goal_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=f"Goal not found: {goal_id}") from exc
    return [as_payload(task) for task in tasks]


@app.post("/tasks/claim")
def claim_task(body: ClaimTaskRequest) -> dict[str, object]:
    task = get_service().claim_task(**body.model_dump())
    if task is None:
        raise HTTPException(
            status_code=404,
            detail="No queued task available for the requested lane.",
        )
    return as_payload(task)


@app.post("/tasks/{task_id}/result")
def submit_task_result(task_id: str, body: SubmitTaskResultRequest) -> dict[str, object]:
    try:
        task = get_service().submit_task_result(task_id=task_id, **body.model_dump())
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=f"Task not found: {task_id}") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return as_payload(task)


@app.post("/approvals")
def request_approval(body: RequestApprovalBody) -> dict[str, object]:
    approval = get_service().request_approval(**body.model_dump())
    return as_payload(approval)


@app.post("/approvals/{approval_id}/decision")
def decide_approval(approval_id: str, body: DecideApprovalBody) -> dict[str, object]:
    try:
        approval = get_service().decide_approval(approval_id=approval_id, **body.model_dump())
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=f"Approval not found: {approval_id}") from exc
    return as_payload(approval)


@app.get("/events")
def list_events() -> list[dict[str, object]]:
    return [as_payload(event) for event in get_service().list_events()]


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("apps.api.main:app", host="127.0.0.1", port=8000, reload=False)
