from __future__ import annotations

from dataclasses import dataclass
import re

from packages.db.task_store import TaskStore
from packages.schemas.task import Task
from packages.schemas.task_packet import TaskStatus, WorkerLane
from packages.schemas.testing import (
    NoTestReasonCode,
    TestLane,
    TestingPolicyResult,
    ValidationFailureCode,
)

OPEN_TASK_STATUSES = {
    TaskStatus.PENDING,
    TaskStatus.IN_PROGRESS,
    TaskStatus.BLOCKED,
}

TESTING_SECTION_HEADER = "## Testing"


@dataclass(frozen=True)
class ChangeRecord:
    status: str
    path: str
    previous_path: str | None = None

    @property
    def is_added(self) -> bool:
        return self.status == "A"

    @property
    def is_modified(self) -> bool:
        return self.status == "M"

    @property
    def is_created_or_modified(self) -> bool:
        return self.status in {"A", "M"}


@dataclass(frozen=True)
class TestingMetadata:
    summary: str
    no_test_reason_code: str | None = None
    followup_task_id: str | None = None


def test_lane_for_worker_lane(worker_lane: WorkerLane) -> TestLane:
    if worker_lane is WorkerLane.IOS:
        return TestLane.IOS
    if worker_lane is WorkerLane.ENGINEERING:
        return TestLane.PYTHON
    return TestLane.NONE


def logic_paths_for_lane(changes: list[ChangeRecord], lane: TestLane) -> list[str]:
    if lane is TestLane.PYTHON:
        return [
            change.path
            for change in changes
            if change.path.startswith(("apps/", "packages/")) and not is_test_path(change.path, lane)
        ]
    if lane is TestLane.IOS:
        return [
            change.path
            for change in changes
            if change.path.startswith("products/catchbook-ios/Sources/")
        ]
    return []


def relevant_test_paths_for_lane(changes: list[ChangeRecord], lane: TestLane) -> list[str]:
    return [
        change.path
        for change in changes
        if is_test_path(change.path, lane) and change.is_created_or_modified
    ]


def is_test_path(path: str, lane: TestLane) -> bool:
    if lane is TestLane.PYTHON:
        return path.startswith("tests/python/")
    if lane is TestLane.IOS:
        return path.startswith("products/catchbook-ios/Tests/")
    return False


def parse_git_status_lines(lines: list[str]) -> list[ChangeRecord]:
    changes: list[ChangeRecord] = []
    for line in lines:
        if not line.strip():
            continue
        status_token = line[:2]
        path_token = line[3:].strip()
        if "->" in path_token:
            previous_path, _, path = path_token.partition(" -> ")
            changes.append(
                ChangeRecord(
                    status=_normalize_short_status(status_token),
                    path=path.strip(),
                    previous_path=previous_path.strip(),
                )
            )
            continue
        changes.append(ChangeRecord(status=_normalize_short_status(status_token), path=path_token))
    return changes


def parse_name_status_lines(lines: list[str]) -> list[ChangeRecord]:
    changes: list[ChangeRecord] = []
    for line in lines:
        if not line.strip():
            continue
        parts = line.split("\t")
        status_token = parts[0]
        if status_token.startswith("R") and len(parts) >= 3:
            changes.append(ChangeRecord(status="R", path=parts[2], previous_path=parts[1]))
            continue
        if len(parts) >= 2:
            changes.append(ChangeRecord(status=_normalize_name_status(status_token), path=parts[1]))
    return changes


def parse_testing_metadata(markdown: str) -> TestingMetadata | None:
    lines = markdown.splitlines()
    in_section = False
    section_lines: list[str] = []
    for line in lines:
        if line.strip().startswith("## "):
            if in_section:
                break
            if line.strip().lower().startswith(TESTING_SECTION_HEADER.lower()):
                in_section = True
                continue
        if in_section:
            section_lines.append(line)
    if not in_section:
        return None

    summary = "\n".join(section_lines).strip()
    no_test_reason_match = re.search(r"\bno_test_reason_code\s*=\s*([a-z_]+)\b", summary)
    followup_task_match = re.search(r"\bfollowup_task_id\s*=\s*([A-Za-z0-9._:-]+)\b", summary)
    return TestingMetadata(
        summary=summary,
        no_test_reason_code=no_test_reason_match.group(1) if no_test_reason_match else None,
        followup_task_id=followup_task_match.group(1) if followup_task_match else None,
    )


