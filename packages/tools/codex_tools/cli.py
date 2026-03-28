from dataclasses import dataclass


@dataclass(frozen=True)
class CodexInvocation:
    task_id: str
    worktree_path: str
    instruction_path: str


def describe_invocation(invocation: CodexInvocation) -> str:
    return (
        f"Run Codex for task {invocation.task_id} in {invocation.worktree_path} "
        f"using {invocation.instruction_path}."
    )
