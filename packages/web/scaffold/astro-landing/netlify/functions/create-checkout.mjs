// Netlify serverless function — create a Stripe Checkout session.
// The browser POSTs here; we return a hosted Checkout URL to redirect to.
// Env (set in Netlify, never committed): STRIPE_SECRET_KEY, STRIPE_PRICE_ID.
// Test mode (sk_test_…) needs no approval; live mode is gated by the platform.
import Stripe from "stripe";

export async function handler(event) {
  if (event.httpMethod !== "POST") {
    return { statusCode: 405, body: "Method Not Allowed" };
  }
  const key = process.env.STRIPE_SECRET_KEY;
  if (!key) {
    return { statusCode: 503, body: JSON.stringify({ error: "payments not configured" }) };
  }
  const stripe = new Stripe(key);
  const base = process.env.URL || "{{SITE_URL}}";
  try {
    const session = await stripe.checkout.sessions.create({
      mode: "payment",
      line_items: [{ price: process.env.STRIPE_PRICE_ID || "{{STRIPE_PRICE_ID}}", quantity: 1 }],
      success_url: `${base}/?checkout=success`,
      cancel_url: `${base}/?checkout=cancel`,
    });
    return { statusCode: 200, body: JSON.stringify({ url: session.url }) };
  } catch (err) {
    return { statusCode: 500, body: JSON.stringify({ error: err.message }) };
  }
}
