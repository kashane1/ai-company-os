from dataclasses import asdict, dataclass
from enum import Enum


class ApprovalStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


@dataclass(frozen=True)
class ApprovalRecord:
    id: str
    status: ApprovalStatus
    summary: str
    created_at: str
    task_id: str | None = None
    task_run_id: str | None = None
    approval_type: str = ""
    review_artifact_path: str | None = None
    subject_type: str = "task_run"
    subject_id: str = ""
    action: str = ""
    decided_at: str | None = None
    decision_notes: str | None = None

    def to_dict(self) -> dict[str, object]:
        payload = asdict(self)
        payload["status"] = self.status.value
        return payload

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> "ApprovalRecord":
        return cls(
            id=str(payload["id"]),
            status=ApprovalStatus(str(payload["status"])),
            summary=str(payload["summary"]),
            created_at=str(payload["created_at"]),
            task_id=str(payload["task_id"]) if payload.get("task_id") else None,
            task_run_id=str(payload["task_run_id"]) if payload.get("task_run_id") else None,
            approval_type=str(payload.get("approval_type", "")),
            review_artifact_path=(
                str(payload["review_artifact_path"])
                if payload.get("review_artifact_path")
                else None
            ),
            subject_type=str(payload.get("subject_type", "task_run")),
            subject_id=str(payload.get("subject_id", "")),
            action=str(payload.get("action", "")),
            decided_at=str(payload["decided_at"]) if payload.get("decided_at") else None,
            decision_notes=(
                str(payload["decision_notes"]) if payload.get("decision_notes") else None
            ),
        )
