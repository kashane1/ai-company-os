---
description: Reference for the engineering worker on how to select and render Codex task packets from the standard pattern library.
canonical_source: skills/canonical/shared/codex-task-packet-library.md
---

# Codex Task Packet Library — Engineering Worker Reference

This is a non-executable reference document. Codex does not read this file at runtime.

The engineering worker uses this alongside the canonical definition at `skills/canonical/shared/codex-task-packet-library.md` to select and render task packets.

## How the engineering worker uses this

1. Load the task record from `state/checkpoints/platform/tasks/<task-id>.json`
2. Determine the appropriate packet pattern based on the task type:
   - Feature work → `implementation`
   - Review findings → `ui-polish`
   - Defect fix → `bugfix`
   - Test/lint/build work → `validation`
   - Cross-lane output → `handoff-safe`
3. Read the pattern template from `skills/canonical/shared/codex-packet-patterns/<pattern>.md`
4. Fill in task-specific content (objective, constraints, context files, target files, acceptance)
5. Append the standard rules block (worktree-only, no commit, no push)
6. Write the rendered packet to `<worktree>/TASK_PACKET.md`
7. Pass the worktree path to `bounded-codex-implementation` for execution

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
