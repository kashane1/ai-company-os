#!/usr/bin/env node
// Pull verified Stripe billing events from the BBW Netlify Blobs store
// ("stripe-events", written by netlify/functions/stripe-webhook.mjs) into the
// platform as JSON files under state/agency/stripe-events/. This is the local
// drain half of the production webhook design — the Netlify Function is the stable
// endpoint, this poller pulls when the Mac is up. Mirrors scripts/web/pull-inbound.mjs.
//
//   node scripts/web/pull-stripe-events.mjs
//   # then apply them to the ledger:
//   python scripts/agency/reconcile_stripe_billing.py
//
// Auth: NETLIFY_AUTH_TOKEN (env or repo .env). Site: BBW_SITE_ID env or default.
// Pulled blobs are deleted from Netlify after a local copy lands (at-least-once;
// reconcile is idempotent, so a re-pulled event is safe).

import { getStore } from "@netlify/blobs";
import fs from "node:fs";
import path from "node:path";

const REPO = path.resolve(import.meta.dirname, "../..");
const SITE_ID = process.env.BBW_SITE_ID || "e497b81f-1f10-468d-97b8-b27ddf6eca3b";
const OUT = path.join(REPO, "state", "agency", "stripe-events");

function token() {
  if (process.env.NETLIFY_AUTH_TOKEN) return process.env.NETLIFY_AUTH_TOKEN;
  const envFile = path.join(REPO, ".env");
  if (fs.existsSync(envFile)) {
    const m = fs.readFileSync(envFile, "utf8").match(/^NETLIFY_AUTH_TOKEN=(.*)$/m);
    if (m) return m[1].trim().replace(/^["']|["']$/g, "");
  }
  throw new Error("NETLIFY_AUTH_TOKEN not set (env or .env)");
}

const sanitize = (id) => (String(id).replace(/[^A-Za-z0-9_-]/g, "_") || "event");

const store = getStore({ name: "stripe-events", siteID: SITE_ID, token: token() });
const { blobs } = await store.list();
fs.mkdirSync(OUT, { recursive: true });

let pulled = 0;
for (const b of blobs) {
  const evt = await store.get(b.key, { type: "json" });
  if (!evt) continue;
  const id = sanitize(evt.id || b.key);
  fs.writeFileSync(path.join(OUT, `${id}.json`), JSON.stringify(evt, null, 2) + "\n");
  await store.delete(b.key);
  pulled += 1;
  console.log(`✓ pulled ${id} (${evt.type}, livemode=${evt.livemode})`);
}
console.log(`pulled ${pulled} stripe event(s) → ${path.relative(REPO, OUT)}/`);
