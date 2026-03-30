from dataclasses import asdict, dataclass, field
from enum import Enum

from packages.schemas.testing import TestingPolicyResult
from packages.schemas.task_packet import WorkerLane


class TaskRunStatus(str, Enum):
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


@dataclass(frozen=True)
class ValidationCheck:
    name: str
    passed: bool
    details: str
    code: str | None = None

    def to_dict(self) -> dict[str, object]:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> "ValidationCheck":
        return cls(
            name=str(payload["name"]),
            passed=bool(payload["passed"]),
            details=str(payload["details"]),
            code=str(payload["code"]) if payload.get("code") else None,
        )


@dataclass(frozen=True)
class CodexExecutionRecord:
    command: list[str]
    command_display: str
    cwd: str
    stdout_path: str
    stderr_path: str
    exit_code: int
    started_at: str
    finished_at: str
    timed_out: bool = False

    def to_dict(self) -> dict[str, object]:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> "CodexExecutionRecord":
        return cls(
            command=list(payload["command"]),
            command_display=str(payload["command_display"]),
            cwd=str(payload["cwd"]),
            stdout_path=str(payload["stdout_path"]),
            stderr_path=str(payload["stderr_path"]),
            exit_code=int(payload["exit_code"]),
            started_at=str(payload["started_at"]),
            finished_at=str(payload["finished_at"]),
            timed_out=bool(payload.get("timed_out", False)),
        )


class EngineeringResultClassification(str, Enum):
    NO_CHANGE = "no_change"
    SAFE_FOR_REVIEW = "safe_for_review"
    VALIDATION_FAILED = "validation_failed"
    EXECUTION_FAILED = "execution_failed"


@dataclass(frozen=True)
class GitStateSnapshot:
    status_lines: list[str]
    changed_files: list[str]
    diff_summary: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> "GitStateSnapshot":
        return cls(
            status_lines=list(payload.get("status_lines", [])),
            changed_files=list(payload.get("changed_files", [])),
            diff_summary=str(payload.get("diff_summary", "")),
        )


@dataclass(frozen=True)
class TaskRun:
    id: str
    task_id: str
    worker_lane: WorkerLane
    repo_id: str
    worktree_id: str
    worktree_path: str
    packet_path: str
    execution_result_path: str
    execution: CodexExecutionRecord
    pre_run_git_state: GitStateSnapshot
    post_run_git_state: GitStateSnapshot
    diff_path: str
    classification: EngineeringResultClassification
    review_artifact_path: str
    approval_id: str | None
    status: TaskRunStatus
    summary: str
    started_at: str
    finished_at: str
    validation_checks: list[ValidationCheck] = field(default_factory=list)
    testing_policy: TestingPolicyResult | None = None
    failure_codes: list[str] = field(default_factory=list)
    artifacts: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        payload = asdict(self)
        payload["worker_lane"] = self.worker_lane.value
        payload["status"] = self.status.value
        payload["classification"] = self.classification.value
        payload["validation_checks"] = [check.to_dict() for check in self.validation_checks]
        payload["testing_policy"] = self.testing_policy.to_dict() if self.testing_policy else None
        return payload

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> "TaskRun":
        return cls(
            id=str(payload["id"]),
            task_id=str(payload["task_id"]),
            worker_lane=WorkerLane(str(payload["worker_lane"])),
            repo_id=str(payload["repo_id"]),
            worktree_id=str(payload["worktree_id"]),
            worktree_path=str(payload["worktree_path"]),
            packet_path=str(payload["packet_path"]),
            execution_result_path=str(payload["execution_result_path"]),
            execution=CodexExecutionRecord.from_dict(dict(payload["execution"])),
            pre_run_git_state=GitStateSnapshot.from_dict(dict(payload["pre_run_git_state"])),
            post_run_git_state=GitStateSnapshot.from_dict(dict(payload["post_run_git_state"])),
            diff_path=str(payload["diff_path"]),
            classification=EngineeringResultClassification(str(payload["classification"])),
            review_artifact_path=str(payload["review_artifact_path"]),
            approval_id=str(payload["approval_id"]) if payload.get("approval_id") else None,
            status=TaskRunStatus(str(payload["status"])),
            summary=str(payload["summary"]),
            started_at=str(payload["started_at"]),
            finished_at=str(payload["finished_at"]),
            validation_checks=[
                ValidationCheck.from_dict(item)
                for item in list(payload.get("validation_checks", []))
            ],
            testing_policy=TestingPolicyResult.from_dict(dict(payload["testing_policy"]))
            if payload.get("testing_policy")
            else None,
            failure_codes=list(payload.get("failure_codes", [])),
            artifacts=list(payload.get("artifacts", [])),
        )
