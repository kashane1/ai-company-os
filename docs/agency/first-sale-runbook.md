# First-Sale Runbook — taking money for the first time

> The one-time setup tax that turns "code-complete" into "can accept a paying
> customer," plus a break-glass fallback to close sale #1 even if the automation
> hiccups. Do this once; every sale after is minutes-to-cash.
>
> Canonical env vars + receiver/tunnel setup live in
> [go-live-checklist.md §2](go-live-checklist.md) — this runbook is the **sequence,
> the corrections, and the fallback**, not a duplicate of that table.
> Sources + Stripe doc links: [go-live readiness plan → Research Insights G1](../plans/2026-06-05-feat-agency-packages-go-live-readiness-plan.md#-g1--stripe-go-live-the-code-is-right-these-are-the-runbook-deltas).

## Which keys actually matter (read this first)

The sale flow uses **hosted Stripe Checkout** (`scripts/agency/create_checkout.py`
→ `packages/agency/payments.py`). It needs the **server-side** keys:

| Env var | What it's for |
|---|---|
| `STRIPE_SECRET_KEY` (`sk_test_…` / `sk_live_…`) | create the Checkout session ← **the real unlock** |
| `STRIPE_WEBHOOK_SECRET` (`whsec_…`) | verify the webhook signature |
| `STRIPE_PRICE_MAP` | bundle → `{setup, monthly}` price IDs, keyed by `"test"` / `"live"` |
| forward URL + secret | webhook → forwarder → local receiver (see go-live-checklist §2a) |

> A **publishable key (`pk_…`) is NOT used anywhere** in this codebase (no
> client-side Stripe.js) — adding it does **not** unblock payments. Don't mistake it
> for progress on the secret key.

## Step 1 — Test mode (mandatory dry run)

1. In Stripe **test** mode, create each bundle's **setup (one-time)** Price and
   **monthly (recurring)** Price. Set a stable **`lookup_key`** on each (e.g.
   `pkg_a_setup`, `pkg_a_monthly`) so the test↔live `price_…` ID divergence stops
   mattering.
2. Put the test price IDs in the `"test"` block of `STRIPE_PRICE_MAP`; set the test
   `STRIPE_SECRET_KEY`.
3. Stand up the receiver + tunnel and register the **test** webhook endpoint with
   the 8-event subscription (go-live-checklist §2a–2b).
4. `python scripts/agency/create_checkout.py --product-id <id> --bundle package_a`
   → open the URL → pay with test card `4242 4242 4242 4242`.
5. Confirm the loop: webhook → forwarder → receiver flips
   `state/agency/billing/<id>.json` to `billing_status: active`, and the registry
   `client.billing_status` matches with `accepted_at`/`accepted_by` stamped.

## Step 2 — Go live

1. **Recreate** the Products + Prices in **live** mode (IDs differ; reuse the same
   `lookup_key`s). Add the `"live"` block to `STRIPE_PRICE_MAP`.
2. Set `STRIPE_SECRET_KEY=sk_live_…`. **Rotate keys before go-live** in case a dev
   key leaked during development.
3. Register a **live** webhook endpoint (same 8 events); copy its `whsec_…` into
   `STRIPE_WEBHOOK_SECRET`. Point the forwarder at the live receiver.
4. Confirm the account is **activated for live charges AND payouts** (a charge can
   succeed while payouts are paused if activation is incomplete).
5. Grant the `stripe_live_subscription` approval for the first client.

## Step 3 — Live smoke test (corrected — this is the important one)

`create_checkout.py --mode live` (refuses without the approval + an `sk_live_` key),
pay with a **real card you control**, then:

1. Confirm a real **live `invoice.paid` reached the receiver** — not just that the
   card was charged. *(This catches the #1 go-live mistake: webhook still on test /
   wrong `whsec_`.)*
2. Confirm the ledger flips `active` and stamps acceptance.
3. **Refund the charge AND cancel the subscription.** ⚠️ A refund alone does **not**
   cancel the subscription — leave it and the test card rebills next month. Then
   confirm the ledger flips to `refunded`.

## Step 4 — Don't-forget settings (per Stripe go-live)

- [ ] **Tax:** either enable Stripe Tax (`automatic_tax`, registrations for states
      where you have nexus, business origin address, collect billing address) **or**
      record "confirmed no nexus obligation for target states." Don't omit silently.
- [ ] **Customer comms:** enable live **email receipts** + **invoice emails**
      (Settings → Customer emails). They're often off in test mode.
- [ ] **Statement descriptor + business name** set, so customers recognize the
      charge (unrecognized charges → disputes).

## Break-glass fallback for sale #1

If the live webhook smoke test surfaces a problem mid-sale, don't block revenue —
close the deal by hand and reconcile later:

- **Stripe Payment Link** (subscription mode, two prices: monthly recurring + setup
  one-time). Send the link, customer pays today, zero webhook code. **Point it at
  the same live webhook endpoint** so once the endpoint is healthy the
  `invoice.paid` still flows through the ledger.
- **Hosted Invoice** (`collection_method=send_invoice`) if the client wants an
  invoice / NET terms / bank payment.

Use these as a **one-time safety net**, not steady state — beyond a couple of
clients you'd be hand-maintaining subscription state Stripe's events give you for
free.

## Monitoring after go-live (lightweight)

- **Billing drift:** ledger `billing_status` ≠ registry `client.billing_status` for
  the same `product_id`.
- **Dead-letter:** anything in `state/agency/billing/dead-letter/` → a payment for
  an unpromoted/unknown client; promote + re-run.
- **Dispute/refund:** any `disputed`/`refunded` ledger → `assert_billing_active`
  already halts retainer work; respond to a dispute within the network deadline
  (7–21 days) with proof of service (the live site). A dispute does **not** cancel
  the subscription — decide whether to cancel it.
- Live webhooks retry up to **3 days**; manual resend up to **15 days** (Dashboard)
  / **30 days** (CLI `stripe events resend`).
