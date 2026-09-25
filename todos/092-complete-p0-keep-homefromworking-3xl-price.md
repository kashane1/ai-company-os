---
status: complete
priority: p0
issue_id: "092"
tags: [home-from-working, etsy, pricing, margin]
dependencies: []
---

# Resolve the HomeFromWorking 3XL margin decision

## Problem Statement

The verified Printify cost for an enabled Gildan 5000 3XL variant is $9.87. At the current $20.99 item price, $4.95 buyer-paid U.S. shipping, and a 2% operating reserve, expected contribution is $7.68 or 29.61% of order revenue. That misses the agreed 30% launch gate by 0.39 percentage points. Changing Etsy prices is buyer-facing and requires approval of the exact revision.

## Findings

- Live/current cost evidence: S–XL $7.40, 2XL $8.94, 3XL $9.87, 4XL $10.34, and 5XL $10.31.
- Current 3XL scenario: $20.99 item + $4.95 shipping; $7.68 expected contribution; 29.61% expected margin.
- The same scenario remains positive at a 15% Offsite Ads stress fee: $3.79 contribution.
- Raising only 3XL to $21.99 produces approximately $8.57 expected contribution and a 31.81% expected margin while preserving the 2% reserve.

## Proposed Solutions

### Option 1: Raise 3XL to $21.99

**Approach:** Prepare an exact listing/variation diff after live Etsy reconciliation, then apply it only after action-time approval and read it back.

**Pros:** Clears the 30% gate without weakening the reserve; keeps the size ladder simple.  
**Cons:** Adds $1 to the buyer price for 3XL.  
**Effort:** Low after OAuth reconciliation.  
**Risk:** Low to medium because it changes public pricing.

### Option 2: Keep $20.99 and accept a documented exception

**Approach:** Leave 3XL unchanged and explicitly lower or waive the 30% gate for this size.

**Pros:** No price change.  
**Cons:** Weakens the launch discipline before real refund/replacement data exists.  
**Effort:** None.  
**Risk:** Medium.

## Recommended Action

The founder declined the proposed 3XL price change. Keep 3XL at $20.99 and preserve the existing 30% launch gate rather than silently weakening the reserve. Until a later explicit exception or price approval, operations that require the 3XL margin gate remain blocked.

## Technical Details

**Affected files and systems:**

- `state/home-from-working/operations/launch-policy.json`
- Etsy 3XL variation prices on applicable active listings

## Acceptance Criteria

- [x] Founder declined the proposed $21.99 public price revision.
- [x] 3XL remains $20.99; no Etsy price mutation was performed.
- [x] The 29.61% expected margin and 30% launch-gate failure remain explicit.
- [x] No other size, shipping price, reserve, or publication state changed.

## Work Log

### 2026-09-06 - Cost correction found

**By:** Codex

**Actions:** Reconciled the policy inputs against the current Printify variant cost set, corrected 2XL from $8.98 to $8.94 and 3XL from $9.58 to $9.87, and blocked 3XL rather than changing a live Etsy price.

### 2026-09-06 - Founder declined price change

**By:** Codex

**Actions:** Closed the price decision without changing Etsy. Kept the verified 3XL economics visible and retained the launch block for any operation that depends on the 30% margin floor.

**Learnings:** A declined public price change is not approval to lower the reserve or waive the margin gate.

## Notes

This todo authorizes no Etsy mutation by itself.
