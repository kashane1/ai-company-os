---
status: pending
priority: p1
issue_id: "002"
tags: [planning, catchbook, ios, ux, location-model]
dependencies: []
---

# Problem Statement

The plan makes "At" versus "Near" central to the user-facing confidence language, but it leaves the actual rule unresolved while also making it part of the acceptance criteria. That leaves a core product and implementation contract undefined.

## Findings

- The plan introduces "At" and "Near" as the main confidence-language contract in [2026-04-11-location-model-plan.md](/Users/simons/ai-company-os/docs/products/catchbook/2026-04-11-location-model-plan.md:160).
- It then requires trip and map surfaces to apply a documented confidence-language rule in the acceptance criteria at [2026-04-11-location-model-plan.md](/Users/simons/ai-company-os/docs/products/catchbook/2026-04-11-location-model-plan.md:248).
- But the exact rule is still an open question at [2026-04-11-location-model-plan.md](/Users/simons/ai-company-os/docs/products/catchbook/2026-04-11-location-model-plan.md:290), which means implementation and review will lack a stable definition of done.

## Proposed Solutions

### Option 1: Resolve the rule in the plan now

Pros:
- Gives engineering and design a stable contract
- Makes acceptance criteria testable
- Prevents avoidable UI churn during implementation

Cons:
- Requires a product call before build starts

Effort: low
Risk: low

### Option 2: Explicitly defer confidence language out of Phase 1 acceptance

Pros:
- Keeps work moving if the product decision is not ready
- Narrows the first implementation slice

Cons:
- Weakens the plan's main trust/UX promise
- Risks another doc revision immediately after Phase 1

Effort: low
Risk: medium

## Recommended Action

Choose and document the `At`/`Near` rule before implementation begins, or remove it from Phase 1 acceptance and mark it as a follow-up phase decision. The better path is to resolve it now.

## Acceptance Criteria

- [ ] The plan defines how `At` and `Near` are determined.
- [ ] The rule is precise enough to test in UI/presentation logic.
- [ ] The open question is either closed or explicitly removed from current-phase acceptance.

## Work Log

### 2026-04-12 - Initial review capture

**By:** Codex

**Actions:**
- Reviewed the confidence-language sections and acceptance criteria.
- Flagged the mismatch between required behavior and unresolved decision.

**Learnings:**
- This is a small-seeming wording choice, but it is actually a core product contract for the redesign.

