# Agency Go-Live Checklist

> Operator runbook to take the agency transaction loop **live** and deliver
> Package C. The code is complete and tested; everything below is configuration,
> external setup, and verification — the things only the operator can do.
>
> Related: [transaction-loop plan](../plans/2026-06-04-feat-agency-transaction-loop-package-c-fulfillment-plan.md) ·
> [service catalog](service-catalog.md) · [client lifecycle](client-lifecycle.md)

## Conventions

- **Secrets are server-side only.** Set them in Netlify env / the gitignored
  `.env`, never committed, never in `dist/`. The deploy refuses to ship a build
  containing a credential-shaped string (`packages/web/deploy.assert_no_secret_leak`).
- **Test mode first.** Validate every payment/email/SMS path in test mode before
  flipping the live switch. Live Stripe + live SMS move real money / carry legal risk.
- **Approvals gate the irreversible.** Live payments and ad go-live are refused
  without a granted approval.

---

## 0. Pre-flight (once)

- [ ] `python -m pytest tests/python/unit -q` is green.
- [ ] Decide the agency's sending domain (for Resend) and a Stripe account.
- [ ] `.env` (gitignored) or Netlify env holds the secrets below; `git grep` finds
      none of them in the repo.

| Env var | Used by | Where set |
|---|---|---|
| `RESEND_API_KEY`, `LEAD_NOTIFY_EMAIL`, `LEAD_FROM_EMAIL` | G2 lead email | Netlify (BBW site) |
| `STRIPE_SECRET_KEY`, `STRIPE_PRICE_MAP` | G1 checkout (CLI) | `.env` / API host |
| `STRIPE_WEBHOOK_SECRET_TEST`, `STRIPE_WEBHOOK_SECRET_LIVE` | webhook signature verify | **Netlify** (BBW site) |
| `NETLIFY_AUTH_TOKEN`, `BBW_SITE_ID` (optional) | Blobs poller (`pull-stripe-events.mjs`) | `.env` |
| `PLAUSIBLE_API_KEY`, `PLAUSIBLE_BASE_URL` | G10 reporting | `.env` / API host |
| `NETLIFY_AUTH_TOKEN` | deploys | `.env` |

---

## 1. G2 — Lead capture + notification (lowest risk; do first)

- [ ] In Resend, **add + verify the sending domain** (SPF `TXT`, DKIM `TXT`,
      DMARC `TXT` at `_dmarc`). Status must read **verified** before real sends.
- [ ] Set `RESEND_API_KEY`, `LEAD_NOTIFY_EMAIL` (default `ksakhakorn@gmail.com`),
      and `LEAD_FROM_EMAIL` (a `…@<verified-domain>` address) in the BBW Netlify env.
- [ ] Preflight the key out-of-band:
      `curl -s https://api.resend.com/emails -H "Authorization: Bearer $RESEND_API_KEY" -H "Content-Type: application/json" -d '{"from":"<verified>","to":"<you>","subject":"preflight","text":"ok"}'` → expect `200` + an `id`.
- [ ] Deploy the BBW site. **Submit a real test lead through the live form.**
      Confirm: lands on `/thanks/`, the email arrives within seconds, and after
      `node scripts/web/pull-inbound.mjs` the typed record is in
      `state/prospects/inbound/`.
- [ ] Act on it: `python scripts/agency/process_inbound_review.py --id <id> --city "<City>" --genre <genre>`.

**Rollback:** unset `RESEND_API_KEY` (leads still capture, just no email), or
redeploy the prior `website-review.mjs`.

---

## 2. G1 — Payments (real money; test mode → live)

### 2a. Webhook architecture (no tunnel — Blobs + poller)
The deployed webhook is a **stable Netlify Function** that verifies the Stripe
signature and writes each event to a Netlify **Blobs** store (`stripe-events`); a
local poller drains it when the Mac is up. There is **no** localhost tunnel and no
`/stripe/forward` receiver in this path (`AGENCY_STRIPE_EVENT_FORWARD_*` are the
deprecated forward design — leave unset). The flow:

```
Stripe → https://better-business-web.netlify.app/.netlify/functions/stripe-webhook
       → (verify sig, write Blobs "stripe-events")
       → node scripts/web/pull-stripe-events.mjs   (drain Blobs → state/agency/stripe-events/)
       → python scripts/agency/reconcile_stripe_billing.py   (apply → ledger)
```

- [ ] The function ships with every `netlify deploy --prod` (it's in `netlify.toml`'s
      functions dir). It returns `503 payments not configured` until a webhook secret
      is set — that's step 2b/2c.
- [ ] Poller auth: `NETLIFY_AUTH_TOKEN` in `.env` (the script also reads it from `.env`
      directly). `BBW_SITE_ID` defaults to the BBW site; override only if it changes.

### 2b. Test mode (mandatory dry run)
- [ ] Create the bundle's **setup (one-time)** + **monthly (recurring)** prices in
      Stripe **test** mode; put their ids in `STRIPE_PRICE_MAP` under `"test"`.
- [ ] Register a **test** webhook endpoint (URL above) and set its `whsec_…` as
      `STRIPE_WEBHOOK_SECRET_TEST` in **Netlify** env; redeploy.
- [ ] `python scripts/agency/create_checkout.py --product-id <id> --bundle package_c`
      → open the URL, pay with test card `4242 4242 4242 4242`.
