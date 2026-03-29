---
id: codex-claude-handoff
name: Codex-Claude Handoff
purpose: Transfer work between Codex and Claude agents with explicit context, boundaries, and expected next actions.
owner_agent: any
target_runtimes: [claude, codex]
stage: active
inputs:
  - source_agent (claude or codex)
  - task_id or work context identifier
  - completed_work summary
  - remaining_work description
  - relevant file paths
  - any blocking issues or open questions
outputs:
  - a handoff document at the expected location for the receiving agent
  - updated task status if applicable
allowed_edit_boundaries:
  - state/artifacts/
  - state/checkpoints/platform/tasks/
  - skills/adapters/ (if adapter regeneration is needed)
forbidden_areas:
  - packages/policies/
  - infra/
dependencies: []
validation_steps:
  - handoff document is present and non-empty
  - receiving agent's expected inputs are all provided
  - no ambiguous instructions (every next action references a concrete file or skill)
handoff_contract:
  what_is_handed_off: handoff document with full context
  handed_to: the receiving agent (claude or codex)
claude_adaptation_notes: |
  When Claude receives a handoff from Codex, it should read the handoff
  document, verify the referenced artifacts exist, and proceed with the
  remaining_work section. When Claude hands off to Codex, it should
  render a task packet using the bounded-codex-implementation skill.
codex_adaptation_notes: |
  When Codex receives a handoff from Claude, the task packet in the
  worktree IS the handoff. Codex does not read this skill definition
  directly — the engineering worker translates it into a task packet.
---

## Instructions

### Handoff FROM Codex TO Claude

Use this when Codex has completed implementation work and Claude needs to review, validate, or extend it.

1. Locate the task run artifacts:
   - diff at `state/artifacts/engineering/<task-id>/diff.patch`
   - logs at `state/logs/engineering/<task-id>/`
   - task run at `state/checkpoints/platform/task_runs/<run-id>.json`

2. Write the handoff document to `state/artifacts/handoffs/<task-id>-codex-to-claude.md`:

```markdown
# Handoff: Codex → Claude

## Task
<task-id>: <title>

## What Codex completed
<summary of changes, referencing the diff artifact>

## Artifacts
- Diff: state/artifacts/engineering/<task-id>/diff.patch
- Logs: state/logs/engineering/<task-id>/

## Remaining work
<specific next actions for Claude>

## Open questions
<anything unresolved that Claude must address or escalate>
```

3. Validate all referenced artifact paths exist.

### Handoff FROM Claude TO Codex

Use this when Claude has completed planning, review, or design work and Codex should implement.

1. Prepare the implementation scope:
   - identify the target repo and files
   - write explicit constraints
   - specify acceptance criteria

2. Create a task record (or update an existing one) in the platform state.

3. Use the `bounded-codex-implementation` skill to render the task packet and execute.

The task packet IS the handoff to Codex. Do not create a separate handoff document.

### Handoff validation

Before completing any handoff:

- every referenced file path must exist
- every next action must reference a concrete skill, file, or command
- ambiguous instructions like "finish the feature" are not acceptable
- if the remaining work cannot be fully specified, create explicit open questions instead
