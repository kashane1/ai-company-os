# Packet Pattern: Validation

Use for adding or fixing tests, lint rules, or build checks.

## Template

```markdown
# Task: <title>

## Objective
<describe what validation coverage to add or fix>

## Coverage target
- Current: <current state, e.g. "no tests for TripViewModel">
- Goal: <target state, e.g. "unit tests for all public methods on TripViewModel">

## Context
Read these files before starting:
- <source files being tested>
- <existing test files for reference patterns>
- <test configuration files>

## Target files
Expected to create or modify:
<list of test files>

## Rules
- Work only inside this worktree
- Do not modify files outside the repository root
- Do not commit or push
- Leave changes uncommitted for inspection
- Do not add dependencies without explicit constraint approval
- Do not modify source code — only test files (unless fixing a discovered bug is part of the objective)

## Constraints
- Follow existing test patterns and naming conventions
- Use existing fixtures and helpers where available
- Do not mock what can be tested directly
<additional constraints from task record>

## Validation commands
Run after changes:
<list of commands, e.g. "swift test", "python -m pytest tests/", "npm test">

## Acceptance criteria
- All new tests pass
- All existing tests still pass
- Coverage goal is met
- No flaky or timing-dependent tests introduced
```

## When to use

- Adding unit tests for new or untested code
- Fixing broken or flaky tests
- Adding integration tests for persistence or API flows
- Improving lint or type-check coverage

## Key principles

- Always specify the validation commands so Codex can self-check
- Reference existing test patterns to maintain consistency
- Distinguish between "test-only" tasks and "fix + test" tasks
