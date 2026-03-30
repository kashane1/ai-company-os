from dataclasses import dataclass, field
from enum import Enum

from packages.schemas.testing import NoTestReasonCode, TestLane


class WorkerLane(str, Enum):
    SUPERVISOR = "supervisor"
    ENGINEERING = "engineering"
    IOS = "ios"
    APPSTORE = "appstore"


class TaskStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    BLOCKED = "blocked"
    COMPLETED = "completed"
    FAILED = "failed"


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass(frozen=True)
class Goal:
    id: str
    title: str
    summary: str


@dataclass(frozen=True)
class TaskPacket:
    id: str
    goal_id: str
    lane: WorkerLane
    title: str
    summary: str
    risk_level: RiskLevel = RiskLevel.LOW
    requires_approval: bool = False
    constraints: list[str] = field(default_factory=list)
    tests_required: bool = False
    test_lane: TestLane = TestLane.NONE
    allowed_no_test_reason_codes: list[NoTestReasonCode] = field(default_factory=list)


@dataclass(frozen=True)
class TaskResult:
    task_id: str
    status: TaskStatus
    summary: str
    run_id: str | None = None
    repo_id: str | None = None
    worktree_path: str | None = None
    classification: str | None = None
    review_artifact_path: str | None = None
    approval_id: str | None = None
    artifacts: list[str] = field(default_factory=list)
    validation_checks: list[str] = field(default_factory=list)
    failure_codes: list[str] = field(default_factory=list)
    next_actions: list[str] = field(default_factory=list)