- [ ] Drain + reconcile, then confirm the ledger flips:
      `node scripts/web/pull-stripe-events.mjs && python scripts/agency/reconcile_stripe_billing.py`
      → `cat state/agency/billing/<id>.json` shows `billing_status: active`, and the
      registry `client.billing_status` matches with `accepted_at`/`accepted_by` stamped.

### 2c. Go live
- [ ] **Recreate** the prices in Stripe **live** mode (ids differ) → add a `"live"`
      block to `STRIPE_PRICE_MAP`.
- [ ] Set `STRIPE_SECRET_KEY=sk_live_…` and register a **live** webhook endpoint
      (URL: `https://better-business-web.netlify.app/.netlify/functions/stripe-webhook`);
      copy its `whsec_…` into **Netlify** env as `STRIPE_WEBHOOK_SECRET_LIVE` (NOT the
      local `.env` — the function runs on Netlify), then redeploy. Test and live secrets
      coexist; the function tries each until one verifies. Subscribe to: `invoice.paid`,
      `invoice.payment_failed`, `customer.subscription.updated`,
      `customer.subscription.deleted`, `charge.dispute.created`,
      `charge.dispute.closed`, `charge.refunded`, `checkout.session.completed`.
- [ ] **Free plumbing test (do before any charge):** in the Stripe endpoint page click
      **Send test webhook** → `checkout.session.completed` (expect `200`), then
      `node scripts/web/pull-stripe-events.mjs && python scripts/agency/reconcile_stripe_billing.py`.
      It dead-letters (no real client metadata) — that's success: it proves signature
      verify + Blobs + poller + reconcile end to end for **$0**.
- [ ] **$1 money smoke:** create a $1 Payment Link in **Live**, pay with your own card,
      drain + reconcile, then **refund it** and re-drain — confirm `charge.refunded`
      processes (the refund reconciles itself).
- [ ] Grant the `stripe_live_subscription` approval for the first client.
- [ ] `create_checkout.py --mode live` (refuses without the approval + an `sk_live_` key).
- [ ] **Full activation smoke:** pay a real bundle checkout (carries client metadata) →
      ledger `active` → then **refund it** and confirm the ledger flips to `refunded`.

**Rollback:** disable the live webhook endpoint in Stripe; revoke the approval; refund
any erroneous charge (the refund reconciles itself).

---

## 3. G10 — Reporting data

- [ ] Add the Plausible script to each client site and configure a **custom-event
      goal named exactly `Form Lead`**; fire `plausible('Form Lead')` on form submit.
- [ ] Set `PLAUSIBLE_API_KEY` (and `PLAUSIBLE_BASE_URL` if self-hosted).
- [ ] `python scripts/agency/run_monthly_report.py --product-id <id> --month YYYY-MM --site-id <site>`
      → real visits/leads. If the goal is missing it **fails loud** (exit 2) — fix the goal, don't ship a fake 0.

---

## 4. Per-client Package C delivery (build-on-demand, all offline)

- [ ] **Promo page:** `python scripts/agency/build_promo_page.py --business … --headline … --out …`
- [ ] **GBP:** `python scripts/agency/draft_gbp_changeset.py --business … --service … --city … --out <docs>` → apply the `GBP_CHANGESET.md` by hand (re-check live state first).
- [ ] **Google Ads:** `python scripts/agency/draft_google_ads.py … --daily-budget N --monthly-budget M --out <docs>`. Go-live is gated: a positive daily **and** monthly cap + a granted `ad_campaign_go_live` approval are required. Spend stays in the client's account.
- [ ] **Business email:** `python scripts/agency/setup_business_email.py --business … --domain … --out <docs>`; `--mark-complete` once mail flows.
- [ ] **Booking:** `python scripts/agency/inject_booking.py --site-file … --provider calendly --booking-url … --product-id <id>` (idempotent).
- [ ] **Local SEO / site build / launch:** existing `run_local_seo.py`, scaffold, and `launch_client.py` gate.

---

## 5. G9 — Review SMS: **do not send live yet**

Ships **templates-only** behind `assert_review_sms_allowed`. Before a single live
text is legal you must: register an A2P 10DLC brand + campaign (with live
**Privacy Policy + Terms URLs** — binding 2026-06-30), capture each customer's
opt-in, and build the send-time per-recipient STOP-suppression + quiet-hours
checks. Until then, leave it gated. (Tracked as the one remaining Tier-2 slice.)

---

## 6. Monitoring (lightweight, local-first)

- [ ] **Un-notified leads:** records in `state/prospects/inbound/` with `status: new`
      past ~30 min → the email pipeline is broken.
- [ ] **Billing drift:** ledger `billing_status` ≠ registry `client.billing_status`
      for the same `product_id`.
- [ ] **Dead-letter:** anything in `state/agency/billing/dead-letter/` → a payment
      for an unpromoted/unknown client; promote + re-run.
- [ ] **Dispute/refund:** any `disputed`/`refunded` ledger → the `assert_billing_active`
      guard already stops retainer work; follow up with the client.

---

## Definition of "live"

A real prospect can submit the form → you're notified → you send a preview and a
pay link → they pay → the ledger activates and stamps acceptance → you deliver the
bundle's services. Everything in that sentence is code-complete; this checklist is
the configuration that turns it on.
