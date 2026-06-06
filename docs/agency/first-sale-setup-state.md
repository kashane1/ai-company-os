# First-Sale Setup — current state & handoff

> Working companion to [first-sale-runbook.md](first-sale-runbook.md). Tracks what's
> already proven vs. what still needs a human. Delete or archive once sale #1 lands.

## ✅ Proven (no Stripe account needed — done locally)

- **Billing logic** — 40/40 unit tests green (`test_agency_payments`, `_billing`,
  `_billing_states`, `_stripe_receiver`, `_billing_active_gate`, `_retainer_approvals`).
- **The full receiver loop, as a running server** — started `apps.api.main:app` against
  an isolated sandbox (`AI_COMPANY_OS_REPO_ROOT`) and POSTed reshaped events to
  `/stripe/forward`. Confirmed end-to-end:
  | Event | Result |
  |---|---|
  | `invoice.paid` (good secret) | ledger → `active`, registry `billing_status` → `active`, `accepted_at`/`accepted_by` stamped |
  | wrong forward secret | `401` (Stripe will retry) |
  | duplicate redelivery | no double-process (`processed_event_ids` stable) |
  | unknown `product_id` | `200` dead-lettered + `dead-letter/<evt>.json` written |
  | live event vs test ledger | `422` mode-fence refusal |
  | `charge.refunded` | ledger → `refunded` (then `assert_billing_active` halts retainer work) |

  Everything *downstream* of Stripe works. The only unproven hop is Stripe → the
  Netlify forwarder, which needs a real key + public tunnel.

## ✅ Staged (ready, waiting on your inputs)

- **`.env`** — `AGENCY_STRIPE_EVENT_FORWARD_SECRET` filled with a real generated secret.
  Empty placeholders left for: `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`,
  `STRIPE_PRICE_MAP`, `AGENCY_STRIPE_EVENT_FORWARD_URL`.
- **`scripts/agency/stripe_bootstrap.py`** — creates all 3 products + 6 prices
  (stable `lookup_key`s) from the marketed prices in `packages.json`, idempotent,
  no SDK/CLI needed. Emits the `STRIPE_PRICE_MAP` block. Mode-guarded.

## 🙋 Needs you (the irreducible human gates)

| # | Step | Why it's yours |
|---|---|---|
| 1 | Paste a **`sk_test_…`** key into `.env` → `STRIPE_SECRET_KEY` | It's behind your Stripe login + 2FA |
| 2 | Install a tunnel: `brew install cloudflared` (and `stripe` CLI optional) | System install on your machine |
| 3 | Run the tunnel, paste its origin+`/stripe/forward` into `AGENCY_STRIPE_EVENT_FORWARD_URL` | — |
| 4 | Register the **test** webhook endpoint (8 events) in your Stripe Dashboard, copy `whsec_…` → `STRIPE_WEBHOOK_SECRET`; set the forward secret + URL in **Netlify** env | Dashboard + Netlify are your accounts |
| 5 | Pay the test checkout with `4242 4242 4242 4242` | I *can* do this once the tunnel's up — but it's one click for you |

Once #1–#4 are done I can run `stripe_bootstrap.py`, fill `STRIPE_PRICE_MAP`, create
the checkout, and drive the test payment — then we watch the **real** webhook flow
through to the ledger. After that, the live cutover is the same recipe with `sk_live_`
+ your money-clicks (charge/refund), per the runbook's Step 3.

## ✅ Live test RESULTS (2026-06-05 — real test-mode payment)

Ran the full loop with a real Stripe **test** checkout + `4242` payment through a
cloudflared tunnel → the **actual** Netlify forwarder `.mjs` → local receiver:

- **It works.** `smoketest-site` flipped `trial → active`; registry stamped
  `accepted_by=cus_UeWdvZvCjIDEwO`, real `sub_…`/`in_…` ids in the ledger.
- **3 products + 6 prices** created in Stripe test (via `stripe_bootstrap.py`),
  `STRIPE_PRICE_MAP` wired, all three bundles resolve.
- **`stripe` SDK** was missing from `pyproject` → added (`stripe>=15.2.0`).

### Findings (carry into go-live)

1. **`invoice.paid` carries NO `product_id` metadata** (empirically confirmed —
   Stripe does not propagate subscription metadata onto the invoice). Activation
   still works because `checkout.session.completed` (which *does* carry metadata)
   **seeds the ledger first**, and `invoice.paid` falls back to it by
   subscription/customer (`billing.py:156`). **⇒ `checkout.session.completed` is
   load-bearing — never drop it from the 8-event subscription.**
2. **Event-ordering race is benign.** If `invoice.paid` arrives before the ledger
   exists, the receiver returns `422` → forwarder returns 502 → Stripe retries →
   heals once `checkout.session.completed` lands. Saw exactly one such transient
   `422` in the test; final state was correct. This is the intended durability path.
3. **Idempotency-key bug (`payments.py`)** — the key is fixed
   (`checkout:<id>:<bundle>:<mode>`) but `expires_at` varies per call, so Stripe
   rejects any *second* checkout for the same client/bundle/mode for ~24h
   (`IdempotencyError`). Bites on **resending an offer**. Not yet fixed.
4. **Paid success page** — `/thanks/` was the free-review confirmation (wrong for
   payers). Added `/welcome/` (`welcome.astro`) and repointed `success_url`
   (`payments.py:156`). ⚠️ **Must be deployed to Netlify before the new
   `success_url` goes live** (else it 404s on `better-business-web.netlify.app`).

## Resume command (for the next session)

```bash
# after STRIPE_SECRET_KEY=sk_test_… is in .env:
python scripts/agency/stripe_bootstrap.py --mode test      # prints STRIPE_PRICE_MAP "test" block
# paste that into .env STRIPE_PRICE_MAP, then:
python scripts/agency/create_checkout.py --product-id <id> --bundle package_a
```
