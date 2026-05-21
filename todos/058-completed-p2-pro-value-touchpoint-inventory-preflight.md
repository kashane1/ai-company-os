---
status: pending
priority: p2
issue_id: "058"
tags: [code-review, skills, pro-value-audit, adapter, preflight]
dependencies: []
---

# Problem Statement

`pro-value-audit`'s canonical body declares an "empty Pro touchpoint inventory" as a failure mode (canonical line 224: "emit one-prompt bootstrap: 'inventory Pro touchpoints in the rubric first.'") — but the adapter pre-flight does not check this condition. The adapter only does a rubric line-count stub check, which would pass for a rubric whose touchpoint inventory section is empty.

This leaves a silent path: a rubric with all category headers filled out but an empty "Pro touchpoint inventory" section passes the adapter check, then the canonical body has no programmatic recovery — the audit runs against an empty inventory and produces a degenerate backlog.

## Findings

- **spec-flow-analyzer:** "Empty Pro touchpoint inventory not in pre-flight (failure-mode matrix). Canonical `:224` describes the bootstrap behavior but adapter pre-flight at `pro-value-audit.md:14-22` does not include a check that the inventory section in the rubric has entries. Adds a silent path where a rubric with stub touchpoint section passes stub-check (line count) but the inventory is empty."

## Proposed Solutions

### Option 1: Add a touchpoint-inventory check to the pre-flight

Pre-flight gets a new step (between current steps 6 and 7):

```
7. Touchpoint inventory check: extract the "## Pro touchpoint inventory" section
   from pro-value-rule.md. If the section contains zero bullet items (or fewer
   than the operator-defined minimum), emit a one-prompt bootstrap backlog
   asking the operator to inventory Pro touchpoints before audit can proceed.
```

Pros: closes the silent path; matches the canonical body's documented behavior; cheap
Cons: pre-flight grows one step
Effort: Trivial
Risk: None

### Option 2: Strengthen the stub check to verify section content, not just line count

Change the stub check from `wc -l` to a grep-based test that counts bullets under `## Pro touchpoint inventory`.

Pros: single check covers both stub and empty-inventory
Cons: less explicit about what's being checked
Effort: Trivial
Risk: None

## Recommended Action

**Option 1.** Explicit > clever. The pre-flight should name each check it does. A grep-based stub check that conflates "rubric is too short" with "inventory is empty" is harder to debug when it triggers.

## Technical Details

- Files affected:
  - `skills/adapters/claude/pro-value-audit.md` (add pre-flight step 7)

## Acceptance Criteria

- [ ] Adapter pre-flight has an explicit touchpoint-inventory check
- [ ] The check is described in plain text (not a regex an LLM has to parse)
- [ ] Canonical body's existing "empty Pro touchpoint inventory" failure mode language is preserved
- [ ] All fixture tests pass

## Work Log

(empty)
