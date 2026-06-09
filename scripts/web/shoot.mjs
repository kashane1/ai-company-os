#!/usr/bin/env node
// Screenshot any built static site → PNG files. Reusable across every demo /
// prospect / landing site we build.
//
//   node scripts/web/shoot.mjs <distDir> <outDir> <route:name> [route:name ...] [--width <px>]
//
// --width sets the capture viewport width (default 1440 desktop; pass 390 for a
// true mobile full-page shot). Capture stays full-page top-to-bottom.
//
// Example (from repo root, after `astro build`):
//   node scripts/web/shoot.mjs \
//     products/better-business-web/site/dist \
//     docs/products/better-business-web/screenshots \
//     /:editorial-warm /compare/luminous:luminous-dark
//
// Capture is a single NATIVE full-page screenshot (Playwright fullPage:true, which
// uses CDP captureBeyondViewport under the hood — one off-screen surface for the
// whole document). We previously slice-and-stitched per viewport, but that broke on
// any page with `scroll-behavior:smooth`: window.scrollTo() animates, so the
// pageYOffset read right after it returned the *pre-animation* offset and every
// slice landed ~one viewport too high — dropping the hero and duplicating the
// bottom. The native capture composites the real layout once and sidesteps all of
// that scroll bookkeeping.
//
// Two things still need care before the shot:
//   1. Scroll reveals — these builds reveal content on scroll. CSS scroll-driven
//      reveals (animation-timeline) have a `prefers-reduced-motion: reduce`
//      fallback that shows everything, so we run the context with reducedMotion:
//      "reduce". For any JS IntersectionObserver reveals we also do one full
//      scroll-through pass (then return to top) so they fire and lazy images load.
//   2. Sticky/fixed elements — in a full-page capture a `position: sticky` header
//      can smear or a fixed overlay can cover the page, so we neutralize them to
//      `position: static` first; the header then renders once at the top in flow.

import http from "node:http";
import fs from "node:fs";
import path from "node:path";
import { chromium } from "playwright";

// Pull `--width <px>` / `--width=<px>` out of argv; everything else is positional.
const rawArgs = process.argv.slice(2);
let widthArg = 1440;
const positional = [];
for (let i = 0; i < rawArgs.length; i++) {
  const a = rawArgs[i];
  if (a === "--width") { widthArg = parseInt(rawArgs[++i], 10); continue; }
  if (a.startsWith("--width=")) { widthArg = parseInt(a.slice(8), 10); continue; }
  positional.push(a);
}
const [distDir, outDir, ...routeArgs] = positional;
if (!distDir || !outDir || routeArgs.length === 0 || !Number.isFinite(widthArg)) {
  console.error("usage: node shoot.mjs <distDir> <outDir> <route:name> [route:name ...] [--width <px>]");
  process.exit(1);
}

const MIME = {
  ".html": "text/html", ".css": "text/css", ".js": "application/javascript",
  ".mjs": "application/javascript", ".json": "application/json", ".svg": "image/svg+xml",
  ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".webp": "image/webp",
  ".woff": "font/woff", ".woff2": "font/woff2", ".ttf": "font/ttf", ".ico": "image/x-icon",
  ".xml": "application/xml", ".txt": "text/plain",
};

function resolveFile(urlPath) {
  let p = decodeURIComponent(urlPath.split("?")[0]);
  let fp = path.join(distDir, p);
  if (fs.existsSync(fp) && fs.statSync(fp).isFile()) return fp;
  const idx = path.join(distDir, p, "index.html");
  if (fs.existsSync(idx)) return idx;
  if (fs.existsSync(fp + ".html")) return fp + ".html";
  return null;
}

const server = http.createServer((req, res) => {
  const fp = resolveFile(req.url);
  if (!fp) { res.writeHead(404); res.end("not found"); return; }
  const body = fs.readFileSync(fp);
  res.writeHead(200, {
    "content-type": MIME[path.extname(fp)] || "application/octet-stream",
    "content-length": body.length,
  });
  res.end(body);
});

await new Promise((r) => server.listen(0, r));
const port = server.address().port;
const base = `http://localhost:${port}`;

fs.mkdirSync(outDir, { recursive: true });

const VW = widthArg, VH = 900, MAX_PX = 16000;
const browser = await chromium.launch();

for (const arg of routeArgs) {
  const [route, name] = arg.includes(":")
    ? [arg.slice(0, arg.lastIndexOf(":")), arg.slice(arg.lastIndexOf(":") + 1)]
    : [arg, arg.replace(/\W+/g, "-")];

  // reducedMotion: "reduce" → CSS scroll-driven reveals fall back to fully visible.
  const ctx = await browser.newContext({
    viewport: { width: VW, height: VH },
    deviceScaleFactor: 1,
    reducedMotion: "reduce",
  });
  const page = await ctx.newPage();
  // "load" (not networkidle) — external font CDNs can keep the network busy and
  // never idle. Then settle fonts + first paint.
  await page.goto(base + route, { waitUntil: "load" });
  await page.evaluate(() => document.fonts && document.fonts.ready).catch(() => {});
  await page.waitForTimeout(600);

  // One scroll-through pass so JS IntersectionObserver reveals fire and any lazy
  // images start loading, then return to the top for the capture. (force auto so a
  // page-level `scroll-behavior:smooth` doesn't turn this into slow animated jumps.)
  await page.evaluate(async () => {
    document.documentElement.style.scrollBehavior = "auto";
    const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
    const docH = () => Math.max(document.body.scrollHeight, document.documentElement.scrollHeight);
    for (let y = 0; y < docH(); y += Math.round(window.innerHeight * 0.8)) {
      window.scrollTo(0, y);
      await sleep(120);
    }
    window.scrollTo(0, 0);
  });

  // Neutralize sticky/fixed so nothing smears or covers the page in the full-page
  // capture; a sticky header then renders once at the top in normal flow.
  await page.evaluate(() => {
    for (const el of document.querySelectorAll("*")) {
      const pos = getComputedStyle(el).position;
      if (pos === "fixed" || pos === "sticky") el.style.position = "static";
    }
  });

  // Decode images and let the reveal fallbacks / layout settle before the shot.
  await page.evaluate(() => Promise.all([...document.images].map((im) => (im.decode ? im.decode().catch(() => {}) : 0))));
  await page.waitForTimeout(500);

  const height = await page.evaluate(() =>
    Math.max(document.body.scrollHeight, document.documentElement.scrollHeight));
  const opts = height > MAX_PX
    ? (console.warn(`! ${route}: ${height}px tall, capping at ${MAX_PX}px`),
       { clip: { x: 0, y: 0, width: VW, height: MAX_PX } })
    : { fullPage: true };

  const buf = await page.screenshot(opts);
  await ctx.close();
  const outFile = path.join(outDir, `${name}.png`);
  fs.writeFileSync(outFile, buf);
  console.log(`✓ ${route} → ${outFile}`);
}

await browser.close();
server.close();
