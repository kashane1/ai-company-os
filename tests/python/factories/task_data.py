from packages.schemas.testing import NoTestReasonCode, TestLane
from packages.schemas.repo import RepoConfig, RepoRecord, RepoSyncStatus
from packages.schemas.task import Task
from packages.schemas.task_packet import RiskLevel, TaskPacket, TaskStatus, WorkerLane
from packages.schemas.worktree import WorktreeMetadata, WorktreeStatus


def build_task_packet(
    *,
    task_id: str = "task-123",
    goal_id: str = "goal-123",
    lane: WorkerLane = WorkerLane.ENGINEERING,
    title: str = "Implement task",
    summary: str = "Add automation safely",
    risk_level: RiskLevel = RiskLevel.LOW,
) -> TaskPacket:
    return TaskPacket(
        id=task_id,
        goal_id=goal_id,
        lane=lane,
        title=title,
        summary=summary,
        risk_level=risk_level,
        tests_required=lane in {WorkerLane.ENGINEERING, WorkerLane.IOS},
        test_lane=(
            TestLane.IOS
            if lane is WorkerLane.IOS
            else TestLane.PYTHON if lane is WorkerLane.ENGINEERING else TestLane.NONE
        ),
        allowed_no_test_reason_codes=[
            NoTestReasonCode.COMMENTS_ONLY,
            NoTestReasonCode.CONFIG_NO_BEHAVIOR_CHANGE,
        ],
    )


def build_task(
    *,
    task_id: str = "task-123",
    repo_id: str = "repo-123",
    lane: WorkerLane = WorkerLane.ENGINEERING,
    product_id: str | None = None,
    title: str = "Implement task",
    summary: str = "Add automation safely",
    task_type: str = "engineering_change",
    status: TaskStatus = TaskStatus.PENDING,
    risk_level: RiskLevel = RiskLevel.LOW,
    requires_approval: bool = False,
    constraints: list[str] | None = None,
) -> Task:
    return Task(
        id=task_id,
        repo_id=repo_id,
        lane=lane,
        product_id=product_id,
        title=title,
        summary=summary,
        task_type=task_type,
        status=status,
        risk_level=risk_level,
        requires_approval=requires_approval,
        constraints=constraints or [],
        created_at="2026-03-30T00:00:00+00:00",
        updated_at="2026-03-30T00:00:00+00:00",
    )


def build_repo_config(
    *,
    repo_id: str = "repo-123",
    source_path: str = "/tmp/source-repo",
    managed_repo_name: str = "managed-repo-123",
    default_branch: str = "main",
) -> RepoConfig:
    return RepoConfig(
        id=repo_id,
        name="Managed Repo",
        source_path=source_path,
        managed_repo_name=managed_repo_name,
        default_branch=default_branch,
    )


def build_repo_record(
    *,
    repo_id: str = "repo-123",
    source_path: str = "/tmp/source-repo",
    managed_path: str = "/tmp/managed-repo",
    default_branch: str = "main",
) -> RepoRecord:
    return RepoRecord(
        id=repo_id,
        name="Managed Repo",
        source_path=source_path,
        managed_path=managed_path,
        default_branch=default_branch,
        sync_status=RepoSyncStatus.READY,
        last_synced_at="2026-03-30T00:00:00+00:00",
    )


def build_worktree_metadata(root_path: str) -> WorktreeMetadata:
    return WorktreeMetadata(
        id="worktree-123",
        task_id="task-123",
        repo_id="repo-123",
        root_path=root_path,
        status=WorktreeStatus.PREPARED,
        created_at="2026-03-30T00:00:00+00:00",
        packet_path="packet.json",
    )
