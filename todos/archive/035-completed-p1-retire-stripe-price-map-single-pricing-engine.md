---
status: pending
priority: p1
issue_id: "035"
tags: [code-review, architecture, agent-native, stripe, agency, money]
dependencies: []
---

# Problem Statement

The plan keeps TWO mechanisms reaching Stripe for the same money: the operator/CLI path resolves pre-created Price IDs from `STRIPE_PRICE_MAP` (`payments.py` `resolve_price_entry`), while the web custom path mints inline `price_data` from `quote_services`. The plan also says to "regenerate `STRIPE_PRICE_MAP`" — but a regenerated map CANNOT carry the curated promo ($599/$899/$1,799), because the promo is a `setup_promo` override computed by `quote_services`, not a per-service price. Result: CLI and web charge different money for the same package A/B/C.

## Findings (architecture-strategist P2, agent-native-reviewer #1, pattern P2-4, data P3-2)

1. `STRIPE_PRICE_MAP` holds pre-promo Price IDs; regenerating it only carries the re-split per-service numbers, never the bundle-level promo. So `create_checkout.py --bundle package_a` would charge a different setup than the website's $599.
2. The plan's line "regenerate STRIPE_PRICE_MAP so the operator path charges post-re-split numbers" **contradicts** its own line "A/B/C resolve `bundle → service_ids → quote_services` on both web and CLI."
3. This is the same dual-source-of-truth bug as the Python/JS one, one layer down (Stripe-side).

## Proposed Solutions

### Option 1 (recommended): one engine — inline `price_data` for ALL paths
Retire `STRIPE_PRICE_MAP` for the BBW agency/BYO flow. Both web function and CLI resolve `bundle → setup_promo + service_ids → quote_services → inline price_data` (and custom carts → tier → inline `price_data`). `mode` branches subscription/payment on monthly>0. Remove the "regenerate the price map" done-criterion.
- Pros: single pricing engine; CLI/web byte-identical; no stale Price IDs. Cons: every checkout mints inline prices (already required for custom carts anyway).

### Option 2: keep the price map, guard it
Regenerate `STRIPE_PRICE_MAP` from the catalog AND add a test asserting `resolve_price_entry(package_b).setup unit_amount == quote_bundle("package_b").setup_after_discount` (cents). Custom carts still inline.
- Pros: smaller diff. Cons: two mechanisms persist; the promo can't be represented as a per-service price, so presets still can't use the map for promo pricing → Option 1 is cleaner.

## Recommended Action

(leave blank for triage)

## Technical Details

- Affected: `packages/agency/payments.py` (`resolve_price_entry`, `create_client_checkout`, hardcoded `mode="subscription"`), `scripts/agency/create_checkout.py` (add `--service-id`), `scripts/agency/stripe_bootstrap.py` (price-map regen — likely retire for this flow).
- Mid-migration hazard: until the CLI moves to `quote_services`, `--bundle` quotes stale prices. Move the CLI to `quote_services` in Phase 1 (needs only the schema) or mark it stale until Phase 3c.

## Acceptance Criteria

- [ ] One pricing engine reaches Stripe for presets and custom carts (web + CLI).
- [ ] CLI `--bundle package_b` charges the promo $899 (cents-identical to web).
- [ ] If price map retained: cents-equality test vs `quote_bundle` exists; else map retired for BBW flow and the regen criterion removed from the plan.

## Work Log

- 2026-06-07: The **web** path is done — `create-checkout.mjs` prices all carts
  (preset + custom) via inline `price_data` from the shared engine, no price map.
  **Remaining:** the operator/agent CLI parity — generalize
  `packages/agency/payments.py:create_client_checkout` to accept a `service_ids`
  list and build inline `price_data` (so an agent can checkout an arbitrary custom
  bundle), add `--service-id` to `scripts/agency/create_checkout.py`, and route
  the `--bundle` path through `quote_bundle` (promo) rather than the stale
  `STRIPE_PRICE_MAP`. Until then the operator CLI quotes pre-re-split prices for
  named bundles. Kept pending.

## Resources

- /workflows:review round 2 (2026-06-06): architecture-strategist P2, agent-native-reviewer #1, pattern-recognition P2-4

- 2026-06-07 (done): added `create_inline_checkout` (catalog-priced inline `price_data`, subscription/payment mode branch, `validate_selection` guard) + `--service-id` on `create_checkout.py`, both bundle and custom routes through one engine that matches the web flow. `StripeCheckoutProvider.create_checkout` handles both modes. Legacy `create_client_checkout`/STRIPE_PRICE_MAP kept but no longer used by the CLI. Tests in test_agency_payments_inline.py.
