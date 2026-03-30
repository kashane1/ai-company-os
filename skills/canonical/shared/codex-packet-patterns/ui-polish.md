# Packet Pattern: UI Polish

Use for fixing layout, styling, accessibility, or platform convention issues identified in a review.

## Template

```markdown
# Task: <title>

## Objective
Address UI polish findings from <review-document-path>.

## Review findings to address
<paste or reference the specific findings from the review document>

## Context
Read these files before starting:
- <review document path>
- <relevant style/theme files>
- <target view files>

## Target files
Expected to modify:
<list of view files with findings>

## Rules
- Work only inside this worktree
- Do not modify files outside the repository root
- Do not commit or push
- Leave changes uncommitted for inspection
- Do not add dependencies without explicit constraint approval
- Do not modify test fixtures unless the task objective requires it

## Constraints
- Address only the findings listed above — do not refactor unrelated code
- Preserve existing functionality while fixing polish issues
- Follow platform conventions (iOS HIG, SwiftUI idioms)
<additional constraints from task record>

## Acceptance criteria
- Each listed finding is addressed
- No regression in existing behavior
- Layout renders correctly across supported device sizes
```

## When to use

- After an ios-ui-polish-review produces findings
- Fixing accessibility issues (tap targets, VoiceOver, Dynamic Type)
- Correcting spacing, alignment, or color inconsistencies
- Addressing dark mode or locale-specific rendering issues

## Key principles

- Always reference the review document so Codex has concrete findings
- Keep scope tight — polish tasks should not become feature work
- Findings should have file:line references from the review
