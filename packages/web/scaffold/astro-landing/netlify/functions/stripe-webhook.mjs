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
    const payload = {
      id: evt.id,
      type: evt.type,
      created: evt.created,
      livemode: evt.livemode,
      data: {
        object: {
          id: evt.data.object.id,
          customer: evt.data.object.customer || "",
          subscription: evt.data.object.subscription || "",
          latest_invoice: evt.data.object.latest_invoice || "",
          status: evt.data.object.status || "",
          metadata: evt.data.object.metadata || {},
        },
      },
    };
    await fetch(process.env.AGENCY_STRIPE_EVENT_FORWARD_URL, {
      method: "POST",
      headers: {
        "content-type": "application/json",
        "x-agency-forward-secret": process.env.AGENCY_STRIPE_EVENT_FORWARD_SECRET || "",
      },
      body: JSON.stringify(payload),
    });
  } else if (evt.type === "checkout.session.completed") {
    // Integration point: record one paid conversion for {{SITE_NAME}}.
    console.log("paid conversion", evt.data.object.id);
  }
  return { statusCode: 200, body: JSON.stringify({ received: true }) };
}
