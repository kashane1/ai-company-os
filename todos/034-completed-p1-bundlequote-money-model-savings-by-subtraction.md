---
status: pending
priority: p1
issue_id: "034"
tags: [code-review, data-integrity, money, agency, schema]
dependencies: []
---

# Problem Statement

The revised plan keeps a single `BundleQuote.discount_pct` and says "for a package it's the effective % implied by the override." The effective %s are fractional (A 14.31%, B 16.29%, C 19.11% — C exceeds the 15% tier max). Overloading one field invites a phantom-tier UI label and lossy reverse-derivation of the charged price. Money must be computed in integer cents with half-up rounding, discount as subtraction.

## Findings (architecture-strategist P1, data-integrity P1-1/P1-2, pattern P1-4, simplicity #2)

1. **Savings must be subtraction, not %-derived.** If any layer rounds the % and back-computes savings: A shows $97.86 not $100.00; B $171.84 not $175.00; C $422.56 not $425.00. Required: `discount_cents = setup_gross_cents - setup_after_cents`; display/island read `discount_cents`, never recompute from `%`.
2. **Phantom tier label.** Reusing `discount_pct` makes a package render "19% off setup" — a tier rung that doesn't exist. Replace overloaded field with a discriminated `pricing_mode: "tier" | "promo"` (+ `tier_pct` for tier, `promo_setup_cents`/`savings_cents` for promo); compute any displayed "% off vs building it yourself" only at the display edge.
3. **`round_half_up` underspecified.** Must operate on `Decimal(str(value))` with `ROUND_HALF_UP`, NOT a binary float (`2.675*100` = 267.4999…). Replace banker's `round()` at `offer.py:167-168` and `stripe_bootstrap.py`. No real half-cent exists in the catalog today — the boundary test needs a synthetic fixture.
4. **`BundleQuote` rename breaks 3 callers.** `setup_total` is read in `templates.py` `render_offer` (line 64), `render_service_catalog` (140), `render_catalog_json` (167). Migrate atomically (or keep `setup_total` as a back-compat property). Grep tests for `setup_total` first.
5. **No `monthly_after_discount` field** — keep discounted-monthly structurally impossible; assert `monthly_total == sum(monthly)` regardless of discount.

## Proposed Solutions

### Option 1 (recommended)
`BundleQuote` exposes `setup_gross`, `setup_after_discount`, `monthly_total`, `discount_cents` (=gross−after), and `pricing_mode`. `discount_pct` (if kept) is display-only and documented lossy. One `round_half_up(Decimal)` primitive in the schema module; `quote_bundle` routes through `quote_services`. Migrate all `setup_total` readers in the same atomic change.

## Recommended Action

(leave blank for triage)

## Technical Details

- Affected: `packages/schemas/offer.py` (⚠️ founder-gated) `BundleQuote`/`quote_services`/`quote_bundle`/`round_half_up`; `packages/agency/templates.py` (3 `setup_total` readers + `_num`); `scripts/agency/stripe_bootstrap.py` (rounding).

## Acceptance Criteria

- [ ] Savings computed by integer subtraction everywhere; display never back-derives from %.
- [ ] `round_half_up` uses Decimal+ROUND_HALF_UP; banker's `round()` removed from offer.py & stripe_bootstrap.py.
- [ ] Test: per-package `setup_gross_cents - setup_after_cents == {10000,17500,42500}`; synthetic half-cent agrees Py↔JS; `monthly_total == sum(monthly)` at every tier.
- [ ] All `setup_total` readers migrated atomically; renders unbroken.

## Work Log

(to be filled in)

## Resources

- /workflows:review round 2 (2026-06-06): architecture-strategist P1, data-integrity-guardian P1-1/P1-2, pattern-recognition P1-4
