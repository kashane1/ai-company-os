// Netlify serverless function — verify Stripe webhook events.
// On a completed checkout we have a real paid conversion: the strongest
// willingness-to-pay signal. Forward it to the platform's paid-validation
// experiment (packages/web/stripe_monetization.record_checkout_outcome).
// Env (set in Netlify): STRIPE_SECRET_KEY, STRIPE_WEBHOOK_SECRET.
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

  if (evt.type === "checkout.session.completed") {
    // Integration point: record one paid conversion for {{SITE_NAME}}.
    // e.g. POST to the platform endpoint that calls record_checkout_outcome.
    console.log("paid conversion", evt.data.object.id);
  }
  return { statusCode: 200, body: JSON.stringify({ received: true }) };
}
