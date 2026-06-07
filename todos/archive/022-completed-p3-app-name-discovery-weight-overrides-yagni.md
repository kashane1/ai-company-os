---
status: completed
priority: p3
issue_id: "022"
tags: [code-review, skills, yagni, app-name-discovery]
dependencies: []
---

# Problem Statement

`weight_overrides` is plumbed through the `app-name-discovery` skill's contract.yaml, skill.md, adapter, and output-template — but no caller has asked for per-product rubric overrides. It is speculative flexibility.

## Findings

Code-simplicity-reviewer:
> "`weight_overrides` is YAGNI. No caller asked for it; it complicates contract, fixture, and output front-matter. Remove until a real need appears. Saves ~10 lines across skill.md, contract.yaml, adapter, output-template."

Also flagged by agent-native-reviewer: the type `map_or_null` in contract.yaml is non-standard versus the canonical type vocabulary used by other skills.

## Proposed Solutions

### Option 1: Remove `weight_overrides` entirely (recommended)

Default weights become the only weights. If a future product needs overrides, add it then.

Pros: simpler contract; aligns with YAGNI. Removes the non-standard `map_or_null` type question.
Cons: future override callers need a small PR. Acceptable.
Effort: Trivial. Risk: None.

### Option 2: Keep but document as experimental

Tag the input as experimental in contract.yaml; tighten type to a real one.
Pros: preserves the optionality. Cons: still YAGNI-violating, just labeled.

## Recommended Action

(triage)

## Acceptance Criteria

- [ ] `weight_overrides` removed from `contract.yaml`, `skill.md`, adapter, and output-template front-matter examples.
- [ ] Fixture and pytest still pass.
- [ ] Skill body still mentions that defaults are tunable (future work).

## Resources

- PR: https://github.com/kashane1/ai-company-os/pull/15
