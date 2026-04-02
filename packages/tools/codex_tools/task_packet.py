from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
import re

from packages.schemas.task import Task
from packages.schemas.testing import NoTestReasonCode, TestLane
from packages.tools.ios_tools.xcode import default_build_command, detect_project_reference

STANDARD_RULES = [
    "Work only inside this worktree.",
    "Do not modify files outside the repository root.",
    "Do not commit or push.",
    "Leave changes uncommitted for inspection.",
    "Do not add dependencies without explicit constraint approval.",
    "Do not modify test fixtures unless the task objective requires it.",
]

PATH_PATTERN = re.compile(r"(?:[A-Za-z0-9_.-]+/)+[A-Za-z0-9_.-]+(?:\.[A-Za-z0-9_.-]+)?")


class PacketPattern(str, Enum):
    IMPLEMENTATION = "implementation"
    BUGFIX = "bugfix"
    VALIDATION = "validation"
    UI_POLISH = "ui-polish"
    HANDOFF_SAFE = "handoff-safe"


@dataclass(frozen=True)
class CodexTaskPacket:
    task_id: str
    title: str
    objective: str
    pattern: PacketPattern
    constraints: list[str] = field(default_factory=list)
    context_files: list[str] = field(default_factory=list)
    target_files: list[str] = field(default_factory=list)
    acceptance_criteria: list[str] = field(default_factory=list)
    verification_commands: list[str] = field(default_factory=list)
    review_findings: list[str] = field(default_factory=list)
    reproduction_steps: list[str] = field(default_factory=list)
    expected_behavior: str = ""
    actual_behavior: str = ""
    root_cause_hypothesis: str = ""
    coverage_current: str = ""
    coverage_goal: str = ""
    handoff_target: str = ""
    output_contract: list[str] = field(default_factory=list)
    extra_rules: list[str] = field(default_factory=list)
    do_not: list[str] = field(default_factory=list)
    tests_required: bool = False
    test_lane: TestLane = TestLane.NONE
    allowed_no_test_reason_codes: list[NoTestReasonCode] = field(default_factory=list)


def select_packet_pattern(task: Task) -> PacketPattern:
    haystack = " ".join([task.title, task.summary, task.task_type, *task.constraints]).lower()

    if any(keyword in haystack for keyword in ("handoff", "testflight", "app store", "appstore")):
        return PacketPattern.HANDOFF_SAFE
    if any(
        keyword in haystack
        for keyword in (
            "ui polish",
            "polish",
            "layout",
            "spacing",
            "alignment",
            "accessibility",
            "voiceover",
            "dynamic type",
            "dark mode",
        )
    ):
        return PacketPattern.UI_POLISH
    if any(keyword in haystack for keyword in ("validation", "test", "tests", "lint", "coverage")):
        return PacketPattern.VALIDATION
    if any(keyword in haystack for keyword in ("bug", "bugfix", "fix", "defect", "regression", "crash")):
        return PacketPattern.BUGFIX
    return PacketPattern.IMPLEMENTATION


def build_task_packet(
    task: Task,
    *,
    worktree_root: str,
    test_lane: TestLane,
    allowed_no_test_reason_codes: list[NoTestReasonCode],
    lane_constraints: list[str] | None = None,
) -> CodexTaskPacket:
    worktree_path = Path(worktree_root)
    pattern = select_packet_pattern(task)
    context_files, target_files = infer_packet_paths(task, worktree_path, pattern)
    verification_commands = infer_verification_commands(task, worktree_path, pattern)

    constraints = [*(lane_constraints or []), *task.constraints]
    acceptance_criteria = build_acceptance_criteria(task, pattern)
    review_findings = build_review_findings(task, pattern)
    reproduction_steps, expected_behavior, actual_behavior, root_cause = build_bugfix_details(task, pattern)
    coverage_current, coverage_goal = build_validation_details(task, pattern)
    handoff_target, output_contract, do_not = build_handoff_details(task, pattern)

    return CodexTaskPacket(
        task_id=task.id,
        title=task.title,
        objective=task.summary,
        pattern=pattern,
        constraints=constraints,
        context_files=context_files,
        target_files=target_files,
        acceptance_criteria=acceptance_criteria,
        verification_commands=verification_commands,
        review_findings=review_findings,
        reproduction_steps=reproduction_steps,
        expected_behavior=expected_behavior,
        actual_behavior=actual_behavior,
        root_cause_hypothesis=root_cause,
        coverage_current=coverage_current,
        coverage_goal=coverage_goal,
        handoff_target=handoff_target,
        output_contract=output_contract,
        do_not=do_not,
        tests_required=True,
        test_lane=test_lane,
        allowed_no_test_reason_codes=allowed_no_test_reason_codes,
    )


