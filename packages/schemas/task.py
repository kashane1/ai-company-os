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
            created_at=str(payload.get("created_at", "")),
            updated_at=str(payload.get("updated_at", "")),
        )
