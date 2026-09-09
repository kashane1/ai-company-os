from dataclasses import asdict, dataclass, field
from enum import Enum


class RepoSyncStatus(str, Enum):
    PENDING = "pending"
    READY = "ready"
    FAILED = "failed"


@dataclass(frozen=True)
class VerificationCommand:
    argv: list[str]
    cwd: str = "."
    timeout_seconds: float = 600

    def __post_init__(self) -> None:
        if not self.argv or not all(isinstance(arg, str) and arg for arg in self.argv):
            raise ValueError("Verification argv must contain nonempty strings")
        if not 0 < self.timeout_seconds <= 3600:
            raise ValueError("Verification timeout must be between 0 and 3600 seconds")


@dataclass(frozen=True)
class RepoConfig:
    id: str
    name: str
    source_path: str
    managed_repo_name: str
    default_branch: str = "main"
    verification: dict[str, list[VerificationCommand]] = field(default_factory=dict)

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
