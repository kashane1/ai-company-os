# Packet Pattern: Implementation

Use for adding a new feature, screen, model, or API endpoint.

## Template

```markdown
# Task: <title>

## Objective
<1-3 sentence description of what to build>

## Context
Read these files before starting:
<list of files that provide necessary context>

## Target files
Expected to create or modify:
<list of files to touch>

## Rules
- Work only inside this worktree
- Do not modify files outside the repository root
- Do not commit or push
- Leave changes uncommitted for inspection
- Do not add dependencies without explicit constraint approval
- Do not modify test fixtures unless the task objective requires it

## Constraints
<one bullet per constraint from the task record>

## Verification
Run after changes (if applicable):
<e.g. "swift build", "python -m pytest tests/", "npm test">

## Acceptance criteria
<concrete criteria — what must be true when done>
```

## When to use

- New SwiftUI views or view models
- New SwiftData models or schema additions
- New API endpoints or workers
- New platform package modules
- Feature additions to existing screens

## Key principles

- Context files help Codex understand the codebase without exploring randomly
- Target files make the expected scope explicit and auditable
- Acceptance criteria should be testable (not "works well" but "renders 3 items from fixture data")
