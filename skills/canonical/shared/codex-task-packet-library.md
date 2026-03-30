---
id: codex-task-packet-library
name: Codex Task Packet Library
purpose: Provide reusable packet patterns for common Codex task types so engineering workers render consistent, bounded task packets.
owner_agent: engineering
target_runtimes: [codex]
stage: active
inputs:
  - task record with type, objective, constraints, and target repo
  - packet pattern name (implementation, ui-polish, bugfix, validation, handoff-safe)
outputs:
  - rendered TASK_PACKET.md written to the task worktree
allowed_edit_boundaries:
  - state/worktrees/<repo-id>/<task-id>/TASK_PACKET.md
forbidden_areas:
  - packages/policies/
  - packages/schemas/
  - infra/
  - docs/
dependencies:
  - task must exist in state/checkpoints/platform/tasks/
  - repo must be synced to state/repos/<repo-id>/
  - worktree must exist at state/worktrees/<repo-id>/<task-id>/
validation_steps:
  - rendered packet follows the selected pattern structure
  - packet contains an objective section
  - packet contains explicit rules (worktree-only, no commit, no push)
  - packet contains constraints from the task record
  - packet does not include orchestration instructions or multi-lane work
handoff_contract:
  what_is_handed_off: path to rendered TASK_PACKET.md
  handed_to: bounded-codex-implementation skill for execution
codex_adaptation_notes: |
  This skill runs BEFORE Codex — it renders the packet that Codex will receive.
  The engineering worker uses this skill to select the right pattern and fill it
  with task-specific content. Codex never reads this skill file directly.
---

## Instructions

### 1. Select the packet pattern

Based on the task record's type or objective, select one of the standard patterns:

| Pattern | Use when |
|---------|----------|
| `implementation` | Adding a new feature, screen, model, or API endpoint |
| `ui-polish` | Fixing layout, styling, accessibility, or platform convention issues |
| `bugfix` | Fixing a specific reported defect with known reproduction |
| `validation` | Adding or fixing tests, lint rules, or build checks |
| `handoff-safe` | Task output will be handed to another worker lane — extra boundary strictness |

### 2. Render the packet

Use the selected pattern template from `skills/canonical/shared/codex-packet-patterns/` as the skeleton. Fill in:

- **Objective**: from the task record's title and summary
- **Constraints**: from the task record's constraints list
- **Context files**: key files Codex should read before editing (the engineering worker selects these based on the task scope and repo knowledge — they are not part of the task record)
- **Target files**: files Codex is expected to modify (same — selected by the engineering worker)
- **Acceptance criteria**: from the task record

**Path convention**: All file paths in the packet must be relative to the worktree root. When the engineering worker renders a packet for a managed product, use paths as they appear inside the worktree (e.g. `FishingLogbook/Views/TripListView.swift`), not the repo-root path (e.g. `products/fishing-logbook-ios/FishingLogbook/Views/TripListView.swift`).

### 3. Apply standard rules

Every packet, regardless of pattern, must include these rules:

```
## Rules
- Work only inside this worktree
- Do not modify files outside the repository root
- Do not commit or push
- Leave changes uncommitted for inspection
- Do not add dependencies without explicit constraint approval
- Do not modify test fixtures unless the task objective requires it
```

### 4. Write the packet

Write the rendered packet to `<worktree>/TASK_PACKET.md`.

### 5. Validate before handoff

- Packet file exists and is non-empty
- Objective section is present
- Rules section is present and includes all standard rules
- Constraints section lists at least one constraint
- No orchestration language (no "then tell", "coordinate with", "hand off to")

---

## Pattern reference

See `skills/canonical/shared/codex-packet-patterns/` for the full templates. Summary:

### implementation

Standard feature work. Includes context files, target files, acceptance criteria, and explicit scope boundaries.

### ui-polish

Review-driven fixes. Includes the review document path, checklist reference, and file-level findings to address.

### bugfix

Defect-targeted. Includes reproduction steps, expected vs actual behavior, root cause hypothesis, and targeted fix scope.

### validation

Test and build hygiene. Includes coverage targets, test file paths, and validation commands to run.

### handoff-safe

Extra boundary strictness for tasks whose output crosses worker lanes. Includes explicit "do not" list and output contract description.
