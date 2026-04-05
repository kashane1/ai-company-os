from dataclasses import asdict, dataclass, field


@dataclass(frozen=True)
class EventRecord:
    id: str
    event_type: str
    subject_type: str
    subject_id: str
    created_at: str
    goal_id: str | None = None
    task_id: str | None = None
    approval_id: str | None = None
    payload: dict[str, object] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> "EventRecord":
        return cls(
            id=str(payload["id"]),
            event_type=str(payload["event_type"]),
            subject_type=str(payload["subject_type"]),
            subject_id=str(payload["subject_id"]),
            created_at=str(payload["created_at"]),
            goal_id=str(payload["goal_id"]) if payload.get("goal_id") else None,
            task_id=str(payload["task_id"]) if payload.get("task_id") else None,
            approval_id=str(payload["approval_id"]) if payload.get("approval_id") else None,
            payload=dict(payload.get("payload", {})),
        )
