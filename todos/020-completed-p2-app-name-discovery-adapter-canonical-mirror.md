---
status: completed
priority: p2
issue_id: "020"
tags: [code-review, skills, simplification, app-name-discovery]
dependencies: []
---

# Problem Statement

The `app-name-discovery` Claude adapter at [skills/adapters/claude/app-name-discovery.md](skills/adapters/claude/app-name-discovery.md) duplicates ~50% of the canonical body at [skills/canonical/app-name-discovery/skill.md](skills/canonical/app-name-discovery/skill.md): the rubric table, the three hard gates, the spread rule, and the validation list all appear in both files. The adapter even says "This adapter mirrors that body" and then mirrors it. Compare to `skills/adapters/claude/gtm-artifact-refresh.md`, which delegates harder. Two surfaces to keep in sync is the worst of both worlds.

## Findings

Code-simplicity-reviewer:
> "Pick one: either (a) shrink the adapter to a quick-reference + 'follow canonical step N' pointers (~40 lines), or (b) drop the canonical and keep only the adapter. The current 50/50 mirror is the worst of both — two surfaces to keep in sync."

Reference: [skills/adapters/claude/gtm-artifact-refresh.md](skills/adapters/claude/gtm-artifact-refresh.md) is the established pattern — the adapter quick-references the canonical and lets the canonical own the details.

## Proposed Solutions

### Option 1: Shrink the adapter to a quick-reference (recommended)

Reduce the adapter to: frontmatter + Quick reference (3–5 bullets) + Steps (one line each: "1. Validate founder pack — see canonical Phase 0") + Boundaries. Move the rubric table, gate definitions, and validation checklist out of the adapter; keep them only in canonical.

Pros: matches `gtm-artifact-refresh` convention; one source of truth; ~100-line reduction.
Cons: Claude runtime now must read both files; minor fetch cost.
Effort: Small. Risk: Low.

### Option 2: Drop the canonical, keep only the adapter

Removes the canonical/adapter split for this skill. Easier to read, but breaks the WIRING.md contract and would require a registry-level exception.

Pros: zero duplication.
Cons: violates the WIRING canonical → adapter → pointer model; precedent risk for other skills.
Effort: Small. Risk: High (architectural).

## Recommended Action

(triage)

## Technical Details

- Files affected: `skills/adapters/claude/app-name-discovery.md` (shrink).
- No registry/test changes needed; the contract-freeze fixture asserts on canonical body, not adapter body.

## Acceptance Criteria

- [ ] Adapter is < 60 lines of body content.
- [ ] Adapter contains no rubric weight table, no gate threshold details, no validation checklist — those live only in canonical.
- [ ] Adapter Quick reference + Steps reference canonical phase numbers.
- [ ] Pytest `test_app_name_discovery_fixtures.py` still passes.

## Work Log

_Empty — pending triage._

## Resources

- PR: https://github.com/kashane1/ai-company-os/pull/15
- Pattern reference: [skills/adapters/claude/gtm-artifact-refresh.md](skills/adapters/claude/gtm-artifact-refresh.md)
- WIRING contract: [skills/WIRING.md](skills/WIRING.md)
