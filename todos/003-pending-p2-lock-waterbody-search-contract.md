---
status: pending
priority: p2
issue_id: "003"
tags: [planning, catchbook, ios, location-model, search]
dependencies: []
---

# Problem Statement

Phase 1 depends on a search-first waterbody flow, but the plan does not lock the search/provider contract. That leaves a material scope and privacy ambiguity in the first phase.

## Findings

- The plan makes search-first waterbody entry a Phase 1 UX commitment in [2026-04-11-location-model-plan.md](/Users/simons/ai-company-os/docs/products/catchbook/2026-04-11-location-model-plan.md:142) and [2026-04-11-location-model-plan.md](/Users/simons/ai-company-os/docs/products/catchbook/2026-04-11-location-model-plan.md:181).
- It later lists the actual search-provider decision as a dependency at [2026-04-11-location-model-plan.md](/Users/simons/ai-company-os/docs/products/catchbook/2026-04-11-location-model-plan.md:272).
- That choice materially affects offline behavior, privacy posture, API surface, and how much of the new waterbody flow can be implemented inside the current local-first form architecture.

## Proposed Solutions

### Option 1: Commit to Apple-native place search with manual/private fallback

Pros:
- Clearest implementation path
- Aligns with iOS-native UX expectations
- Keeps the search-first promise concrete

Cons:
- Search quality and offline behavior depend on Apple APIs

Effort: low
Risk: medium

### Option 2: Narrow Phase 1 to local/manual search semantics only

Pros:
- Stronger local-first story
- Lower integration complexity

Cons:
- Underdelivers on the brainstorm's canonical-water discovery goal
- Likely requires another redesign soon after

Effort: low-medium
Risk: medium

## Recommended Action

Add an explicit Phase 1 contract for waterbody search: which provider is in scope, what happens offline, and what fallback path ships if canonical search is unavailable.

## Acceptance Criteria

- [ ] The plan specifies the in-scope search source for Phase 1.
- [ ] The plan specifies offline behavior for waterbody entry.
- [ ] The plan specifies the fallback path for private/custom water creation when search is unavailable or unsuitable.

## Work Log

### 2026-04-12 - Initial review capture

**By:** Codex

**Actions:**
- Reviewed the Phase 1 waterbody-entry commitments and dependency list.
- Captured the unresolved provider contract as a planning risk rather than an implementation detail.

**Learnings:**
- The search contract is part of the product scope, not just a technical implementation choice.

