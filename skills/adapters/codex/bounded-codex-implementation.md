# Bounded Codex Implementation — Codex Adapter

Canonical source: `skills/canonical/shared/bounded-codex-implementation.md`

This file documents how the engineering worker translates the canonical
`bounded-codex-implementation` skill into a Codex CLI invocation.

Codex does not read this file at runtime. The engineering worker uses
the canonical definition to:

1. Create the isolated worktree at `state/worktrees/<repo-id>/<task-id>/`
2. Render a `TASK_PACKET.md` inside the worktree with:
   - task objective
   - execution rules (no commits, worktree-only edits)
   - explicit constraints from the task record
3. Invoke `codex exec` with:
   - working directory: the worktree
   - stdin: the task packet
   - sandbox mode: workspace-write
4. Capture stdout, stderr, exit code, timestamps
5. Generate diff artifact at `state/artifacts/engineering/<task-id>/diff.patch`
6. Validate and persist the task run record

The task packet format follows the template in the canonical definition.
The engineering worker is responsible for all orchestration around Codex.
Codex only sees the rendered task packet.
