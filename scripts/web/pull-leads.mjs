#!/usr/bin/env node
// Pull each client site's contact-form leads from their own Netlify Blobs store
// ("inbound-leads") down to state/clients/<product_id>/leads/ so the lead-health
// check (packages/agency/lead_health.py + scripts/agency/check_lead_health.py)
// can flag leads that were captured but never emailed to the owner (the silent
// Resend failure behind the $49/mo "contact-form monitoring" SLA).
//
//   node scripts/web/pull-leads.mjs
//
// Targets: every client-site in infra/products.json that sells `hosting` AND has
// a recorded client.netlify_site_id (mirrors registry.lead_drain_targets — keep
// the two filters in sync). Each client's store lives on THEIR Netlify site.
//
// Copy & keep: leads are the client's durable inbox — we copy locally (and
// overwrite each run so a late notified_at stamp stays fresh) and NEVER delete
// from their store. Auth: NETLIFY_AUTH_TOKEN (env or repo .env).
//
// Exit non-zero if any target site fails (so a cron/launchd wrapper can alert).

import { getStore } from "@netlify/blobs";
import fs from "node:fs";
import path from "node:path";

const REPO = path.resolve(import.meta.dirname, "../..");
const REGISTRY = path.join(REPO, "infra", "products.json");

function token() {
  if (process.env.NETLIFY_AUTH_TOKEN) return process.env.NETLIFY_AUTH_TOKEN;
  const envFile = path.join(REPO, ".env");
  if (fs.existsSync(envFile)) {
    const m = fs.readFileSync(envFile, "utf8").match(/^NETLIFY_AUTH_TOKEN=(.*)$/m);
    if (m) return m[1].trim().replace(/^["']|["']$/g, "");
  }
  throw new Error("NETLIFY_AUTH_TOKEN not set (env or .env)");
}

const sanitize = (id) => String(id).replace(/[^A-Za-z0-9_-]/g, "_") || "lead";

// Mirror of packages.agency.registry.lead_drain_targets.
function drainTargets() {
  if (!fs.existsSync(REGISTRY)) return [];
  const records = JSON.parse(fs.readFileSync(REGISTRY, "utf8"));
  const targets = [];
  for (const rec of records) {
    if (rec?.type !== "client-site") continue;
    const client = rec.client || {};
    const siteId = String(client.netlify_site_id || "").trim();
    const services = Array.isArray(client.services) ? client.services.map(String) : [];
    if (siteId && services.includes("hosting")) {
      targets.push({ productId: String(rec.id), siteId });
    }
  }
  return targets;
}

async function drainOne(authToken, { productId, siteId }) {
  const store = getStore({ name: "inbound-leads", siteID: siteId, token: authToken });
  const { blobs } = await store.list();
  const outDir = path.join(REPO, "state", "clients", productId, "leads");
  fs.mkdirSync(outDir, { recursive: true });

  let copied = 0;
  let undelivered = 0;
  for (const b of blobs) {
    const lead = await store.get(b.key, { type: "json" });
    if (!lead) continue;
    const id = sanitize(lead.submission_id || b.key);
    // Overwrite each run so a late notified_at stamp stays current; never delete.
    fs.writeFileSync(path.join(outDir, `${id}.json`), JSON.stringify(lead, null, 2) + "\n");
    copied += 1;
    if (!lead.notified_at) undelivered += 1;
  }
  return { copied, undelivered };
}

const authToken = token();
const targets = drainTargets();
if (targets.length === 0) {
  console.log("no client-site lead-drain targets (need hosting + client.netlify_site_id)");
  process.exit(0);
}

let failures = 0;
let totalUndelivered = 0;
for (const target of targets) {
  try {
    const { copied, undelivered } = await drainOne(authToken, target);
    totalUndelivered += undelivered;
    const flag = undelivered > 0 ? ` ⚠ ${undelivered} UNDELIVERED` : "";
    console.log(`✓ ${target.productId}: ${copied} lead(s)${flag}`);
  } catch (err) {
    failures += 1;
    console.error(`✗ ${target.productId} (site ${target.siteId}): ${err.message}`);
  }
}

console.log(
  `drained ${targets.length - failures}/${targets.length} client site(s); ` +
    `${totalUndelivered} undelivered lead(s) → run check_lead_health.py for the full verdict`,
);
process.exit(failures > 0 ? 1 : 0);
