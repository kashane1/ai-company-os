from dataclasses import dataclass, field
from enum import Enum

from packages.schemas.testing import NoTestReasonCode, TestLane


class WorkerLane(str, Enum):
    SUPERVISOR = "supervisor"
    ENGINEERING = "engineering"
    IOS = "ios"
    APPSTORE = "appstore"
    GTM = "gtm"
    # Phase 3 — skill self-evolution worker lane. Proposes patches to
    # canonical skills as structured diffs; never auto-applies. Gated by
    # packages/policies/skill_evolution.py and a human-signed HMAC
    # approval token issued through packages/tools/primitives/approvals.py.
    SKILL_EVOLUTION = "skill_evolution"
    # Section F — web build/ship lanes. WEB implements the site (Codex writes
    # frontend code, web validators check it); WEBDEPLOY publishes the built
    # artifact to a host. They are deliberately separate, mirroring the
    # IOS ↔ APPSTORE split: building a site and putting it in front of the
    # public are different actions with different blast radius. Production
    # deploys / DNS / spend are gated in packages/policies/deploy_readiness.py.
    WEB = "web"
    WEBDEPLOY = "webdeploy"


# Phase 2.1 — GTM task types. These are referenced by task.task_type (the
# string field on Task), not the lane enum. A single GTM worker handles all
# of them.
GTM_TASK_TYPES = frozenset(
    {
        "CONTENT_DRAFT",
        "CONTENT_IMAGE_GEN",
        "SOCIAL_POST_SCHEDULE",
        "GTM_CAMPAIGN_BRIEF",
        "ASO_METADATA_REFRESH",
    }
)

# Phase 5.2 — strategic task types (enum additions only; no new worker).
STRATEGIC_TASK_TYPES = frozenset(
    {
        "PRODUCT_BRIEF_UPDATE",
        "MVP_SPEC_UPDATE",
        "APPSTORE_POSITIONING_REFRESH",
        "APPSTORE_METADATA_DRAFT",
        "SCREENSHOT_PLAN_REFRESH",
        "ARTIFACT_CHAIN_REVIEW",
        "FOUNDER_BRIEF_INTAKE",
        "GTM_CAMPAIGN_BRIEF",
        "FAILURE_REGRESSION_FIXTURE",
    }
)


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
