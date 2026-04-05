from dataclasses import asdict, dataclass, field

from packages.schemas.task_packet import RiskLevel, TaskStatus, WorkerLane


@dataclass(frozen=True)
class Task:
    id: str
    repo_id: str
    lane: WorkerLane
    title: str
    summary: str
    task_type: str
    product_id: str | None = None
    goal_id: str | None = None
    status: TaskStatus = TaskStatus.PENDING
    risk_level: RiskLevel = RiskLevel.LOW
    requires_approval: bool = False
    constraints: list[str] = field(default_factory=list)
    claimed_by: str | None = None
    claimed_at: str | None = None
    started_at: str | None = None
    completed_at: str | None = None
    failed_at: str | None = None
    result_summary: str | None = None
    error_summary: str | None = None
    approval_id: str | None = None
    created_at: str = ""
    updated_at: str = ""

    def to_dict(self) -> dict[str, object]:
        payload = asdict(self)
        payload["lane"] = self.lane.value
        payload["status"] = self.status.value
        payload["risk_level"] = self.risk_level.value
        return payload

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> "Task":
        return cls(
            id=str(payload["id"]),
            repo_id=str(payload["repo_id"]),
            lane=WorkerLane(str(payload["lane"])),
            title=str(payload["title"]),
            summary=str(payload["summary"]),
            task_type=str(payload["task_type"]),
            product_id=str(payload["product_id"]) if payload.get("product_id") else None,
            goal_id=str(payload["goal_id"]) if payload.get("goal_id") else None,
            status=TaskStatus(str(payload["status"])),
            risk_level=RiskLevel(str(payload["risk_level"])),
            requires_approval=bool(payload.get("requires_approval", False)),
            constraints=list(payload.get("constraints", [])),
            claimed_by=str(payload["claimed_by"]) if payload.get("claimed_by") else None,
            claimed_at=str(payload["claimed_at"]) if payload.get("claimed_at") else None,
            started_at=str(payload["started_at"]) if payload.get("started_at") else None,
            completed_at=str(payload["completed_at"]) if payload.get("completed_at") else None,
            failed_at=str(payload["failed_at"]) if payload.get("failed_at") else None,
            result_summary=str(payload["result_summary"])
            if payload.get("result_summary")
            else None,
            error_summary=str(payload["error_summary"])
            if payload.get("error_summary")
            else None,
            approval_id=str(payload["approval_id"]) if payload.get("approval_id") else None,
            created_at=str(payload.get("created_at", "")),
            updated_at=str(payload.get("updated_at", "")),
        )
