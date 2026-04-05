from dataclasses import asdict, dataclass
from enum import Enum


class GoalStatus(str, Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass(frozen=True)
class GoalRecord:
    id: str
    title: str
    summary: str
    description: str = ""
    status: GoalStatus = GoalStatus.OPEN
    parent_goal_id: str | None = None
    created_at: str = ""
    updated_at: str = ""
    completed_at: str | None = None

    def to_dict(self) -> dict[str, object]:
        payload = asdict(self)
        payload["status"] = self.status.value
        return payload

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> "GoalRecord":
        return cls(
            id=str(payload["id"]),
            title=str(payload["title"]),
            summary=str(payload["summary"]),
            description=str(payload.get("description", "")),
            status=GoalStatus(str(payload.get("status", GoalStatus.OPEN.value))),
            parent_goal_id=(
                str(payload["parent_goal_id"]) if payload.get("parent_goal_id") else None
            ),
            created_at=str(payload.get("created_at", "")),
            updated_at=str(payload.get("updated_at", "")),
            completed_at=str(payload["completed_at"]) if payload.get("completed_at") else None,
        )
