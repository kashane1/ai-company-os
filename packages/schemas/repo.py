from dataclasses import asdict, dataclass
from enum import Enum


class RepoSyncStatus(str, Enum):
    PENDING = "pending"
    READY = "ready"
    FAILED = "failed"


@dataclass(frozen=True)
class RepoConfig:
    id: str
    name: str
    source_path: str
    managed_repo_name: str
    default_branch: str = "main"

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class RepoRecord:
    id: str
    name: str
    source_path: str
    managed_path: str
    default_branch: str
    sync_status: RepoSyncStatus
    last_synced_at: str

    def to_dict(self) -> dict[str, object]:
        payload = asdict(self)
        payload["sync_status"] = self.sync_status.value
        return payload

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> "RepoRecord":
        return cls(
            id=str(payload["id"]),
            name=str(payload["name"]),
            source_path=str(payload["source_path"]),
            managed_path=str(payload["managed_path"]),
            default_branch=str(payload["default_branch"]),
            sync_status=RepoSyncStatus(str(payload["sync_status"])),
            last_synced_at=str(payload["last_synced_at"]),
        )
