// Netlify Function — self-serve Build-Your-Own-Bundle checkout.
//
// The buy-now path for the /build configurator. The client sends a list of
// service_ids (+ an optional preset_id hint) and light identity; this function
// RECOMPUTES the price server-side from the drift-guarded packages.json (never
// trusting any client amount), persists the order to Netlify Blobs, creates a
// Stripe Checkout Session with inline price_data, and returns its URL.
//
// This is the first .mjs that mutates Stripe state + computes money, so it leans
// hard on shared, tested logic: pricing.mjs is the JS twin of Python
// quote_services (cross-language golden test), and the metadata shape mirrors
// packages/agency/payments.py so billing.py reconciliation stays generic.
//
// Env (Netlify only — never PUBLIC_/VITE_, never in dist/):
//   BYO_LIVE_ENABLED            "true" (exactly) enables live; anything else = test
//   STRIPE_SECRET_KEY_TEST      sk_test_…   (legacy STRIPE_SECRET_KEY accepted for test)
//   STRIPE_SECRET_KEY_LIVE      sk_live_…
//   RESEND_API_KEY / LEAD_NOTIFY_EMAIL / LEAD_FROM_EMAIL  (best-effort notify)

import { getStore } from "@netlify/blobs";
import Stripe from "stripe";

import { quoteServices, servicesById } from "../../src/lib/pricing.mjs";
import packages from "../../src/data/packages.json" with { type: "json" };

const SITE = "https://better-business-web.netlify.app";
const SUCCESS_URL = `${SITE}/welcome/`; // PAID success page (not /thanks/)
const CANCEL_URL = `${SITE}/build/`;
const MAX_DUE_TODAY_CENTS = 1_000_000; // $10k backstop — real bundles are << this

const json = (body, status = 200) =>
  new Response(JSON.stringify(body), { status, headers: { "content-type": "application/json" } });

