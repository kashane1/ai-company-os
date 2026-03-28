from dataclasses import asdict, dataclass, field
from enum import Enum


class BuildStatus(str, Enum):
    DRAFT = "draft"
    READY = "ready"


class MetadataStatus(str, Enum):
    DRAFT = "draft"
    READY = "ready"


class ScreenshotStatus(str, Enum):
    DRAFT = "draft"
    READY = "ready"


class StoreChannelStatus(str, Enum):
    NOT_STARTED = "not_started"
    READY = "ready"
    APPROVAL_REQUIRED = "approval_required"
    APPROVED = "approved"


class ReleaseStatus(str, Enum):
    DRAFT = "draft"
    READY_FOR_REVIEW = "ready_for_review"
    BLOCKED = "blocked"


@dataclass(frozen=True)
class BuildCandidate:
    id: str
    product_id: str
    repo_id: str
    source_task_run_id: str
    version: str
    build_number: str
    artifact_paths: list[str] = field(default_factory=list)
    status: BuildStatus = BuildStatus.DRAFT
    created_at: str = ""

    def to_dict(self) -> dict[str, object]:
        payload = asdict(self)
        payload["status"] = self.status.value
        return payload

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> "BuildCandidate":
        return cls(
            id=str(payload["id"]),
            product_id=str(payload["product_id"]),
            repo_id=str(payload["repo_id"]),
            source_task_run_id=str(payload["source_task_run_id"]),
            version=str(payload["version"]),
            build_number=str(payload["build_number"]),
            artifact_paths=list(payload.get("artifact_paths", [])),
            status=BuildStatus(str(payload.get("status", BuildStatus.DRAFT.value))),
            created_at=str(payload.get("created_at", "")),
        )


@dataclass(frozen=True)
class MetadataDraft:
    id: str
    product_id: str
    locale: str
    path: str
    status: MetadataStatus = MetadataStatus.DRAFT
    created_at: str = ""

    def to_dict(self) -> dict[str, object]:
        payload = asdict(self)
        payload["status"] = self.status.value
        return payload

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> "MetadataDraft":
        return cls(
            id=str(payload["id"]),
            product_id=str(payload["product_id"]),
            locale=str(payload["locale"]),
            path=str(payload["path"]),
            status=MetadataStatus(str(payload.get("status", MetadataStatus.DRAFT.value))),
            created_at=str(payload.get("created_at", "")),
        )


@dataclass(frozen=True)
class ScreenshotSet:
    id: str
    product_id: str
    locale: str
    device_family: str
    asset_paths: list[str] = field(default_factory=list)
    status: ScreenshotStatus = ScreenshotStatus.DRAFT
    created_at: str = ""

    def to_dict(self) -> dict[str, object]:
        payload = asdict(self)
        payload["status"] = self.status.value
        return payload

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> "ScreenshotSet":
        return cls(
            id=str(payload["id"]),
            product_id=str(payload["product_id"]),
            locale=str(payload["locale"]),
            device_family=str(payload["device_family"]),
            asset_paths=list(payload.get("asset_paths", [])),
            status=ScreenshotStatus(str(payload.get("status", ScreenshotStatus.DRAFT.value))),
            created_at=str(payload.get("created_at", "")),
        )


@dataclass(frozen=True)
class ReleaseRecord:
    id: str
    product_id: str
    build_candidate_id: str
    metadata_draft_id: str
    screenshot_set_id: str
    testflight_status: StoreChannelStatus = StoreChannelStatus.NOT_STARTED
    appstore_status: StoreChannelStatus = StoreChannelStatus.NOT_STARTED
    status: ReleaseStatus = ReleaseStatus.DRAFT
    created_at: str = ""
    updated_at: str = ""

    def to_dict(self) -> dict[str, object]:
        payload = asdict(self)
        payload["testflight_status"] = self.testflight_status.value
        payload["appstore_status"] = self.appstore_status.value
        payload["status"] = self.status.value
        return payload

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> "ReleaseRecord":
        return cls(
            id=str(payload["id"]),
            product_id=str(payload["product_id"]),
            build_candidate_id=str(payload["build_candidate_id"]),
            metadata_draft_id=str(payload["metadata_draft_id"]),
            screenshot_set_id=str(payload["screenshot_set_id"]),
            testflight_status=StoreChannelStatus(
                str(payload.get("testflight_status", StoreChannelStatus.NOT_STARTED.value))
            ),
            appstore_status=StoreChannelStatus(
                str(payload.get("appstore_status", StoreChannelStatus.NOT_STARTED.value))
            ),
            status=ReleaseStatus(str(payload.get("status", ReleaseStatus.DRAFT.value))),
            created_at=str(payload.get("created_at", "")),
            updated_at=str(payload.get("updated_at", "")),
        )
