from dataclasses import asdict, dataclass
from enum import Enum


class WorktreeStatus(str, Enum):
    PREPARED = "prepared"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass(frozen=True)
class WorktreeMetadata:
    id: str
    task_id: str
    repo_id: str
    root_path: str
    status: WorktreeStatus
    created_at: str
    packet_path: str = ""
    validated_at: str = ""

    def to_dict(self) -> dict[str, object]:
        payload = asdict(self)
        payload["status"] = self.status.value
        return payload

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> "WorktreeMetadata":
        return cls(
            id=str(payload["id"]),
            task_id=str(payload["task_id"]),
            repo_id=str(payload["repo_id"]),
            root_path=str(payload["root_path"]),
            status=WorktreeStatus(str(payload["status"])),
            created_at=str(payload["created_at"]),
            packet_path=str(payload.get("packet_path", "")),
            validated_at=str(payload.get("validated_at", "")),
        )
