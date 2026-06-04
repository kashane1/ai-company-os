// Netlify serverless function — verify Stripe webhook events.
// On a completed checkout we have a real paid conversion: the strongest
// willingness-to-pay signal. Forward it to the platform's paid-validation
// experiment (packages/web/stripe_monetization.record_checkout_outcome).
// Env (set in Netlify): STRIPE_SECRET_KEY, STRIPE_WEBHOOK_SECRET.
// Optional agency retainer forwarding:
//   AGENCY_STRIPE_EVENT_FORWARD_URL, AGENCY_STRIPE_EVENT_FORWARD_SECRET.
import Stripe from "stripe";

export async function handler(event) {
  const key = process.env.STRIPE_SECRET_KEY;
  const secret = process.env.STRIPE_WEBHOOK_SECRET;
  if (!key || !secret) {
    return { statusCode: 503, body: "payments not configured" };
  }
  const stripe = new Stripe(key);
  let evt;
  try {
    evt = stripe.webhooks.constructEvent(
      event.body,
      event.headers["stripe-signature"],
      secret,
    );
  } catch (err) {
    return { statusCode: 400, body: `Webhook Error: ${err.message}` };
  }

  if (process.env.AGENCY_STRIPE_EVENT_FORWARD_URL) {
    const o = evt.data.object || {};
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
          // dispute/refund reconciliation needs these (charge.refunded.refunded,
          // charge link). The receiver still re-verifies + may enrich.
          refunded: o.refunded ?? null,
          charge: o.charge || "",
          metadata: o.metadata || {},
        },
      },
    };
    // [B4] The forward must NOT be fire-and-forget: if the platform endpoint is
    // down or slow, return a non-2xx so Stripe RETRIES (its retry schedule is our
    // durable async queue). A swallowed forward = a permanently lost payment.
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), 4000);
    try {
      const res = await fetch(process.env.AGENCY_STRIPE_EVENT_FORWARD_URL, {
        method: "POST",
        headers: {
          "content-type": "application/json",
          "x-agency-forward-secret": process.env.AGENCY_STRIPE_EVENT_FORWARD_SECRET || "",
        },
        body: JSON.stringify(payload),
        signal: controller.signal,
      });
      if (!res.ok) {
        console.error("forward failed", res.status);
        return { statusCode: 502, body: "forward failed" };
      }
    } catch (err) {
      console.error("forward threw", err?.name || err);
      return { statusCode: 502, body: "forward error" };
    } finally {
      clearTimeout(timer);
    }
  } else if (evt.type === "checkout.session.completed") {
    // Integration point: record one paid conversion for {{SITE_NAME}}.
    console.log("paid conversion", evt.data.object.id);
  }
  return { statusCode: 200, body: JSON.stringify({ received: true }) };
}
