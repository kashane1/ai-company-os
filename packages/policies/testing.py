from __future__ import annotations

import re
from dataclasses import dataclass

from packages.db.task_store import TaskStore
from packages.schemas.task import Task
from packages.schemas.task_packet import TaskStatus, WorkerLane
from packages.schemas.testing import (
    NoTestReasonCode,
    TestingPolicyResult,
    TestLane,
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


@dataclass(frozen=True)
class SourceTestArea:
    name: str
    lane: TestLane
    source_roots: tuple[str, ...]
    source_suffixes: tuple[str, ...]
    test_roots: tuple[str, ...]
    test_suffixes: tuple[str, ...]

    def contains_source(self, path: str) -> bool:
        return path.startswith(self.source_roots) and path.endswith(self.source_suffixes)

    def contains_test(self, path: str) -> bool:
        return path.startswith(self.test_roots) and path.endswith(self.test_suffixes)


SOURCE_TEST_AREAS = (
    SourceTestArea(
        name="platform_python",
        lane=TestLane.PYTHON,
        source_roots=("apps/", "packages/"),
        source_suffixes=(".py",),
        test_roots=("tests/python/",),
        test_suffixes=(".py",),
    ),
    SourceTestArea(
        name="repository_scripts",
        lane=TestLane.PYTHON,
        source_roots=("scripts/",),
        source_suffixes=(".py", ".sh"),
        test_roots=("tests/python/",),
        test_suffixes=(".py",),
    ),
    SourceTestArea(
        name="after_plans_ios",
        lane=TestLane.IOS,
        source_roots=("products/after-plans-ios/Sources/",),
        source_suffixes=(".swift",),
        test_roots=(
            "products/after-plans-ios/Tests/",
            "products/after-plans-ios/UITests/",
        ),
        test_suffixes=(".swift",),
    ),
    SourceTestArea(
        name="catchbook_ios",
        lane=TestLane.IOS,
        source_roots=("products/catchbook-ios/Sources/",),
        source_suffixes=(".swift",),
        test_roots=(
            "products/catchbook-ios/Tests/",
            "products/catchbook-ios/UITests/",
        ),
        test_suffixes=(".swift",),
    ),
    SourceTestArea(
        name="life_clock_ios",
        lane=TestLane.IOS,
        source_roots=("products/life-clock-ios/Sources/",),
        source_suffixes=(".swift",),
        test_roots=(
            "products/life-clock-ios/Tests/",
            "products/life-clock-ios/UITests/",
        ),
        test_suffixes=(".swift",),
    ),
    SourceTestArea(
        name="better_business_web",
        lane=TestLane.WEB,
        source_roots=(
            "products/better-business-web/site/src/",
            "products/better-business-web/site/netlify/functions/",
            "products/better-business-web/portfolio/synapsex/src/",
        ),
        source_suffixes=(".astro", ".css", ".js", ".jsx", ".mjs", ".ts", ".tsx"),
        test_roots=(
            "products/better-business-web/tests/",
            "products/better-business-web/site/tests/",
            "products/better-business-web/portfolio/synapsex/tests/",
            "tests/web/better-business-web/",
        ),
        test_suffixes=(".js", ".jsx", ".mjs", ".py", ".ts", ".tsx"),
    ),
    SourceTestArea(
        name="pokemon_tcg_web",
        lane=TestLane.WEB,
        source_roots=("products/pokemon-tcg-search/web/",),
        source_suffixes=(".css", ".html", ".js"),
        test_roots=(
            "products/pokemon-tcg-search/tests/",
            "products/pokemon-tcg-search/web/tests/",
        ),
        test_suffixes=(".js", ".mjs", ".py", ".ts"),
    ),
)


def test_lane_for_worker_lane(worker_lane: WorkerLane) -> TestLane:
    if worker_lane is WorkerLane.IOS:
        return TestLane.IOS
    if worker_lane is WorkerLane.WEB:
        return TestLane.WEB
    if worker_lane is WorkerLane.ENGINEERING:
        return TestLane.PYTHON
    return TestLane.NONE


def logic_paths_for_lane(
    changes: list[ChangeRecord], lane: TestLane, source_root: str | None = None
) -> list[str]:
    areas = _areas_for_lane(lane, source_root=source_root)
    return [
        change.path
        for change in changes
        if any(area.contains_source(change.path) for area in areas)
    ]


def relevant_test_paths_for_lane(
    changes: list[ChangeRecord], lane: TestLane, source_root: str | None = None
) -> list[str]:
    affected_areas = _affected_areas(changes, lane, source_root=source_root)
    areas = affected_areas or _areas_for_lane(lane, source_root=source_root)
    return [
        change.path
        for change in changes
        if change.is_created_or_modified
        and any(area.contains_test(change.path) for area in areas)
    ]


def is_test_path(path: str, lane: TestLane, source_root: str | None = None) -> bool:
    return any(
        area.contains_test(path) for area in _areas_for_lane(lane, source_root=source_root)
    )


def _areas_for_lane(
    lane: TestLane, source_root: str | None = None
) -> tuple[SourceTestArea, ...]:
    areas = tuple(area for area in SOURCE_TEST_AREAS if area.lane is lane)
    standalone_areas = _standalone_areas_for_source_root(areas, source_root)
    return standalone_areas or areas


def _standalone_areas_for_source_root(
    areas: tuple[SourceTestArea, ...], source_root: str | None
) -> tuple[SourceTestArea, ...]:
    """Expose registered product-relative paths for a standalone worktree.

    Callers must derive ``source_root`` from the trusted repository registry's
    ``RepoConfig.source_path``. A managed checkout for Catchbook, for example,
    reports ``Sources/...`` rather than the monorepo's
    ``products/catchbook-ios/Sources/...``. The canonical roots remain accepted
    too, which keeps this mapping safe for callers that already have monorepo
    relative paths.
    """
    if not source_root:
        return ()

    normalized_root = source_root.replace("\\", "/").rstrip("/")
    standalone_areas: list[SourceTestArea] = []
    for area in areas:
        product_root = _product_root(area)
        if product_root is None or not _matches_source_root(normalized_root, product_root):
            continue

        relative_source_roots = tuple(
            source_root.removeprefix(product_root) for source_root in area.source_roots
        )
        relative_test_roots = tuple(
            test_root.removeprefix(product_root) for test_root in area.test_roots
        )
        standalone_areas.append(
            SourceTestArea(
                name=area.name,
                lane=area.lane,
                source_roots=area.source_roots + relative_source_roots,
                source_suffixes=area.source_suffixes,
                test_roots=area.test_roots + relative_test_roots,
                test_suffixes=area.test_suffixes,
            )
        )
    return tuple(standalone_areas)


def _product_root(area: SourceTestArea) -> str | None:
    marker = "/Sources/"
    source_root = area.source_roots[0]
    if marker not in source_root:
        return None
    return source_root.split(marker, maxsplit=1)[0] + "/"


def _matches_source_root(source_root: str, product_root: str) -> bool:
    canonical_root = product_root.rstrip("/")
    return source_root == canonical_root or source_root.endswith(f"/{canonical_root}")


def _affected_areas(
    changes: list[ChangeRecord], lane: TestLane, source_root: str | None = None
) -> tuple[SourceTestArea, ...]:
    return tuple(
        area
        for area in _areas_for_lane(lane, source_root=source_root)
        if any(area.contains_source(change.path) for change in changes)
    )


def _untested_areas(
    changes: list[ChangeRecord], lane: TestLane, source_root: str | None = None
) -> tuple[SourceTestArea, ...]:
    return tuple(
        area
        for area in _affected_areas(changes, lane, source_root=source_root)
        if not any(
            change.is_created_or_modified and area.contains_test(change.path)
            for change in changes
        )
    )


def parse_git_status_lines(lines: list[str]) -> list[ChangeRecord]:
    changes: list[ChangeRecord] = []
    for line in lines:
        if not line.strip():
            continue
        status_token = line[:2]
        raw_status = status_token.strip()
        if ("R" in raw_status or "C" in raw_status) and line[2:].startswith("\t"):
            _, previous_path, path = line.split("\t", maxsplit=2)
            changes.append(
                ChangeRecord(
                    status=_normalize_short_status(status_token),
                    path=path,
                    previous_path=previous_path,
                )
            )
            continue
        path_token = line[3:].strip()
        status = _normalize_short_status(status_token)
        if status == "R" and " -> " in path_token:
            previous_path, _, path = path_token.partition(" -> ")
            changes.append(
                ChangeRecord(
                    status=status,
                    path=path.strip(),
                    previous_path=previous_path.strip(),
                )
            )
            continue
        changes.append(ChangeRecord(status=status, path=path_token))
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
    source_root: str | None = None,
) -> TestingPolicyResult:
    relevant_logic_paths = logic_paths_for_lane(changes, lane, source_root=source_root)
    relevant_test_paths = relevant_test_paths_for_lane(changes, lane, source_root=source_root)
    tests_required = bool(relevant_logic_paths)
    untested_areas = _untested_areas(changes, lane, source_root=source_root)
    all_affected_areas_tested = tests_required and not untested_areas

    if testing_metadata is None or not testing_metadata.summary:
        return TestingPolicyResult(
            tests_required=tests_required,
            test_lane=lane if tests_required else TestLane.NONE,
            relevant_tests_changed=all_affected_areas_tested,
            failure_code=ValidationFailureCode.MISSING_TESTING_METADATA,
            details="Codex result must include a ## Testing section with tests added or a valid no_test_reason_code.",
        )

    no_test_reason_code = _parse_no_test_reason_code(testing_metadata.no_test_reason_code)
    if testing_metadata.no_test_reason_code and no_test_reason_code is None:
        return TestingPolicyResult(
            tests_required=tests_required,
            test_lane=lane if tests_required else TestLane.NONE,
            relevant_tests_changed=all_affected_areas_tested,
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

    if all_affected_areas_tested:
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
        details=(
            f"Logic-bearing {lane.value} files changed without matching created or "
            f"modified tests for: {', '.join(area.name for area in untested_areas)}."
        ),
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

    if required_lane in {TestLane.IOS, TestLane.WEB} and (
        current_task.product_id != followup_task.product_id
    ):
        return False

    return True
