---
status: pending
priority: p1
issue_id: "069"
tags: [code-review, product, honesty-guardrail, better-business-web, agency]
dependencies: []
---

# Problem Statement

The hero's spine — "previewed before you pay" — promises a real preview link of
*the visitor's* site. But v1 only collects a review request and routes it to the
Stage-2 **audit** loop; the per-client preview demos are built by a different
system (`prospect_site.py`, outbound). Nothing in the plan connects "visitor
requests a review" → "visitor receives a preview of their site." v1 therefore
delivers a free *audit*, not the *preview* the hero sells — an honesty-boundary
gap the plan's own §11 guardrails care about.

## Findings

- Hero/tagline lead on "previewed before you pay" — [LANDING_PAGE_PLAN.md:23](../docs/products/better-business-web/LANDING_PAGE_PLAN.md:23); called "the spine of the page... the real, defensible edge" — [LANDING_PAGE_PLAN.md:30](../docs/products/better-business-web/LANDING_PAGE_PLAN.md:30).
- v1 CTA fulfillment is the Stage-2 audit loop — [LANDING_PAGE_PLAN.md:194](../docs/products/better-business-web/LANDING_PAGE_PLAN.md:194) — which does website *audits*, not site *previews*.
- Preview demos are a separate outbound system (`packages/agency/prospect_site.py`); the plan never specifies a request→preview trigger.
- §11 honesty guardrails — [LANDING_PAGE_PLAN.md:200](../docs/products/better-business-web/LANDING_PAGE_PLAN.md:200) — make a hero promise v1 can't fulfill a self-inconsistency.

## Proposed Solutions

### Option 1: Narrow v1 hero copy to match delivery (recommended for speed)
Lead with "free website review" for the inbound funnel; reserve "previewed
before you pay" for the outbound prospect lane where a preview is actually built.

Pros:
- Honest v1 with no new system; ships now

Cons:
- Drops the strongest differentiator from the public page

Effort: small
Risk: low

### Option 2: Wire request → prospect_site preview generation
Specify the trigger so an inbound request actually produces a preview link.

Pros:
- Delivers the promised differentiator

Cons:
- Pulls the outbound preview system into the inbound v1 — larger scope; abuse/cost surface (see 074)

Effort: large
Risk: medium

## Recommended Action

Decide explicitly: either narrow the hero copy (Option 1) or specify the
request→preview bridge (Option 2). Do not ship a hero promise v1 cannot keep.

## Acceptance Criteria

- [ ] The hero promise and what v1 actually delivers are reconciled in the plan.
- [ ] If the preview promise stays, the request→preview trigger is specified.

## Work Log

### 2026-06-02 - Initial review capture
Surfaced by spec-flow-analyzer during `/review`.

### 2026-06-02 - Plan amended (diagnose+fix, P1 pass)
Resolved by making the promise traceable rather than gutting the locked
positioning: §1 now states v1 delivers "a real preview link first" by generating
a first-party preview via the existing prospect-site lane (operator-triggered),
with the Stage-2 audit as enrichment; §10 specifies both fulfillment steps; §11
reconciled ("nothing auto-sends **to the prospect**"). **Pending build step:** the
request→preview trigger wiring (depends on 068's typed capture). Keep open until
the bridge is implemented or the hero copy is narrowed if it isn't.
