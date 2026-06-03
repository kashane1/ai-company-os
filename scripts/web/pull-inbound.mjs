#!/usr/bin/env node
// Pull inbound "website review" submissions from the BBW Netlify Blobs store
// into the platform as typed WebsiteReviewRequest records under
// state/prospects/inbound/ (todos 071/068). The Netlify Function writes each
// submission to the "inbound-reviews" store; this poller drains it locally so an
// operator/agent can run the preview/audit fulfilment.
//
//   node scripts/web/pull-inbound.mjs
//
// Auth: NETLIFY_AUTH_TOKEN (from env or repo .env). Site: BBW_SITE_ID env or the
// default below. Pulled blobs are deleted from Netlify after a local copy lands.

import { getStore } from "@netlify/blobs";
import fs from "node:fs";
import path from "node:path";

const REPO = path.resolve(import.meta.dirname, "../..");
const SITE_ID = process.env.BBW_SITE_ID || "e497b81f-1f10-468d-97b8-b27ddf6eca3b";
const OUT = path.join(REPO, "state", "prospects", "inbound");

function token() {
  if (process.env.NETLIFY_AUTH_TOKEN) return process.env.NETLIFY_AUTH_TOKEN;
  const envFile = path.join(REPO, ".env");
  if (fs.existsSync(envFile)) {
    const m = fs.readFileSync(envFile, "utf8").match(/^NETLIFY_AUTH_TOKEN=(.*)$/m);
    if (m) return m[1].trim().replace(/^["']|["']$/g, "");
  }
  throw new Error("NETLIFY_AUTH_TOKEN not set (env or .env)");
}

const sanitize = (id) => (String(id).replace(/[^A-Za-z0-9_-]/g, "_") || "review");

const store = getStore({ name: "inbound-reviews", siteID: SITE_ID, token: token() });
const { blobs } = await store.list();
fs.mkdirSync(OUT, { recursive: true });

let pulled = 0;
for (const b of blobs) {
  const sub = await store.get(b.key, { type: "json" });
  if (!sub) continue;
  const id = sanitize(sub.submission_id || b.key);
  fs.writeFileSync(path.join(OUT, `${id}.json`), JSON.stringify(sub, null, 2) + "\n");
  await store.delete(b.key);
  pulled += 1;
  console.log(`✓ pulled ${id} (${sub.business || sub.name})`);
}
console.log(`pulled ${pulled} inbound review(s) → ${path.relative(REPO, OUT)}/`);
