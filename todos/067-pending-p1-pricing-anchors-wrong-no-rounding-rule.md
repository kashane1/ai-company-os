---
status: pending
priority: p1
issue_id: "067"
tags: [code-review, data-integrity, pricing, better-business-web, agency]
dependencies: []
---

# Problem Statement

§2 presents a halved per-service price table and three bundle "from" anchors as
authoritative. They are wrong: halving odd list prices produces half-dollar
floats, the only rounding in the system is the display formatter `_money`
(`{value:,.0f}`, round-half-to-even), and the plan's hand-typed numbers do not
match what `quote_bundle` + `_money` will actually render. The plan even claims
the anchors are "computed, not hand-typed" — yet they are hand-typed and wrong.
No canonical rounding rule is pinned.

## Findings

- §2 table rounds inconsistently by hand: `$249→$125` (up) but `$99→$49` (down) — [LANDING_PAGE_PLAN.md:41](../docs/products/better-business-web/LANDING_PAGE_PLAN.md:41).
- `quote_bundle` keeps cents as floats — [offer.py:159](../packages/schemas/offer.py:159).
- Display rounds via `_money` `{value:,.0f}` (round-half-to-even) — [templates.py:124](../packages/agency/templates.py:124).
- Actual rendered output vs plan:
  - Per-service: `$999/2=499.5 → $500` (plan says $499); `$99/2 → $50` (plan $49); `$249/2 → $124` (plan $125); `$49/2 → $24` (plan $25). Multiple rows wrong.
  - Bundle anchors render **A $774 + $50/mo**, **B $1,024 + $99/mo**, **C $1,200 + $248/mo**; plan says A $49/mo, B $98/mo, C $1,199+$247/mo — **all three wrong**.
- Minor: §2 labels Package C "Presence + Growth"; catalog says "Presence + Capture + Growth" — [catalog.yaml:192](../packages/agency/catalog.yaml:192).

## Proposed Solutions

### Option 1: Store pre-rounded whole-dollar prices in catalog.yaml (recommended)
Operator picks a clean halved price per service (e.g. $999→$500, $99→$50,
$249→$125, $49→$25). No half-dollar ever enters the pipeline; `_money` becomes a
no-op; anchors are deterministic. Then regenerate the §2 table + anchors from
`quote_bundle` output.

Pros:
- Removes float non-determinism entirely; numbers become trivially verifiable

Cons:
- Prices aren't exactly half (operator judgment per line)

Effort: small
Risk: low

### Option 2: Keep exact halves, pin one documented rounding function
Decide round-vs-floor and whether rounding happens at data or display layer;
document it; recompute the table/anchors to match.

Pros:
- Prices are exactly half

Cons:
- Half-dollar floats persist; easy to reintroduce drift

Effort: small-medium
Risk: medium

## Recommended Action

Adopt Option 1. Drop the hand-typed anchors from the plan prose and reference
`quote_bundle` output; fix the Package C label; recompute every number in §2
from the catalog after the rounding decision.

## Technical Details

- `packages/agency/catalog.yaml` (the values), `packages/agency/templates.py` `_money` (rounding behavior), `packages/schemas/offer.py` `quote_bundle`.

## Acceptance Criteria

- [ ] A canonical rounding rule is decided and stated.
- [ ] Every §2 per-service number matches `_money(catalog value)`.
- [ ] All three bundle anchors match `quote_bundle()` rendered output.
- [ ] Package C label matches catalog.yaml.

## Work Log

### 2026-06-02 - Initial review capture
Pricing math verified against catalog.yaml + _money/.0f during `/review`.

### 2026-06-02 - Plan amended (diagnose+fix, P1 pass)
Locked the rounding rule in §2 (halve → round up to whole dollar; store integers
so no half-dollar enters the pipeline and `_money` is a no-op). Corrected every
per-service number and all three bundle anchors (A $775+$50/mo, B $1,025+$100/mo,
C $1,200+$250/mo) and fixed the Package C label to "Presence + Capture + Growth".
**Pending build step:** apply the whole-dollar values to `catalog.yaml` and
regenerate from `quote_bundle()` (sequenced in 077; interacts with 070). Keep
open until the catalog is updated and numbers regenerate cleanly.
