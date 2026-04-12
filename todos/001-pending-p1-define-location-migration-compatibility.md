---
status: pending
priority: p1
issue_id: "001"
tags: [planning, catchbook, ios, location-model, migration]
dependencies: []
---

# Problem Statement

The location-model plan changes map semantics to prefer canonical waterbody coordinates, but it leaves historical-data migration and compatibility strategy unresolved. Without an explicit transition plan, Phase 1 can regress existing Trips and map behavior for waters that currently rely on inferred spot-derived coordinates.

## Findings

- The plan updates trip and water summaries to anchor on canonical waterbody coordinates instead of inferred spot centroids in [2026-04-11-location-model-plan.md](/Users/simons/ai-company-os/docs/products/catchbook/2026-04-11-location-model-plan.md:187).
- The same document still leaves historical records without canonical coordinates as an open question and says migration should be handled incrementally later in the plan at [2026-04-11-location-model-plan.md](/Users/simons/ai-company-os/docs/products/catchbook/2026-04-11-location-model-plan.md:231) and [2026-04-11-location-model-plan.md](/Users/simons/ai-company-os/docs/products/catchbook/2026-04-11-location-model-plan.md:238).
- Current Trips map behavior depends on inferred centroids from spots, as seen in `TripHistoryLogic` calling `SpotPresentationLogic.waterbodyCentroid(from:)`, so existing records already depend on that compatibility path.

## Proposed Solutions

### Option 1: Define lazy compatibility fallback in Phase 1

Pros:
- Minimal migration risk
- Preserves current map usefulness for existing data
- Lets implementation proceed without one-time backfill

Cons:
- Adds a transitional state the product must document
- May keep mixed semantics around longer

Effort: medium
Risk: low

### Option 2: Require one-time backfill before map behavior switches

Pros:
- Cleaner final model
- Reduces long-lived compatibility code

Cons:
- Higher delivery risk
- Backfill may be lossy or unreliable for old records

Effort: medium-high
Risk: medium-high

## Recommended Action

Update the plan so Phase 1 explicitly states how existing waters and trips behave before canonical coordinates are populated, including whether inferred spot centroids remain an allowed compatibility fallback and when that fallback can be removed.

## Acceptance Criteria

- [ ] The plan states a concrete compatibility strategy for existing records without canonical waterbody coordinates.
- [ ] The plan defines whether spot-centroid fallback remains temporarily allowed on Trips maps.
- [ ] The plan states whether any backfill is required, optional, or deferred.

## Work Log

### 2026-04-12 - Initial review capture

**By:** Codex

**Actions:**
- Reviewed the plan and compared its map-phase commitments against current Catchbook map logic.
- Identified a gap between the planned canonical-coordinate rollout and the unresolved migration/backfill decision.

**Learnings:**
- The plan is directionally strong, but map compatibility for existing data needs to be spelled out before implementation starts.

