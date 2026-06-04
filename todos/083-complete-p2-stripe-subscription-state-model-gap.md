---
status: complete
priority: p2
issue_id: "083"
tags: [code-review, planning, billing, stripe, agency, architecture]
dependencies: []
---

# Stripe Subscription State Model Gap

## Problem Statement

The plan adds Stripe subscriptions, webhook updates, and per-client billing status, but the current client registry schema only stores `billing_status`. There is no documented place for Stripe customer IDs, subscription IDs, price IDs, test/live mode, last invoice, or idempotency state.

Without those identifiers, a webhook cannot safely map Stripe events back to the correct client, retries can duplicate subscriptions, and operators cannot audit which catalog bundle maps to which live Stripe object.

## Findings

- `docs/plans/2026-06-03-feat-agency-retainer-ops-phases-6-8-plan.md:251` proposes `packages/agency/billing.py` to map packages to Stripe Price IDs.
- `docs/plans/2026-06-03-feat-agency-retainer-ops-phases-6-8-plan.md:253` proposes a subscription-creation CLI after promotion.
- `docs/plans/2026-06-03-feat-agency-retainer-ops-phases-6-8-plan.md:254` says webhooks update `client.billing_status` in the registry.
- `docs/plans/2026-06-03-feat-agency-retainer-ops-phases-6-8-plan.md:257` says one live Stripe approval plus per-client confirmation is expected.
- `packages/schemas/product.py` `ClientConfig` has `billing_status` only, with no Stripe identifiers or mode metadata.
- `packages/web/stripe_monetization.py` is a paid-validation experiment helper, not a subscription lifecycle state model for client retainers.

## Proposed Solutions

### Option 1: Add A Typed Client Billing Record

**Approach:** Extend `ClientConfig` with an optional nested billing record containing provider, mode, customer ID, subscription ID, setup invoice/payment link, monthly price ID, setup price ID, and last synced timestamp.

**Pros:**
- Gives billing code and webhooks a durable source of truth.
- Keeps client billing attached to the product registry.
- Makes audit/debugging practical.

**Cons:**
- Requires schema, loader, tests, and fixture updates.
- Needs careful defaults for legacy client records.

**Effort:** 1-2 days

**Risk:** Medium

---

### Option 2: Store Stripe State In A Separate Agency Billing Ledger

**Approach:** Keep `infra/products.json` lightweight and write Stripe identifiers to `state/agency/billing/<product_id>.json`, with registry only holding summarized billing status.

**Pros:**
- Avoids expanding registry shape too much.
- Keeps live operational/payment state under `state/`.

**Cons:**
- Requires a join between registry and state for reporting.
- Needs backup/audit strategy for payment-critical state.

**Effort:** 1-2 days

**Risk:** Medium

---

### Option 3: Limit Phase 9 To Checkout Links And Manual Reconciliation

**Approach:** Revise Phase 9 v1 to generate approved Stripe checkout/payment links and manually record `billing_status`, deferring webhooks and subscription automation.

**Pros:**
- Smaller first slice.
- Reduces risk while pricing and catalog settle.

**Cons:**
- Less agent-native and more manual.
- Does not satisfy the current "Stripe in repo" subscription goal.

**Effort:** 2-4 hours for plan revision

**Risk:** Low

## Recommended Action

Resolved in the plan by adding a Stripe billing ledger under
`state/agency/billing/<product_id>.json`, keeping `client.billing_status` as the
registry summary, and requiring metadata/idempotency checks for subscription creation
and webhooks.

## Technical Details

**Affected files:**
- `docs/plans/2026-06-03-feat-agency-retainer-ops-phases-6-8-plan.md`
- `packages/schemas/product.py`
- `packages/config/products.py`
- Future `packages/agency/billing.py`
- Future `scripts/agency/create_client_subscription.py`
- Tests under `tests/python/unit/`

**Related components:**
- Catalog bundle pricing.
- Stripe live-payment gate.
- Client registry.
- Monthly reports.

**Database changes:**
- No SQL migration expected, but registry/state schema changes are likely.

## Resources

- Plan billing section: `docs/plans/2026-06-03-feat-agency-retainer-ops-phases-6-8-plan.md`
- Client schema: `packages/schemas/product.py`
- Existing Stripe helper: `packages/web/stripe_monetization.py`

## Acceptance Criteria

- [ ] Phase 9 specifies where Stripe customer/subscription/price identifiers are stored.
- [ ] Subscription creation is idempotent for a client product ID.
- [ ] Webhook mapping from Stripe event to client record is deterministic and tested.
- [ ] Live Stripe actions require canonical approval and preserve test/live mode in state.
- [ ] Reporting can explain billing status using persisted Stripe state, not only a final enum.

## Work Log

### 2026-06-03 - Review Finding

**By:** Codex

**Actions:**
- Compared the Phase 9 plan against current client registry schema and existing Stripe helper.
- Created this todo as P2 because the gap is a reliability/auditability risk for billing implementation.

**Learnings:**
- `billing_status` is enough for a dashboard badge, but not enough for subscription lifecycle automation.

### 2026-06-03 - Plan Resolution

**By:** Codex

**Actions:**
- Added a billing state model to the plan with customer/subscription/invoice IDs, mode, price IDs, idempotency key, and last sync.
- Required Stripe metadata mapping for `product_id` and `bundle`.
- Clarified that registry remains source-controlled summary state while operational Stripe IDs live in `state/`.

**Learnings:**
- Retainer billing needs a durable operational ledger, but source-controlled registry should stay small.

## Notes

- This finding assumes Phase 9 keeps automated subscriptions/webhooks in scope. If v1 becomes manual Stripe links, the todo can be downgraded or closed after the plan is updated.
