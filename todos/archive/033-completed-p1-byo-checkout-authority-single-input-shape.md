---
status: pending
priority: p1
issue_id: "033"
tags: [code-review, security, architecture, agency, byo-bundle, stripe]
dependencies: []
---

# Problem Statement

The build-your-own-bundle checkout function (`netlify/functions/create-checkout.mjs`, planned) accepts EITHER a `bundle_id` (promo price) OR a custom `service_ids[]` (tier discount). The plan never states the authority rule when both are sent, or when a custom `service_ids` set happens to equal a preset. This is the highest-risk surface in the feature: security (price-vs-delivery tampering), architecture (path-dependent pricing), and avoidable branching all converge here.

## Findings (security-sentinel C1, architecture-strategist P1, code-simplicity #1)

1. **Tampering vector:** client posts `bundle_id: package_a` (promo $599) but also `service_ids:[…richer set…]`. If the function prices off `bundle_id` but writes the client `service_ids` into metadata → `promote_order_to_client` → `client.services`, the buyer pays the cheap promo and gets the richer set provisioned. Under-charge + over-deliver.
2. **Path-dependent price:** the same 6 services price $899 via `bundle_id=package_b` but $913 via `service_ids` (tier). So price depends on *which field the client populated*, not what they bought. Modifying a preset and reverting lands $913, not $899 — silently different charge for an identical cart.
3. **Two trusted input shapes** each need their own allowlist/dedupe/cap/`self_serve` guards — double the validation surface on the riskiest endpoint.

## Proposed Solutions

### Option 1 (recommended): one input shape — `service_ids[]` + optional `preset_id` hint
- Client ALWAYS sends `service_ids[]` plus an optional `preset_id` hint.
- Server normalizes (sort, dedupe, allowlist, `self_serve`, cap, reject empty), computes the tier price, then **if** `preset_id` present AND the normalized set is byte-identical to that preset's canonical set in the trusted table → substitute `setup_promo_cents`; else ignore the hint and charge tier.
- `preset_id` is a hint, never an authority — it can only *lower* price to a server-known constant for an exact-match set. A forged hint on a non-matching cart does nothing.
- "Modified preset → custom price" becomes free/automatic (no client-trusted "did they edit it?" state). Idempotency key keys uniformly on `service_ids + server amounts + nonce`.
- Pros: one validation path; security story is "hint can only discount an exact match"; less branching. Cons: a sorted-set equality (~3 lines).

### Option 2: keep `bundle_id` XOR `service_ids`, pin the rule
- Exactly one present (reject both/neither → 400). If `bundle_id`: ignore client `service_ids` entirely, derive from trusted table, price promo, write server-derived set to metadata. If `service_ids`: tier price (optionally canonicalize to preset on exact match).
- Pros: explicit. Cons: two input shapes / two guard paths remain.

## Recommended Action

(leave blank for triage)

## Technical Details

- Affected: `products/better-business-web/site/netlify/functions/create-checkout.mjs` (new), `packages/agency/payments.py` `create_client_checkout`, `scripts/agency/create_checkout.py`. Metadata written to Stripe (session + `subscription_data`) and consumed by `promote_order_to_client` must be the **server-derived** set.
- Plan: `/Users/kashane/.claude/plans/sorted-wondering-honey.md` §3a/§3c.

## Acceptance Criteria

- [ ] Server never trusts a client-sent (price, services) pairing; the thing billed == provisioned == reconciled.
- [ ] A `preset_id`/`bundle_id` only discounts an exact-match service set; non-match falls back to tier price.
- [ ] Tests: forged hint on non-matching cart charges tier; exact-match charges promo; both-fields / neither rejected (if Option 2).
- [ ] Idempotency key uses server-computed amounts, not client-sent.

## Work Log

(to be filled in)

## Resources

- /workflows:review round 2 (2026-06-06): security-sentinel C1, architecture-strategist P1, code-simplicity-reviewer #1
