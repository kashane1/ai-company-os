---
status: pending
priority: p2
issue_id: "043"
tags: [code-review, data-integrity, billing, agent-native, agency]
dependencies: ["036"]
---

# Problem Statement

Self-serve sales reconcile through `billing.py`, which dead-letters any event whose `product_id` has no registry record and requires non-empty `metadata.bundle`. Several reconciliation-correctness details must be pinned or paid customers silently fail to activate.

## Findings (architecture-strategist P3, agent-native #4, security M2, data-integrity P4)

1. **`product_id` identity:** the id minted by the order poller MUST equal the `product_id` in Stripe metadata, or the registry lookup misses and the event dead-letters forever. State this contract explicitly.
2. **`bundle` on both:** set `bundle` (`"custom"` or `preset_id`) on the session AND `subscription_data.metadata` — `invoice.paid` renewals carry only the subscription metadata; if `bundle` is session-only, every renewal dead-letters (`payments.py:99-100`, `billing.py:161-169`).
3. **Ledger `service_ids`:** `BillingLedger` has no `service_ids` field — add it so the ledger records what was bought (idempotency key degrades to `product_id:custom:mode`, unique per client but composition-blind).
4. **`self_serve` allowlist must exist before the function enforces it:** the security control references a field that isn't built yet. Ship `self_serve` (default true) or have the function allowlist an explicit `byo_eligible` set — don't leave a control pointing at a non-existent field.
5. **Agent-CLI provenance:** an agent-created custom checkout that bypasses the order store skips `promote_order_to_client` → recreates the dead-letter risk. Route agent-CLI custom checkouts through the same pre-`invoice.paid` registry-record creation, or give them distinct provenance and an equivalent create-then-activate path.
6. **Ordering + replay:** order poller upserts the registry record BEFORE the stripe-events drain; name the dead-letter replay step (no replay script exists today) or make it an explicit manual step.

## Proposed Solutions

### Option 1 (recommended)
Pin the `product_id` contract; write `bundle` + `service_ids` to session and subscription metadata; add `service_ids` to `BillingLedger`; ship the `self_serve` field; ensure both web and agent-CLI custom checkouts create the registry record before payment; document/script dead-letter replay.

## Recommended Action

(leave blank for triage)

## Technical Details

- Affected: `packages/agency/billing.py` (ledger `service_ids`), `packages/agency/payments.py` (metadata on both session + subscription), `packages/agency/promotion.py` (`promote_order_to_client`), `scripts/web/pull-orders.mjs` + `scripts/agency/process_inbound_order.py` (ordering), `packages/schemas/offer.py` (`self_serve`), `scripts/agency/` (replay step). Verify the billing test/live mode-fence covers `source:"byo"` events.

## Acceptance Criteria

- [ ] Test-mode E2E: order → registry upsert → `invoice.paid` reconciles + activates (no dead-letter); renewal invoice also reconciles.
- [ ] `product_id` identical between poller record and Stripe metadata (asserted).
- [ ] `bundle` + `service_ids` present on session AND subscription metadata; ledger stores `service_ids`.
- [ ] `self_serve`/`byo_eligible` allowlist exists and is enforced server-side.
- [ ] Agent-CLI custom checkout gets a pre-payment registry record; dead-letter replay documented.

## Work Log

- 2026-06-07: Core dead-letter fix shipped — `promote_order_to_client` creates the
  registry record from the order (with the same `product_id` the function minted,
  so the reconciler finds it), `bundle` + `service_ids` are set on BOTH the session
  and `subscription_data` metadata, `self_serve` is shipped and enforced server-side,
  and `pull-orders.mjs` + `process_inbound_order.py` are the ingestion pair (run
  before the stripe drain). **Remaining:** add a `service_ids` field to
  `BillingLedger` (currently the purchased composition lives only in the registry
  `client.services`, which is sufficient for fulfillment but not recorded on the
  ledger), and verify the dead-letter **replay** path end-to-end against a live
  Stripe test event after deploy. Kept pending.

## Resources

- /workflows:review round 2 (2026-06-06): architecture-strategist P3, agent-native-reviewer #4, security-sentinel M2, data-integrity-guardian P4
