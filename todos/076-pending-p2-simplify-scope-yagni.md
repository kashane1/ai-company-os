---
status: pending
priority: p2
issue_id: "076"
tags: [code-review, simplicity, yagni, scope, better-business-web, agency]
dependencies: []
---

# Problem Statement

A technical review of a not-yet-built marketing page got upgraded into permanent,
tested infrastructure for a v1 with **zero customers**: a catalog mirror
generator + drift test for a one-time edit, a duplicate render path forced by the
no-build rule, six new portfolio routes, and a launch-mode variant. Several of
these solve problems a pre-customer v1 doesn't have yet.

## Findings

- §2: new `render_service_catalog()` + `scripts/agency/render_catalog_md.py` + drift test to sync a **57-line static** mirror after a **one-time** halving — [LANDING_PAGE_PLAN.md:74](../docs/products/better-business-web/LANDING_PAGE_PLAN.md:74). ~80–120 LOC + recurring CI maintenance tax for a doc no customer reads.
- §5: two tested Python partials (`render_packages_section`, `render_portfolio_section`) maintained as a **second render path** alongside the Astro source-of-record, purely to honor §4's no-build rule — [LANDING_PAGE_PLAN.md:119](../docs/products/better-business-web/LANDING_PAGE_PLAN.md:119). The prospect-lane's no-build discipline is being cargo-culted onto a one-page, rarely-changed site where a single `astro build` is negligible.
- §6: six `/work/<slug>` routes pulled forward from v2 into v1 — [LANDING_PAGE_PLAN.md:134](../docs/products/better-business-web/LANDING_PAGE_PLAN.md:134) ("the v2 route forward").
- §8: offers two options (flag vs separate checklist) for relaxing two items — see 066.

## Proposed Solutions

### Option 1: Trim §2/§5/§6, collapse §8 to the flag (recommended)
- §2: halve prices in `catalog.yaml`, hand-edit the 14 numbers + 3 anchors in the mirror in the same commit; build the generator only when price changes become frequent.
- §5: let Astro build this **one** site (scoped exception to the no-build rule) — packages/portfolio become normal components, no Python twin, no partial tests. (If the no-build rule must hold, keep the partials but drop the render-guard/unit-test ceremony — the operator visually reviews the page in the mandatory preview gate.)
- §6: ship the portfolio **grid** with 6 cards; defer the six routed sub-pages until a lead clicks through.
- §8: pick the flag (per 066), not a separate checklist.

Pros:
- Launches sooner; far less permanent tested machinery for a zero-customer page

Cons:
- Defers hardening until a real lead / second price change justifies it

Effort: small (it's deletion of scope)
Risk: low

### Option 2: Keep the plan as written
Build all four.

Pros:
- Maximally robust from day one

Cons:
- Scope runs ahead of customer count; duplicate render path maintained forever

Effort: large
Risk: medium (maintenance + delay)

## Recommended Action

Adopt Option 1 before any code is written. Note: the §5 "let Astro build this one
site" decision interacts with 071 (Netlify form detection) — building also makes
native form detection the happy path.

## Acceptance Criteria

- [ ] §2 mirror sync is a one-commit hand-edit unless frequent price changes are demonstrated.
- [ ] No duplicate Astro + Python render path ships for the same sections.
- [ ] §6 v1 ships the grid; the six routes are explicitly deferred.
- [ ] §8 resolved to the flag.

## Work Log

### 2026-06-02 - Initial review capture
Surfaced by code-simplicity-reviewer during `/review`.

### 2026-06-02 - Partially resolved
- §5 render path: **resolved** — operator chose "let Astro build this one site"
  (plan §4/§5 updated); no Python render-partial twin will be built.
- §8 flag vs separate checklist: **resolved** — implemented as the `first_party`
  flag (todo 066, done).
- §2 mirror: kept the generator + drift test (built in plan step 1) rather than the
  hand-edit — small and permanently guards the SoT doc.
- §6 routes-into-v1: **still open** — decide grid-only vs the six `/work/<slug>`
  routes when §6 is built (todo 072).
