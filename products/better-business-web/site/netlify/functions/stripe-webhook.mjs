// Netlify Function — production Stripe billing webhook for the agency layer.
//
// Design (mirrors website-review.mjs + the inbound-leads pattern): this is the
// STABLE, self-contained webhook endpoint under the deployed Netlify site. It does
// NOT forward to the local Mac over a tunnel — instead it verifies the Stripe
// signature and writes each verified, reshaped event to a Netlify Blobs store
// ("stripe-events"). A local poller (scripts/web/pull-stripe-events.mjs) drains
// the store into state/agency/stripe-events/*.json when the Mac is up, and
// scripts/agency/reconcile_stripe_billing.py applies them to the local ledger.
// The Blob is the durable record — the Mac being offline never loses a payment
// (Stripe also retries non-2xx for ~3 days as a second safety net).
//
// Env (set in Netlify only — never PUBLIC_/VITE_, never in dist/):
//   STRIPE_WEBHOOK_SECRET_TEST and/or STRIPE_WEBHOOK_SECRET_LIVE  (whsec_…)
//   (legacy STRIPE_WEBHOOK_SECRET also accepted). One function URL can back both a
//   test AND a live Stripe endpoint — we try each configured secret until one
//   verifies, so test and live events are both accepted and tagged by livemode.
//
// Idempotency: events are keyed by Stripe event id in the store; the local
// reconcile (billing.py) is itself idempotent (processed_event_ids) and has a
// test/live mode-fence, so a redelivered or duplicated event is safe end-to-end.

import { getStore } from "@netlify/blobs";
import Stripe from "stripe";

// Minimum events for the three bundles' billing lifecycle. Anything else is
// acknowledged (200) and ignored so Stripe doesn't retry noise.
const HANDLED = new Set([
  "invoice.paid",
  "invoice.payment_failed",
  "customer.subscription.updated",
  "customer.subscription.deleted",
  "charge.dispute.created",
  "charge.dispute.closed",
  "charge.refunded",
  "checkout.session.completed",
]);

const ok = (body) => new Response(JSON.stringify(body), { status: 200, headers: { "content-type": "application/json" } });

function webhookSecrets() {
  // Order matters only for try-sequence; both are valid. Legacy single var last.
  return [
    process.env.STRIPE_WEBHOOK_SECRET_TEST,
    process.env.STRIPE_WEBHOOK_SECRET_LIVE,
    process.env.STRIPE_WEBHOOK_SECRET,
  ].filter(Boolean);
}

// Verify against each configured secret; return the verified event or null.
function verify(stripe, rawBody, sig, secrets) {
  for (const secret of secrets) {
    try {
      return stripe.webhooks.constructEvent(rawBody, sig, secret);
    } catch {
      /* try the next secret */
    }
  }
  return null;
}

export default async (req) => {
  if (req.method !== "POST") return new Response("Method not allowed", { status: 405 });

  const secrets = webhookSecrets();
  if (secrets.length === 0) {
    console.error("stripe webhook not configured (no STRIPE_WEBHOOK_SECRET_* set)");
    return new Response("payments not configured", { status: 503 });
  }

  const rawBody = await req.text(); // raw text required for signature verification
  const sig = req.headers.get("stripe-signature") || "";
  const stripe = new Stripe(process.env.STRIPE_SECRET_KEY || "sk_unused", { apiVersion: "2024-06-20" });

  const evt = verify(stripe, rawBody, sig, secrets);
  if (!evt) {
    console.error("stripe signature verification failed");
    return new Response("invalid signature", { status: 400 });
  }

  // Acknowledge (and don't store) events outside the billing allowlist.
  if (!HANDLED.has(evt.type)) return ok({ received: true, ignored: evt.type });

  const o = evt.data.object || {};
  // Reshape to exactly what billing.py reconcile expects (see stripe_receiver/
  // billing.py). Metadata rides on subscription_data → present on most objects;
  // invoice.paid carries none, and billing.py falls back by subscription/customer.
  const payload = {
    id: evt.id,
    type: evt.type,
    created: evt.created,
    livemode: evt.livemode,
    data: {
      object: {
        id: o.id,
        customer: o.customer || "",
        subscription: o.subscription || "",
        latest_invoice: o.latest_invoice || "",
        status: o.status || "",
        refunded: o.refunded ?? null,
        charge: o.charge || "",
        metadata: o.metadata || {},
      },
    },
  };

  // PERSIST FIRST — the durable record. Key by event id (idempotent overwrite).
  // A non-2xx here makes Stripe retry (its queue is our async durability).
  try {
    const store = getStore("stripe-events");
    await store.setJSON(evt.id, payload);
  } catch (err) {
    console.error("stripe-events blob write failed", err);
    return new Response("could not store event", { status: 500 });
  }

  return ok({ received: true, stored: evt.id });
};
