#!/usr/bin/env node
// Pull self-serve build-your-own-bundle orders from the BBW Netlify Blobs store
// into the platform under state/agency/inbound-orders/. The create-checkout
// Netlify Function writes each order to the "inbound-orders" store; this poller
// drains it locally so process_inbound_order.py can promote it to a client-site
// registry record BEFORE the matching invoice.paid reconciles (else it
// dead-letters). Mirror of scripts/web/pull-inbound.mjs.
//
//   node scripts/web/pull-orders.mjs
//
// Auth: NETLIFY_AUTH_TOKEN (env or repo .env). Site: BBW_SITE_ID env or default.
// Pulled blobs are deleted from Netlify after a local copy lands.

import { getStore } from "@netlify/blobs";
import fs from "node:fs";
import path from "node:path";

const REPO = path.resolve(import.meta.dirname, "../..");
const SITE_ID = process.env.BBW_SITE_ID || "e497b81f-1f10-468d-97b8-b27ddf6eca3b";
const OUT = path.join(REPO, "state", "agency", "inbound-orders");

function token() {
  if (process.env.NETLIFY_AUTH_TOKEN) return process.env.NETLIFY_AUTH_TOKEN;
  const envFile = path.join(REPO, ".env");
  if (fs.existsSync(envFile)) {
    const m = fs.readFileSync(envFile, "utf8").match(/^NETLIFY_AUTH_TOKEN=(.*)$/m);
    if (m) return m[1].trim().replace(/^["']|["']$/g, "");
  }
  throw new Error("NETLIFY_AUTH_TOKEN not set (env or .env)");
}

const sanitize = (id) => (String(id).replace(/[^A-Za-z0-9_-]/g, "_") || "order");

const store = getStore({ name: "inbound-orders", siteID: SITE_ID, token: token() });
const { blobs } = await store.list();
fs.mkdirSync(OUT, { recursive: true });

let pulled = 0;
for (const b of blobs) {
  const order = await store.get(b.key, { type: "json" });
  if (!order) continue;
  const id = sanitize(order.product_id || b.key);
  fs.writeFileSync(path.join(OUT, `${id}.json`), JSON.stringify(order, null, 2) + "\n");
  await store.delete(b.key);
  pulled += 1;
  console.log(`✓ pulled ${id} (${order.business})`);
}
console.log(`pulled ${pulled} inbound order(s) → ${path.relative(REPO, OUT)}/`);
