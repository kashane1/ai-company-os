---
status: complete
priority: p0
issue_id: "093"
tags: [home-from-working, etsy, pilot, approval, measurement]
dependencies: ["088", "089", "092"]
---

# Approve and start the existing-listing pilot observation

## Problem Statement

The founder approved the four-pair/eight-existing-listing cohort, but starting the measurement window must bind to an exact, verified listing-state packet. All eight listings are already active, so the safe step is a zero-write freeze and observation start—not a redundant republish.

## Findings

- Exact packet revision: `53fa55bb0b797b56d31d537635f536fd95a72439206cce05402f71465ab97f28`.
- The packet covers exactly four pairs and eight active listing IDs.
- The API snapshot proves exact titles, descriptions, tags, inventory formats, price points, shipping-profile IDs, return-policy IDs, and active states.
- Signed-in Etsy UI readback proves Printify/A print shop, made-to-order 3–5 day processing, 30-day returns, and current image counts for all eight listings.
- Titles, tags, copy, art direction, and some image counts differ within the pairs. The cohort is suitable for an exploratory directional baseline, not a clean causal estimate of product format alone.
- No public listing change is required to start observing the already-active cohort.

## Recommended Action

Approve exact packet revision `53fa55bb…` for observation only. Freeze the eight listings and begin the 14-day scorecard baseline. Do not edit or republish them, and do not interpret a difference as being caused solely by product format.

## Acceptance Criteria

- [x] Four exact pair identities and eight active listing IDs are founder-approved.
- [x] Exact current titles, descriptions, tags, inventory, price points, shipping, returns, partner, processing, image counts, and states are documented.
- [x] The packet is deterministic and hash-bound to its evidence.
- [x] Founder approved exact observation revision `53fa55bb…`.
- [x] Baseline timestamp and scorecard were created after approval.
- [x] Listings are frozen during the observation window unless a separately approved safety correction is necessary.
- [x] First review is scheduled after 14 days, with no format decision before 100 aggregate listing visits or 1,000 aggregate search impressions.

## Resources

- `state/home-from-working/operations/pilot-cohort-approval-packet.md`
- `state/home-from-working/operations/pilot-cohort-approval-packet.json`
- `state/home-from-working/operations/pilot-cohort-comparability.md`
- `state/home-from-working/operations/evidence/2026-09-07/pilot-cohort-etsy-ui-readback.json`

## Work Log

### 2026-09-07 - Exact zero-write packet prepared

**By:** Codex

**Actions:** Bound current API snapshot data and signed-in Etsy UI evidence into a deterministic approval packet. Verified all eight listings' production partner and processing settings without saving changes.

**Learnings:** Because the listings are already active, Days 22–45 step 6 is satisfied by a verified freeze/readback rather than publishing an unnecessary no-op edit. Step 7 can begin immediately after exact observation approval.

### 2026-09-07 - Observation approved and baseline started

**By:** Codex

**Actions:** Recorded the founder's approval of revision `53fa55bb…`, refreshed all eight signed-in Etsy listing Stats pages, created the active scorecard, and activated the thread heartbeat `homefromworking-pilot-scorecard` for the first review on September 21 and every 14 days afterward. The baseline contains two aggregate listing visits, zero items sold, and zero revenue. No listing was edited or republished.

**Learnings:** Etsy exposed reliable listing-level visits, items sold, and revenue for the current-month baseline. Favorites, listing views, and search impressions were left null where the evidence surface did not provide consistent numeric values for all eight listings.

### 2026-09-07 - Broader read-only monitoring added

**By:** Codex

**Actions:** Added a weekly whole-shop scorecard and a separate contender/new-listing watchlist. Preserved the eight-listing scorecard as the sole product-format observation and retained the existing Etsy Stats baseline without overwriting it with an unbounded dashboard recollection.

**Learnings:** Whole-shop and contender views are useful for discovery, but their rolling UI ranges and uncontrolled creative/age differences make them unsuitable substitutes for the frozen format cohort.
