from dataclasses import dataclass, field


@dataclass(frozen=True)
class CodexTaskPacket:
    task_id: str
    summary: str
    constraints: list[str] = field(default_factory=list)


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
    return "\n".join(lines)