def evaluate_testing_policy(
    *,
    lane: TestLane,
    changes: list[ChangeRecord],
    testing_metadata: TestingMetadata | None,
    current_task: Task | None = None,
    task_store: TaskStore | None = None,
) -> TestingPolicyResult:
    relevant_logic_paths = logic_paths_for_lane(changes, lane)
    relevant_test_paths = relevant_test_paths_for_lane(changes, lane)
    tests_required = bool(relevant_logic_paths)

    if testing_metadata is None or not testing_metadata.summary:
        return TestingPolicyResult(
            tests_required=tests_required,
            test_lane=lane if tests_required else TestLane.NONE,
            relevant_tests_changed=bool(relevant_test_paths),
            failure_code=ValidationFailureCode.MISSING_TESTING_METADATA,
            details="Codex result must include a ## Testing section with tests added or a valid no_test_reason_code.",
        )

    no_test_reason_code = _parse_no_test_reason_code(testing_metadata.no_test_reason_code)
    if testing_metadata.no_test_reason_code and no_test_reason_code is None:
        return TestingPolicyResult(
            tests_required=tests_required,
            test_lane=lane if tests_required else TestLane.NONE,
            relevant_tests_changed=bool(relevant_test_paths),
            failure_code=ValidationFailureCode.INVALID_NO_TEST_REASON_CODE,
            details=f"Unknown no_test_reason_code={testing_metadata.no_test_reason_code}.",
        )

    if not tests_required:
        return TestingPolicyResult(
            tests_required=False,
            test_lane=TestLane.NONE,
            relevant_tests_changed=bool(relevant_test_paths),
            no_test_reason_code=no_test_reason_code,
            followup_task_id=testing_metadata.followup_task_id,
            details="No logic-bearing files changed for this lane.",
        )

    if relevant_test_paths:
        return TestingPolicyResult(
            tests_required=True,
            test_lane=lane,
            relevant_tests_changed=True,
            no_test_reason_code=no_test_reason_code,
            followup_task_id=testing_metadata.followup_task_id,
            details=f"Relevant {lane.value} tests were created or modified.",
        )

    if no_test_reason_code is NoTestReasonCode.APPROVED_FOLLOWUP_TEST_TASK:
        if _is_valid_followup_test_task(
            followup_task_id=testing_metadata.followup_task_id,
            current_task=current_task,
            required_lane=lane,
            task_store=task_store,
        ):
            return TestingPolicyResult(
                tests_required=True,
                test_lane=lane,
                relevant_tests_changed=False,
                no_test_reason_code=no_test_reason_code,
                followup_task_id=testing_metadata.followup_task_id,
                details=f"Approved follow-up test task {testing_metadata.followup_task_id} is open and lane-matched.",
            )
        return TestingPolicyResult(
            tests_required=True,
            test_lane=lane,
            relevant_tests_changed=False,
            no_test_reason_code=no_test_reason_code,
            followup_task_id=testing_metadata.followup_task_id,
            failure_code=ValidationFailureCode.INVALID_FOLLOWUP_TEST_TASK_REFERENCE,
            details="approved_followup_test_task requires an open persisted task in the same lane and affected area.",
        )

    if no_test_reason_code in {
        NoTestReasonCode.COMMENTS_ONLY,
        NoTestReasonCode.VISUAL_ONLY_NON_LOGIC,
        NoTestReasonCode.CONFIG_NO_BEHAVIOR_CHANGE,
    }:
        return TestingPolicyResult(
            tests_required=True,
            test_lane=lane,
            relevant_tests_changed=False,
            no_test_reason_code=no_test_reason_code,
            followup_task_id=testing_metadata.followup_task_id,
            details=f"Explicit exception accepted via {no_test_reason_code.value}.",
        )

    return TestingPolicyResult(
        tests_required=True,
        test_lane=lane,
        relevant_tests_changed=False,
        failure_code=ValidationFailureCode.MISSING_TESTS_FOR_LOGIC_CHANGE,
        details=f"Logic-bearing {lane.value} files changed without matching created or modified tests.",
    )


def _parse_no_test_reason_code(raw_value: str | None) -> NoTestReasonCode | None:
    if raw_value is None:
        return None
    try:
        return NoTestReasonCode(raw_value)
    except ValueError:
        return None


def _normalize_short_status(status_token: str) -> str:
    token = status_token.strip()
    if token == "??":
        return "A"
    if "R" in token:
        return "R"
    if "D" in token and "A" not in token and "M" not in token:
        return "D"
    if "A" in token or "?" in token:
        return "A"
    if any(marker in token for marker in ("M", "T", "C", "U")):
        return "M"
    return token or "M"


def _normalize_name_status(status_token: str) -> str:
    if status_token.startswith("R"):
        return "R"
    if status_token.startswith("D"):
        return "D"
    if status_token.startswith("A"):
        return "A"
    return "M"


def _is_valid_followup_test_task(
    *,
    followup_task_id: str | None,
    current_task: Task | None,
    required_lane: TestLane,
    task_store: TaskStore | None,
) -> bool:
    if not followup_task_id or current_task is None:
        return False

    store = task_store or TaskStore()
    try:
        followup_task = store.load(followup_task_id)
    except FileNotFoundError:
        return False

    if followup_task.status not in OPEN_TASK_STATUSES:
        return False

    if test_lane_for_worker_lane(followup_task.lane) is not required_lane:
        return False

    if followup_task.repo_id != current_task.repo_id:
        return False

    if required_lane is TestLane.IOS and current_task.product_id != followup_task.product_id:
        return False

    return True
