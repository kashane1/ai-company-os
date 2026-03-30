# Packet Pattern: Bugfix

Use for fixing a specific reported defect with known reproduction steps.

## Template

```markdown
# Task: <title>

## Objective
Fix: <one-line defect description>

## Reproduction
1. <step 1>
2. <step 2>
3. <step 3>

**Expected**: <what should happen>
**Actual**: <what happens instead>

## Root cause hypothesis
<brief explanation of the suspected cause, if known>

## Context
Read these files before starting:
<list of files likely involved>

## Target files
Expected to modify:
<narrowest set of files to fix the defect>

## Rules
- Work only inside this worktree
- Do not modify files outside the repository root
- Do not commit or push
- Leave changes uncommitted for inspection
- Do not add dependencies without explicit constraint approval
- Do not modify test fixtures unless the task objective requires it

## Constraints
- Fix only the reported defect — do not refactor surrounding code
- If the root cause hypothesis is wrong, describe the actual cause in a comment
<additional constraints from task record>

## Acceptance criteria
- The reproduction steps no longer produce the defect
- Existing tests still pass
- No new warnings introduced
- If a regression test can be written for this defect, include it
```

## When to use

- A user-reported or QA-reported defect with clear reproduction
- A regression from a recent change
- A crash or data corruption issue

## Key principles

- Reproduction steps are critical — Codex needs to understand the exact failure
- Root cause hypothesis helps Codex focus but should not constrain investigation
- Scope should be minimal — fix the bug, nothing more
