---
status: pending
priority: p2
issue_id: "053"
tags: [code-review, skills, contract, polish_prompt, audit-fork]
dependencies: []
---

# Problem Statement

`simulator-driven-polish/skill.md` does not cite `packages/schemas/polish_prompt.py` by name, despite the producer-consumer contract being built around it. This is a binding plan acceptance criterion that did not ship.

The plan (`docs/plans/2026-05-12-feat-premium-and-pro-value-audit-skills-plan.md` line ~805 in the Deepening Review Findings) committed to: `simulator-driven-polish/skill.md` has the one-line schema-reference annotation. Confirmed missing via grep — zero occurrences of `polish_prompt`, `POLISH_PROMPT_FIELDS`, or `recon-scaffolding` in the consumer skill body.

## Findings

- **spec-flow-analyzer:** Flow E (backlog → polish handoff) — "the producer-consumer contract has no consumer-side cite." Plan acceptance criterion not satisfied.
- **architecture-strategist:** "the consumer `simulator-driven-polish.md` does not mention `polish_prompt.py` or `POLISH_PROMPT_FIELDS`, contradicting the docstring's claim that the consumer cites this module."
- Evidence: `grep -i "polish_prompt\|POLISH_PROMPT\|recon-scaffolding\|consumes prompts\|schema" skills/canonical/simulator-driven-polish/skill.md` returns no results.

## Proposed Solutions

### Option 1: Add one-line annotation to canonical body

Add a single line to `skills/canonical/simulator-driven-polish/skill.md` under a "Consumed prompt contract" section: "This skill consumes polish prompts conforming to `packages/schemas/polish_prompt.py` `POLISH_PROMPT_FIELDS`. Producer skills (`simulator-polish-recon`, `premium-feel-audit`, `pro-value-audit`) emit prompts using the 9-field template defined there and in `skills/canonical/shared/recon-scaffolding.md`."

Pros: minimal change; satisfies the spec; makes the contract visible to readers
Cons: still prose-not-mechanical
Effort: Small
Risk: Low

### Option 2: Option 1 + add a contract-freeze fixture entry for simulator-driven-polish that locks the schema mention

Pros: prevents silent drift; ratchets the cite into the test suite
Cons: requires a new fixture file for a skill that doesn't have one
Effort: Small
Risk: Low

## Recommended Action

Option 2. The whole point of adding the schema was to make this contract mechanical. A prose-only cite repeats the failure mode we just spent commit 1 fixing.

## Technical Details

- Files affected: `skills/canonical/simulator-driven-polish/skill.md`
- If Option 2: also `skills/canonical/simulator-driven-polish/fixtures/happy_path.yaml` (already exists), add `required_section_headings` entry for "Consumed prompt contract" and `required_helper_dependencies` entries for the schema and shared spine.

## Acceptance Criteria

- [ ] `simulator-driven-polish/skill.md` body contains the literal strings `packages/schemas/polish_prompt.py` and `POLISH_PROMPT_FIELDS`
- [ ] Existing `test_simulator_driven_polish_fixtures.py` still passes
- [ ] New fixture lock added if Option 2

## Work Log

(empty)