def render_markdown(packet: CodexTaskPacket) -> str:
    lines = [
        f"# Task: {packet.title}",
        "",
        "## Packet Metadata",
        "",
        f"- task_id={packet.task_id}",
        f"- pattern={packet.pattern.value}",
        "",
        "## Objective",
        "",
        packet.objective,
    ]

    if packet.pattern is PacketPattern.BUGFIX:
        lines.extend(
            [
                "",
                "## Reproduction",
                "",
                *[f"{index}. {step}" for index, step in enumerate(packet.reproduction_steps, start=1)],
                "",
                f"**Expected**: {packet.expected_behavior}",
                f"**Actual**: {packet.actual_behavior}",
                "",
                "## Root cause hypothesis",
                "",
                packet.root_cause_hypothesis,
            ]
        )

    if packet.pattern is PacketPattern.UI_POLISH:
        lines.extend(["", "## Review findings to address", ""])
        lines.extend(f"- {finding}" for finding in packet.review_findings)

    if packet.pattern is PacketPattern.VALIDATION:
        lines.extend(
            [
                "",
                "## Coverage target",
                "",
                f"- Current: {packet.coverage_current}",
                f"- Goal: {packet.coverage_goal}",
            ]
        )

    if packet.pattern is PacketPattern.HANDOFF_SAFE:
        lines.extend(
            [
                "",
                "## Handoff context",
                "",
                f"This task's output will be consumed by the **{packet.handoff_target}** worker.",
                "The output must be self-contained and not require follow-up engineering work to be usable.",
                "",
                "## Output contract",
                "",
            ]
        )
        lines.extend(f"- {item}" for item in packet.output_contract)

    if packet.context_files:
        lines.extend(["", "## Context", "", "Read these files before starting:"])
        lines.extend(f"- {path}" for path in packet.context_files)

    if packet.target_files:
        lines.extend(["", "## Target files", "", "Expected to create or modify:"])
        lines.extend(f"- {path}" for path in packet.target_files)

    lines.extend(["", "## Rules", ""])
    lines.extend(f"- {rule}" for rule in STANDARD_RULES)
    lines.extend(f"- {rule}" for rule in packet.extra_rules)

    if packet.do_not:
        lines.extend(["", "## Do not", ""])
        lines.extend(f"- {rule}" for rule in packet.do_not)

    if packet.constraints:
        lines.extend(["", "## Constraints", ""])
        lines.extend(f"- {constraint}" for constraint in packet.constraints)

    if packet.verification_commands:
        heading = "## Validation commands" if packet.pattern is PacketPattern.VALIDATION else "## Verification"
        intro = "Run after changes:" if packet.pattern is PacketPattern.VALIDATION else "Run after changes (if applicable):"
        lines.extend(["", heading, "", intro])
        lines.extend(f"- {command}" for command in packet.verification_commands)

    if packet.acceptance_criteria:
        lines.extend(["", "## Acceptance criteria", ""])
        lines.extend(f"- {criterion}" for criterion in packet.acceptance_criteria)

    lines.extend(
        [
            "",
            "## Testing Contract",
            "",
            f"- tests_required={'true' if packet.tests_required else 'false'}",
            f"- test_lane={packet.test_lane.value}",
            "- Every logic-bearing change must ship with created or modified lane-matching tests unless a valid exception applies.",
            "- Your final message must include a `## Testing` section.",
            "- In that section, either list tests added or updated, or include `no_test_reason_code=<enum>` with a short reason.",
            "- If you use `approved_followup_test_task`, also include `followup_task_id=<task-id>`.",
        ]
    )
    if packet.allowed_no_test_reason_codes:
        allowed_codes = ", ".join(code.value for code in packet.allowed_no_test_reason_codes)
        lines.append(f"- allowed_no_test_reason_codes={allowed_codes}")
    return "\n".join(lines)


