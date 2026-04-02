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

- The worker renders a markdown packet before invoking Codex.
- The packet lands at `<worktree>/TASK_PACKET.md`.
- Runtime selects from `implementation`, `bugfix`, `ui-polish`, `validation`, and `handoff-safe`.
- The rendered packet includes pattern-specific sections such as `Context`, `Target files`, `Verification`, and `Acceptance criteria`.
- The packet carries structured testing contract fields used by validation.

What is not implemented yet:

- Rich task metadata for exact context-file and target-file selection
- Review-document-aware UI polish packets with precise file:line findings
- Fully structured reproduction data and output contracts from persisted task schema

Treat the canonical library as a target contract. Treat the current renderer as the operational reality.

## How the engineering worker uses this

1. Load the task record from `state/checkpoints/platform/tasks/<task-id>.json`
2. Select a packet pattern from `packages/tools/codex_tools/task_packet.py`
3. Build the packet using task metadata, lane defaults, inferred context paths, and testing contract metadata
4. Write the packet to `<worktree>/TASK_PACKET.md`
5. Pass the worktree path to the Codex execution step

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

These templates are now reflected in runtime through a lightweight shared builder rather than a generic template engine.