const esc = (s) =>
  String(s ?? "").replace(/[&<>"']/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]),
  );

const slugify = (s) =>
  String(s || "")
    .toLowerCase()
    .replace(/['’"]/g, "")
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, 40) || "client";

// Resolve test/live mode + secret key server-side. Fail-closed: only the literal
// string "true" enables live, and the selected key's prefix must match the mode.
function resolveStripe() {
  const live = process.env.BYO_LIVE_ENABLED === "true";
  const mode = live ? "live" : "test";
  const key = live
    ? process.env.STRIPE_SECRET_KEY_LIVE
    : process.env.STRIPE_SECRET_KEY_TEST || process.env.STRIPE_SECRET_KEY;
  if (!key) return { error: "payments not configured" };
  const wantPrefix = live ? "sk_live_" : "sk_test_";
  if (!key.startsWith(wantPrefix)) {
    return { error: `stripe key does not match ${mode} mode` };
  }
  return { mode, stripe: new Stripe(key, { apiVersion: "2024-06-20" }) };
}

// Normalize + validate the requested service_ids against the catalog. Only
// self-serve services may be bought here; unknown/non-self-serve are rejected
// (UI exclusion is not a control). Returns {ids} or {error}.
function normalizeServiceIds(raw, byId) {
  if (!Array.isArray(raw) || raw.length === 0) return { error: "no services selected" };
  const seen = new Set();
  const ids = [];
  for (const v of raw) {
    const id = String(v);
    const svc = byId[id];
    if (!svc) return { error: `unknown service: ${id}` };
    if (!svc.self_serve) return { error: `service not available self-serve: ${id}` };
    if (!seen.has(id)) {
      seen.add(id);
      ids.push(id);
    }
  }
  if (ids.length > Object.keys(byId).length) return { error: "too many services" };
  return { ids };
}

// If the (normalized) selection exactly matches a preset's service set, return
// that bundle so its curated promo applies. preset_id is only a hint.
function matchPreset(ids, presetId, bundles) {
  const set = new Set(ids);
  for (const b of bundles) {
    if (presetId && b.id !== presetId) continue;
    if (b.service_ids.length === set.size && b.service_ids.every((s) => set.has(s))) {
      return b;
    }
  }
  return null;
}

async function notifyOrder(order) {
  const apiKey = process.env.RESEND_API_KEY;
  if (!apiKey) return null;
  const to = process.env.LEAD_NOTIFY_EMAIL || "ksakhakorn@gmail.com";
  const from = process.env.LEAD_FROM_EMAIL || "Lead Bot <onboarding@resend.dev>";
  const looksEmail = /^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(order.contact || "");
  try {
    const res = await fetch("https://api.resend.com/emails", {
      method: "POST",
      headers: {
        Authorization: `Bearer ${apiKey}`,
        "Content-Type": "application/json",
        "Idempotency-Key": `order-${order.product_id}`,
      },
      body: JSON.stringify({
        from,
        to,
        ...(looksEmail ? { reply_to: order.contact } : {}),
        subject: `New bundle order: ${order.business} (${order.bundle})`,
        html: [
          "<h2>New build-your-own-bundle order</h2>",
          `<p><strong>Business:</strong> ${esc(order.business)}</p>`,
          `<p><strong>Contact:</strong> ${esc(order.contact)}</p>`,
          `<p><strong>Bundle:</strong> ${esc(order.bundle)} (${order.mode})</p>`,
          `<p><strong>Services:</strong> ${esc(order.service_ids.join(", "))}</p>`,
          `<p><strong>Setup:</strong> $${(order.setup_after_cents / 100).toFixed(2)} · ` +
            `<strong>Monthly:</strong> $${(order.monthly_cents / 100).toFixed(2)}</p>`,
          `<p><strong>Product ID:</strong> <code>${esc(order.product_id)}</code></p>`,
          "<hr><pre>node scripts/web/pull-orders.mjs\n" +
            `python scripts/agency/process_inbound_order.py --id ${esc(order.product_id)}</pre>`,
        ].join("\n"),
      }),
    });
    if (!res.ok) return null;
    return (await res.json())?.id ?? null;
  } catch {
    return null;
  }
}

export default async (req) => {
  if (req.method !== "POST") return new Response("Method not allowed", { status: 405 });

  let body;
  try {
    body = await req.json();
  } catch {
    return json({ error: "bad request" }, 400);
  }

  // Honeypot — silently accept-and-drop obvious bots (no session, no order).
  if (body.bot_field) return json({ ok: true });

  const business = String(body.business || "").trim().slice(0, 200);
  const contact = String(body.contact || "").trim().slice(0, 200);
  if (!business || !contact) return json({ error: "missing business or contact" }, 400);

  const byId = servicesById(packages.services);
  const norm = normalizeServiceIds(body.service_ids, byId);
  if (norm.error) return json({ error: norm.error }, 400);

  const preset = matchPreset(norm.ids, body.preset_id ?? null, packages.bundles);
  const quote = quoteServices(
    norm.ids,
    byId,
    packages.discount_tiers,
    preset ? preset.setup_after_cents : null,
  );

  const dueToday = quote.setupAfterCents + quote.monthlyCents;
  if (dueToday <= 0 || dueToday > MAX_DUE_TODAY_CENTS) {
    return json({ error: "invalid total" }, 400);
  }

  const { mode, stripe, error } = resolveStripe();
  if (error) return json({ error }, 503);

  const productId = `${slugify(business)}-${slugify(String(body.nonce || "")).slice(0, 8) || "order"}`;
  const bundle = preset ? preset.id : "custom";
  const metadata = {
    product_id: productId,
    bundle,
    service_ids: norm.ids.join(",").slice(0, 480),
    mode,
    source: "byo",
  };

  // Build inline price_data line items. Subscription mode requires >=1 recurring
  // line; a setup-only cart falls back to payment mode.
  const lineItems = [];
  if (quote.monthlyCents > 0) {
    lineItems.push({
      quantity: 1,
      price_data: {
        currency: "usd",
        unit_amount: quote.monthlyCents,
        recurring: { interval: "month" },
        product_data: { name: "Monthly services" },
      },
    });
  }
  if (quote.setupAfterCents > 0) {
    lineItems.push({
      quantity: 1,
      price_data: {
        currency: "usd",
        unit_amount: quote.setupAfterCents,
        product_data: { name: "Setup (one-time)" },
      },
    });
  }
  const checkoutMode = quote.monthlyCents > 0 ? "subscription" : "payment";

  const order = {
    product_id: productId,
    business,
    contact,
    service_ids: norm.ids,
    bundle,
    mode,
    setup_gross_cents: quote.setupGrossCents,
    setup_after_cents: quote.setupAfterCents,
    monthly_cents: quote.monthlyCents,
    received_at: new Date().toISOString(),
    source: "netlify-function",
    session_id: null,
  };

  // 1) PERSIST FIRST — the durable order record (only this path may 500).
  const store = getStore("inbound-orders");
  try {
    await store.setJSON(productId, order);
  } catch (err) {
    console.error("order blob write failed", err);
    return json({ error: "could not store order" }, 500);
  }

  // 2) Create the Checkout Session. Idempotency key derived from the normalized
  // cart + nonce so a double-click collapses but a changed cart is fresh.
  const idemKey = `byo:${productId}:${checkoutMode}:${[...norm.ids].sort().join(",")}:${quote.setupAfterCents}:${quote.monthlyCents}`.slice(0, 200);
  let session;
  try {
    session = await stripe.checkout.sessions.create(
      {
        mode: checkoutMode,
        line_items: lineItems,
        metadata,
        ...(checkoutMode === "subscription"
          ? { subscription_data: { metadata } }
          : {}),
        success_url: SUCCESS_URL,
        cancel_url: CANCEL_URL,
        expires_at: Math.floor(Date.now() / 1000) + 30 * 60,
      },
      { idempotencyKey: idemKey },
    );
  } catch (err) {
    console.error("stripe checkout create failed", err?.message || err);
    return json({ error: "could not start checkout" }, 502);
  }

  // 3) Best-effort: stamp the session id + notify (never fatal).
  try {
    await store.setJSON(productId, { ...order, session_id: session.id });
  } catch (err) {
    console.error("order stamp write failed (non-fatal)", err);
  }
  await notifyOrder(order);

  return json({ url: session.url, product_id: productId });
};
