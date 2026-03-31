---
description: Reference for the engineering worker on how to select and render Codex task packets from the standard pattern library.
canonical_source: skills/canonical/shared/codex-task-packet-library.md
---

# Codex Task Packet Library — Engineering Worker Reference

This is a non-executable reference document. Codex does not read this file at runtime.

The engineering worker uses this alongside the canonical definition at `skills/canonical/shared/codex-task-packet-library.md` to select and render task packets.

## Current runtime status

The canonical packet library is only **partially implemented** in the current worker runtime.

- Current renderer: `packages/tools/codex_tools/task_packet.py`
- Current engineering entrypoint: `apps/worker-engineering/engineering/codex_runner.py`
- Current iOS entrypoint: `apps/worker-ios/ios/codex_runner.py`

What is real today:

- The worker does render a markdown packet before invoking Codex.
- The packet now lands at `<worktree>/TASK_PACKET.md`.
- The packet carries the objective, execution rules, task constraints, and structured testing contract fields.

What is not implemented yet:

- Pattern selection from `skills/canonical/shared/codex-packet-patterns/`
- Distinct packet shapes for `implementation`, `bugfix`, `ui-polish`, `validation`, and `handoff-safe`
- Explicit `Context`, `Target files`, `Verification`, and `Acceptance criteria` sections
- Worker-driven file targeting based on task scope

Treat the canonical library as a target contract. Treat the current renderer as the operational reality.

## How the engineering worker uses this

1. Load the task record from `state/checkpoints/platform/tasks/<task-id>.json`
2. Render the current packet shape from `packages/tools/codex_tools/task_packet.py`
3. Include task summary, constraints, and testing contract metadata
4. Write the packet to `<worktree>/TASK_PACKET.md`
5. Pass the worktree path to the Codex execution step

The pattern library below is the intended next shape, not the current one.

## Pattern selection guide

| Task has... | Use pattern |
|-------------|-------------|
| "Add", "Create", "Implement" in title | `implementation` |
| Review document reference | `ui-polish` |
| "Fix", "Bug", reproduction steps | `bugfix` |
| "Test", "Lint", "Coverage" in title | `validation` |
| Output consumed by another worker lane | `handoff-safe` |

## Path convention

All file paths in rendered packets must be **worktree-relative** (relative to the worktree root). For managed products, use the path as it appears inside the worktree, not the repo-root path.

## Standard rules (always included)

```
- Work only inside this worktree
- Do not modify files outside the repository root
- Do not commit or push
- Leave changes uncommitted for inspection
- Do not add dependencies without explicit constraint approval
- Do not modify test fixtures unless the task objective requires it
```

## Pattern templates

Located at `skills/canonical/shared/codex-packet-patterns/`:
- `implementation.md`
- `ui-polish.md`
- `bugfix.md`
- `validation.md`
- `handoff-safe.md`

These templates are not yet wired into the worker runtime.
