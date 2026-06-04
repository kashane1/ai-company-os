---
status: complete
priority: p2
issue_id: "085"
tags: [code-review, planning, billing, stripe, architecture, agency]
dependencies: []
---

# Stripe Webhook Local State Execution Model

## Problem Statement

The updated plan adds a Stripe billing ledger under `state/agency/billing/` and says
a webhook handler updates that ledger plus the registry summary. It does not specify
where the webhook handler runs or how it can safely write local-first repo state.

Stripe webhooks need a reachable HTTP endpoint. Existing Stripe scaffold code uses
Netlify serverless functions, which cannot directly mutate this Mac's local
`state/agency/billing/` files or source-controlled `infra/products.json`. A local
Mac API can write the files, but Stripe cannot call it unless an explicit tunnel or
poll/reconcile workflow exists. Without that execution model, Phase 9 can be
implemented as a handler that verifies events but never reconciles billing state.

## Findings

- `docs/plans/2026-06-03-feat-agency-retainer-ops-phases-6-8-plan.md` says `state/agency/billing/<product_id>.json` stores Stripe operational state.
- The same plan says the webhook handler handles `invoice.paid` / `subscription.updated` and updates the billing ledger plus `client.billing_status`.
- Existing web-lane Stripe scaffold lives in Netlify functions and currently only logs completed checkout events.
- The repo architecture is local-first: durable runtime state lives under `state/`, and the control plane is local.
- A deployed webhook endpoint and local file-backed state are different runtimes unless the plan defines a bridge, reconciliation job, or tunnel.

## Proposed Solutions

### Option 1: Make Phase 9 Poll/Reconcile First

**Approach:** Replace live inbound webhook mutation in v1 with a local
`scripts/agency/reconcile_stripe_billing.py` command that uses Stripe API event or
subscription reads to update `state/agency/billing/` and registry summary.

**Pros:**
- Fits local-first architecture.
- Avoids exposing a local webhook endpoint.
- Easy to run in monthly RetainerOps and after subscription creation.

**Cons:**
- Billing status is eventually consistent.
- Requires operator/agent scheduling for reconciliation.

**Effort:** 4-8 hours

**Risk:** Low

---

### Option 2: Add A Public Webhook Forwarder With Authenticated Local Pull

**Approach:** Let a deployed webhook endpoint verify Stripe signatures and store
minimal event payloads in a remote queue/object store. The local RetainerOps job
pulls verified events and updates local state.

**Pros:**
- Preserves webhook responsiveness.
- Keeps local state writes local.

**Cons:**
- Adds remote infrastructure and secret handling.
- More moving parts than needed for v1.

**Effort:** 1-2 days

**Risk:** Medium

---

### Option 3: Expose The Local Control Plane Through A Tunnel

**Approach:** Use a tunnel such as Cloudflare Tunnel/ngrok so Stripe can POST to a
local endpoint that writes state.

**Pros:**
- Direct webhook-to-ledger updates.
- Minimal remote code.

**Cons:**
- Operationally fragile for an always-on Mac.
- Expands attack surface and requires explicit auth/rate-limit design.

**Effort:** 1-2 days

**Risk:** High

## Recommended Action

Resolved in the plan by reusing the Netlify Stripe scaffold as the public verified
event receiver and adding a local reconciliation command that writes
`state/agency/billing/` and registry summary state.

## Technical Details

**Affected files:**
- `docs/plans/2026-06-03-feat-agency-retainer-ops-phases-6-8-plan.md`
- Future `packages/agency/billing.py`
- Future `scripts/agency/create_client_subscription.py`
- Future `scripts/agency/reconcile_stripe_billing.py`
- Existing web-lane Stripe docs/scaffold if reused

**Related components:**
- `packages/web/stripe_monetization.py`
- `packages/web/scaffold/astro-landing/netlify/functions/stripe-webhook.mjs`
- `state/agency/billing/`
- `infra/products.json`

**Database changes:**
- None expected.

## Resources

- Plan: `docs/plans/2026-06-03-feat-agency-retainer-ops-phases-6-8-plan.md`
- Existing Netlify webhook scaffold: `packages/web/scaffold/astro-landing/netlify/functions/stripe-webhook.mjs`
- Architecture local-state rule: `docs/architecture.md`

## Acceptance Criteria

- [ ] Phase 9 specifies whether billing status updates are webhook-driven, poll/reconcile-driven, or forwarder-driven.
- [ ] The chosen model can actually update `state/agency/billing/` and registry summary in the local-first repo.
- [ ] If any public webhook endpoint is used, the plan specifies signature verification, replay/idempotency handling, and where verified events are stored.
- [ ] Tests cover idempotent reconciliation for duplicate Stripe events or repeated subscription reads.
- [ ] Monthly reports read billing status from the reconciled ledger, not from remote Stripe assumptions.

## Work Log

### 2026-06-03 - Review Finding

**By:** Codex

**Actions:**
- Re-reviewed Phase 9 after the billing ledger fix.
- Compared the plan against existing Netlify Stripe scaffold and the repo's local-first state model.
- Identified the missing execution model for webhook-to-local-state updates.

**Learnings:**
- A billing ledger location solves identity/state shape, but the plan also needs a runtime path that can write that ledger.

### 2026-06-03 - Plan Resolution

**By:** Codex

**Actions:**
- Updated Phase 9 to reuse the existing Netlify serverless Stripe scaffold.
- Specified that Netlify verifies and records events but does not mutate Mac-local state.
- Added local `scripts/agency/reconcile_stripe_billing.py` as the writer for billing ledger and registry summary updates.

**Learnings:**
- The local-first architecture wants a public receive step and a local reconcile step, not a remote function writing local files.

## Notes

- This is a residual finding after todo 083. Todo 083 fixed what state exists; this one fixes how Stripe events reach that state.