def infer_packet_paths(task: Task, worktree_root: Path, pattern: PacketPattern) -> tuple[list[str], list[str]]:
    explicit_paths = extract_existing_paths(task, worktree_root)
    if explicit_paths:
        context_files = explicit_paths[:4]
        target_files = explicit_paths[:3]
        if pattern is PacketPattern.VALIDATION:
            target_files = [path for path in explicit_paths if "test" in path.lower()] or target_files
        return context_files, target_files

    if task.lane.value == "ios":
        project_reference = detect_project_reference(worktree_root)
        context_files = [path for path in ["Sources/", "Tests/"] if (worktree_root / path).exists()]
        if project_reference:
            context_files.append(project_reference)
        target_files = ["Tests/"] if pattern is PacketPattern.VALIDATION else ["Sources/"]
        if pattern is PacketPattern.UI_POLISH:
            target_files = ["Sources/"]
        return context_files, target_files

    if pattern is PacketPattern.VALIDATION:
        return ["tests/python/", "apps/", "packages/"], ["tests/python/"]

    default_targets = ["apps/", "packages/"]
    if any(path.startswith("docs/") for path in task.constraints) or "docs/" in task.summary:
        default_targets = ["docs/"]
    return default_targets, default_targets[:]


def infer_verification_commands(task: Task, worktree_root: Path, pattern: PacketPattern) -> list[str]:
    if task.lane.value == "ios":
        project_reference = detect_project_reference(worktree_root)
        return [default_build_command(project_reference)] if project_reference else []

    if pattern is PacketPattern.VALIDATION:
        return ["python3 -m pytest tests/python"]
    if "docs/" in task.summary.lower():
        return ["No additional verification command required for docs-only scope."]
    return ["python3 -m pytest tests/python"]


def build_acceptance_criteria(task: Task, pattern: PacketPattern) -> list[str]:
    criteria = [
        "Satisfy the task objective exactly as written.",
        "Keep the change scoped to the files and areas called out above.",
        "Update lane-matching tests or provide a valid `no_test_reason_code` in the final message.",
    ]
    if pattern is PacketPattern.BUGFIX:
        criteria[0] = "The reported defect is resolved without refactoring unrelated code."
    if pattern is PacketPattern.VALIDATION:
        criteria[0] = "The requested validation coverage or check is added or repaired."
    if pattern is PacketPattern.UI_POLISH:
        criteria[0] = "The listed polish issues are addressed without changing underlying behavior."
    if pattern is PacketPattern.HANDOFF_SAFE:
        criteria[0] = "The output is complete and self-contained for the downstream worker."
    if task.lane.value == "ios":
        criteria.append("Preserve current iOS lane boundaries and avoid release automation changes.")
    return criteria


def build_review_findings(task: Task, pattern: PacketPattern) -> list[str]:
    if pattern is not PacketPattern.UI_POLISH:
        return []
    findings = [task.summary]
    findings.extend(task.constraints)
    return findings


def build_bugfix_details(task: Task, pattern: PacketPattern) -> tuple[list[str], str, str, str]:
    if pattern is not PacketPattern.BUGFIX:
        return [], "", "", ""
    return (
        [
            "Reproduce the bug described in the task before changing code.",
            "Inspect the context files to confirm the failing path and affected behavior.",
            "Verify the issue no longer occurs after the fix and that the change stays minimal.",
        ],
        f"The behavior described in the task summary is corrected: {task.summary}",
        f"The current task report indicates incorrect behavior or drift: {task.summary}",
        "Confirm the root cause from the code before changing adjacent logic. If the initial theory is wrong, follow the actual cause and keep the fix narrowly scoped.",
    )


def build_validation_details(task: Task, pattern: PacketPattern) -> tuple[str, str]:
    if pattern is not PacketPattern.VALIDATION:
        return "", ""
    return (
        "Validation coverage or checks are incomplete for the area described in this task.",
        task.summary,
    )


def build_handoff_details(task: Task, pattern: PacketPattern) -> tuple[str, list[str], list[str]]:
    if pattern is not PacketPattern.HANDOFF_SAFE:
        return "", [], []

    if task.lane.value == "ios":
        target = "appstore"
    elif "ios" in task.summary.lower() or "ios" in task.title.lower():
        target = "ios"
    else:
        target = "downstream"

    return (
        target,
        [
            "No TODOs or deferred follow-up work remain in the touched files.",
            "The result can be reviewed or handed off without another scoping pass.",
            "Any required tests or valid test exceptions are included in the final message.",
        ],
        [
            "Include TODO comments that push completion to another worker.",
            "Leave partial implementations that require another Codex pass to be usable.",
            "Modify files outside the inferred target area unless the task summary makes that necessary.",
        ],
    )


def extract_existing_paths(task: Task, worktree_root: Path) -> list[str]:
    text = " ".join([task.title, task.summary, task.task_type, *task.constraints])
    discovered: list[str] = []
    for match in PATH_PATTERN.findall(text):
        candidate = match.rstrip(".,:;)")
        if (worktree_root / candidate).exists() and candidate not in discovered:
            discovered.append(candidate)
    return discovered
