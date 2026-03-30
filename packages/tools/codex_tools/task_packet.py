from dataclasses import dataclass, field

from packages.schemas.testing import NoTestReasonCode, TestLane


@dataclass(frozen=True)
class CodexTaskPacket:
    task_id: str
    summary: str
    constraints: list[str] = field(default_factory=list)
    tests_required: bool = False
    test_lane: TestLane = TestLane.NONE
    allowed_no_test_reason_codes: list[NoTestReasonCode] = field(default_factory=list)


def render_markdown(packet: CodexTaskPacket) -> str:
    lines = [
        f"# Task {packet.task_id}",
        "",
        "## Objective",
        "",
        packet.summary,
        "",
        "## Execution Rules",
        "",
        "- Work only inside the provided isolated worktree.",
        "- Use the current repository contents as the source of truth.",
        "- Do not create commits, rewrite history, push branches, or open PRs.",
        "- Leave all file changes uncommitted for manual inspection.",
        "- Prefer the smallest change that satisfies the task.",
    ]
    if packet.constraints:
        lines.extend(["", "## Constraints"])
        lines.extend(f"- {constraint}" for constraint in packet.constraints)
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
