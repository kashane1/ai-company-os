---
status: completed
priority: p3
issue_id: "024"
tags: [code-review, skills, contracts, app-name-discovery]
dependencies: []
---

# Problem Statement

`skills/canonical/app-name-discovery/skill.md` Phase 6 promises that the output front-matter includes `archetype_count` and `register_count`, but `contract.yaml` only declares `candidates_path`, `shortlist_count`, `total_candidates`, `discarded_count`. A worker reading the contract wouldn't know `archetype_count`/`register_count` exist.

## Findings

Agent-native-reviewer observation:
> "Consider adding `archetype_count` and `register_count` to `contract.yaml` outputs since skill.md promises them in front-matter — currently a worker reading the contract wouldn't know they exist."

## Proposed Solutions

### Option 1: Add them to contract.yaml outputs (recommended)

Two-line addition to contract.yaml. Aligns the contract with what the skill actually produces.

Pros: contract is complete. Cons: none.
Effort: Trivial. Risk: None.

### Option 2: Drop them from the output front-matter

If they aren't part of the contract, they shouldn't be in the output. (4 × 6 are constants in this version of the skill anyway.)

Pros: smaller output; constants are constants. Cons: future-extensibility-loss if the matrix shape ever changes.

## Acceptance Criteria

- [ ] `contract.yaml` outputs lists either both `archetype_count` and `register_count` (Option 1) OR they are dropped from output-template (Option 2).
- [ ] `skill.md` Phase 6 matches the chosen direction.
- [ ] Pytest still passes.

## Resources

- PR: https://github.com/kashane1/ai-company-os/pull/15
