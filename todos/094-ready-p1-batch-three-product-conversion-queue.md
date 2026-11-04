---
status: ready
priority: p1
issue_id: "094"
tags: [home-from-working, printify, etsy, multi-product, automation]
dependencies: ["093"]
---

# Batch the gradual three-product conversion queue

## Problem Statement

The founder wants to continue converting older published shirt listings into multi-product listings for better buyer selection, but the current browser-heavy process takes about 30 minutes per listing. Repeating it ad hoc across roughly 70 listings spends founder time and agent usage without a consistent queue, receipt, or measurement contract.

## Findings

- Printify's public API can inspect component products but cannot create or manage a Multi-Product Listing, so a bounded signed-in browser step remains necessary.
- Etsy treats variations as choices inside one listing. Custom variation names are not search filters, so the conversion should be measured as a selection/conversion hypothesis rather than assumed to create extra search exposure.
- The active four-pair/eight-listing product-format cohort is frozen and must not be edited during its observation window.
- The current rollout default is three coherent apparel choices: the existing shirt, a hoodie, and a crewneck. The historical 12-product pilot is not the default.
- Existing saved group URLs, product IDs, copy, placement decisions, and receipts should be reused rather than rediscovered on every run.

## Proposed Solutions

### Option 1: Five-listing waves with API preflight and postflight

**Approach:** Rank eligible noncohort listings, prepare an exact five-listing queue, collect current IDs/prices/shipping/artwork checks through read-only APIs, use the browser only for irreducible Printify group operations, save each as a draft, and reconcile it before moving to the next listing.

**Pros:** Preserves the founder's strategy while reducing repeated research, ambiguous retries, and token waste. Produces clean timing and outcome data.  
**Cons:** Printify UI work still cannot be fully removed.  
**Effort:** Medium  
**Risk:** Low to medium because draft state is external; publication remains manual or separately approved.

### Option 2: Continue one-off manual conversions

**Approach:** Use the existing browser checklist independently for each listing.

**Pros:** No engineering work.  
**Cons:** Keeps the approximately 30-minute cost, increases drift, and makes comparison difficult.  
**Effort:** High over the catalog  
**Risk:** Medium.

### Option 3: Convert the full catalog to broad 12-product groups

**Approach:** Apply the historical assortment everywhere.

**Pros:** Maximum apparent choice.  
**Cons:** Weak relevance, complex shipping/pricing, excessive variants, noisier galleries, and no evidence of extra Etsy search entries.  
**Effort:** Very high  
**Risk:** High.

## Recommended Action

Use Option 1. Start with a read-only ranked queue of five noncohort listings and exclude all eight frozen cohort IDs. Keep the assortment to shirt, hoodie, and crewneck unless a later design-specific decision says otherwise. Save and reconcile one unpublished Printify group at a time, then give the founder its exact review URL. Publication is not included.

## Acceptance Criteria

- [ ] The first queue contains five exact live Etsy and Printify identities and none of the eight frozen cohort listing IDs.
- [ ] Each candidate has a reason for selection, current traffic evidence where available, artwork preflight, current prices, and shipping risk recorded before browser work.
- [ ] The default group contains only shirt, hoodie, and crewneck with clear variation names and design-appropriate variants.
- [ ] The workflow reuses an existing group URL after creation and refuses to reconvert or retry on ambiguous state.
- [ ] Every completed group has a draft URL, component IDs, copy, mockup, placement, pricing, shipping, and publication-state receipt.
- [ ] Founder minutes, agent usage, browser minutes, and rework reasons are logged per listing.
- [ ] No public listing changes occur without the separate publication gate.
- [ ] Each later-published conversion enters Layer-3 monitoring and is not used to rewrite the frozen cohort's baseline.

## Resources

- `docs/founder/printify-multi-product-workflow.md`
- `state/home-from-working/operations/day-22-90-plan.md`
- `state/home-from-working/operations/contender-watchlist.json`
- `state/home-from-working/operations/pilot.json`

## Work Log

### 2026-09-07 - Gradual conversion direction recorded

**By:** Codex

**Actions:** Recorded the founder's decision to continue older-listing conversions, bounded the work to noncohort listings and small three-product waves, and preserved separate draft, publication, and measurement gates.

**Learnings:** Added buyer choice is a valid conversion hypothesis. It is not evidence that Etsy grants one multi-product listing multiple independent search entries, so search and conversion outcomes must be measured separately.
