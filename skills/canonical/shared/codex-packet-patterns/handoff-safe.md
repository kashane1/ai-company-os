# Packet Pattern: Handoff-Safe

Use when the task output will be handed to another worker lane. Adds extra boundary strictness.

## Template

```markdown
# Task: <title>

## Objective
<1-3 sentence description>

## Handoff context
This task's output will be consumed by the **<target lane>** worker.
The output must be self-contained and not require follow-up engineering work to be usable.

## Context
Read these files before starting:
<list of files that provide necessary context>

## Target files
Expected to create or modify:
<list of files to touch>

## Output contract
The following must be true about the output for handoff to succeed:
<list of concrete output requirements>

## Rules
- Work only inside this worktree
- Do not modify files outside the repository root
- Do not commit or push
- Leave changes uncommitted for inspection
- Do not add dependencies without explicit constraint approval
- Do not modify test fixtures unless the task objective requires it

## Do not
- Include TODO comments that defer work to the receiving worker
- Leave incomplete implementations that require another Codex pass
- Modify files outside the explicit target list
- Embed instructions for other workers in code comments

## Constraints
<one bullet per constraint from the task record>

## Acceptance criteria
- Output contract is fully satisfied
- No loose ends or deferred items
- Changes are self-contained within target files
```

## When to use

- Engineering task whose output feeds into iOS worker (e.g. shared model changes)
- iOS build task whose output feeds into App Store worker
- Any task where the next consumer is a different worker lane

## Key principles

- The "output contract" section is critical — it defines what the receiving worker expects
- The "do not" list prevents common handoff failures (TODOs, partial work, embedded instructions)
- Handoff-safe tasks should be more strictly scoped than regular implementation tasks
