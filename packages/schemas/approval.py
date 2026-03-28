from dataclasses import asdict, dataclass
from enum import Enum


class ApprovalStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


@dataclass(frozen=True)
class ApprovalRecord:
    id: str
    task_id: str
    task_run_id: str
    status: ApprovalStatus
    approval_type: str
    summary: str
    review_artifact_path: str
    created_at: str

    def to_dict(self) -> dict[str, object]:
        payload = asdict(self)
        payload["status"] = self.status.value
        return payload

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> "ApprovalRecord":
        return cls(
            id=str(payload["id"]),
            task_id=str(payload["task_id"]),
            task_run_id=str(payload["task_run_id"]),
            status=ApprovalStatus(str(payload["status"])),
            approval_type=str(payload["approval_type"]),
            summary=str(payload["summary"]),
            review_artifact_path=str(payload["review_artifact_path"]),
            created_at=str(payload["created_at"]),
        )
