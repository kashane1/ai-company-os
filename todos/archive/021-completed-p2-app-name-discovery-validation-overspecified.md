---
status: completed
priority: p2
issue_id: "021"
tags: [code-review, skills, simplification, app-name-discovery]
dependencies: []
---

# Problem Statement

Phase 7 of `skills/canonical/app-name-discovery/skill.md` (Validate, steps 18–25) lists 8 self-checks, several of which are theatre for an LLM-driven agentic skill that's verifying its own arithmetic. "Confirm the output file exists and is non-empty" and "Confirm `total_candidates + discarded_count` equals total generated" are the kind of checks the model passes by writing the right thing in the first place — re-asserting them is overhead.

## Findings

Code-simplicity-reviewer:
> "For an agentic LLM-driven skill, accounting checks of its own arithmetic are theater. Trim to: shortlist=5, ≥3 archetypes, 24 cells. Drop the rest."

The high-signal validators are the ones that constrain agent behavior:
- shortlist count = 5
- shortlist archetype spread ≥ 3
- matrix has 24 cells
- every shortlist row marked `needs_verification: true`

The low-signal validators (file exists, non-empty, accounting math) just restate the contract.

## Proposed Solutions

### Option 1: Trim to 4 high-signal checks (recommended)

Replace Phase 7 (steps 18–25) with 4 checks: shortlist size = 5, shortlist archetype spread ≥ 3, matrix has 24 cells, every shortlist row has `needs_verification: true`. Update the contract-freeze fixture's `required_section_headings` if any heading text changes.

Pros: tighter contract, less prose, focused on agent-behavior invariants.
Cons: removes belt-and-suspenders accounting check.
Effort: Small. Risk: Low.

### Option 2: Keep Phase 7 but flag low-signal checks as "informational"

Preserves the checklist for readers but de-emphasizes the noise.
Pros: no information loss. Cons: doesn't actually reduce complexity.
Effort: Trivial. Risk: None.

## Recommended Action

(triage)

## Technical Details

- File: `skills/canonical/app-name-discovery/skill.md` Phase 7 section.
- Adapter Phase 8 mirrors this — trim there too if Option 1 selected.

## Acceptance Criteria

- [ ] Phase 7 has ≤ 4 validation steps.
- [ ] Each surviving step constrains agent output, not skill arithmetic.
- [ ] Adapter validation list matches canonical.
- [ ] Pytest still passes.

## Work Log

_Empty — pending triage._

## Resources

- PR: https://github.com/kashane1/ai-company-os/pull/15
