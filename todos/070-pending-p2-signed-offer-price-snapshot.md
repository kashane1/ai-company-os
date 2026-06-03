---
status: pending
priority: p2
issue_id: "070"
tags: [code-review, data-integrity, pricing, agency]
dependencies: []
---

# Problem Statement

§2 claims "Halving re-quotes existing signed OFFER.md files." That is factually
wrong — OFFER.md is persisted rendered markdown — but it points at a real
architectural defect: the client registry stores only the bundle id, no agreed
price snapshot, so any future re-scaffold re-renders a signed client's offer at
whatever the catalog says *now*. A signed price is a contractual snapshot; the
system has no snapshot/versioning. Zero customers today makes this harmless *now*
but bakes in a permanently mutable-price model.

## Findings

- §2 re-quote claim — [LANDING_PAGE_PLAN.md:71](../docs/products/better-business-web/LANDING_PAGE_PLAN.md:71).
- OFFER.md is written to disk once: `scaffold_client_workspace` calls `path.write_text(render_offer(...))` — [templates.py:97](../packages/agency/templates.py:97). It does not re-render on read.
- Registry record stores `bundle`/`services`, **no fees** — [promotion.py:102](../packages/agency/promotion.py:102).
- So a re-scaffold of an existing client re-renders OFFER.md at current catalog prices, silently rewriting agreed terms with no record of the original.

## Proposed Solutions

### Option 1: Persist a price snapshot at sign/promote time (recommended)
Store `setup_total`, `monthly_total`, per-service fees, and `signed_date`/
`catalog_rev` into the client registry record; have `render_offer` render
historical offers from the stored snapshot rather than the live catalog.

Pros:
- Signed prices become immutable + auditable; rewrites detectable

Cons:
- Registry schema change + render path branch

Effort: medium
Risk: low

### Option 2: Minimum viable — stamp `catalog_rev` + signed_date only
Don't change rendering yet, but record enough to detect drift.

Pros:
- Cheap; flags the problem

Cons:
- Doesn't prevent the rewrite

Effort: small
Risk: medium

## Recommended Action

Require the snapshot mechanism (Option 1) before the first signed offer, and fix
the §2 prose — the catalog edit affects *future* renders/re-scaffolds, not
"existing signed files."

## Technical Details

- `packages/agency/promotion.py` (record), `packages/agency/templates.py` `render_offer`.

## Acceptance Criteria

- [ ] Client record stores an agreed-price snapshot at sign time.
- [ ] Historical OFFER.md renders from the snapshot, not the live catalog.
- [ ] §2 prose corrected.

## Work Log

### 2026-06-02 - Initial review capture
Surfaced by data-integrity-guardian during `/review`.
