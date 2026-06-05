#!/usr/bin/env node
// Screenshot any built static site → PNG files. Reusable across every demo /
// prospect / landing site we build.
//
//   node scripts/web/shoot.mjs <distDir> <outDir> <route:name> [route:name ...]
//
// Example (from repo root, after `astro build`):
//   node scripts/web/shoot.mjs \
//     products/better-business-web/site/dist \
//     docs/products/better-business-web/screenshots \
//     /:editorial-warm /compare/luminous:luminous-dark
//
// Capture is SLICE-AND-STITCH, not Playwright's fullPage:true. Headless Chromium
// drops image layers to blank in tall single-surface captures (WebP especially),
// while a normal viewport-sized surface paints reliably. So each page is shot in
// viewport-height slices and composited on an in-browser canvas. We scroll each
// slice into view with motion ALLOWED so IntersectionObserver scroll-reveals fire
// (and settle) before capture, then hide fixed/sticky elements after the first
// slice so a sticky nav isn't redrawn down the whole page.

import http from "node:http";
import fs from "node:fs";
import path from "node:path";
import { chromium } from "playwright";
import { PNG } from "pngjs";

const [distDir, outDir, ...routeArgs] = process.argv.slice(2);
if (!distDir || !outDir || routeArgs.length === 0) {
  console.error("usage: node shoot.mjs <distDir> <outDir> <route:name> [route:name ...]");
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

const VW = 1440, SLICE = 900, MAX_PX = 16000;
const browser = await chromium.launch();

for (const arg of routeArgs) {
  const [route, name] = arg.includes(":")
    ? [arg.slice(0, arg.lastIndexOf(":")), arg.slice(arg.lastIndexOf(":") + 1)]
    : [arg, arg.replace(/\W+/g, "-")];

  const ctx = await browser.newContext({ viewport: { width: VW, height: SLICE }, deviceScaleFactor: 1 });
  const page = await ctx.newPage();
  // "load" (not networkidle) — external font CDNs can keep the network busy and
  // never idle. Then settle fonts + first paint.
  await page.goto(base + route, { waitUntil: "load" });
  await page.evaluate(() => document.fonts && document.fonts.ready).catch(() => {});
  await page.waitForTimeout(600);

  let height = await page.evaluate(() =>
    Math.max(document.body.scrollHeight, document.documentElement.scrollHeight));
  if (height > MAX_PX) { console.warn(`! ${route}: ${height}px tall, capping at ${MAX_PX}px`); height = MAX_PX; }

  const slices = [];
  for (let y = 0, i = 0; y < height; y += SLICE, i++) {
    const at = await page.evaluate((yy) => { window.scrollTo(0, yy); return Math.round(window.pageYOffset); }, y);
    if (i === 1) {
      await page.evaluate(() => {
        for (const el of document.querySelectorAll("*")) {
          const pos = getComputedStyle(el).position;
          if (pos === "fixed" || pos === "sticky") el.style.visibility = "hidden";
        }
      });
    }
    // Let scroll-reveals trigger + finish their transition, and images decode.
    await page.evaluate(() => Promise.all([...document.images].map((im) => im.decode ? im.decode().catch(() => {}) : 0)));
    await page.waitForTimeout(700);
    // Headless image rasterization is flaky here; a dropped-image slice compresses
    // tiny (a real photo slice is ~1MB). Retry such slices a few times.
    let buf = await page.screenshot();
    for (let k = 0; k < 4 && buf.length < 120_000; k++) {
      await page.waitForTimeout(500);
      buf = await page.screenshot();
    }
    slices.push({ y: at, buf });
  }
  await ctx.close();

  // Stitch in Node (an in-browser canvas hits the same headless raster bug that
  // blanks tall image surfaces). The per-slice screenshots paint reliably.
  const out = new PNG({ width: VW, height });
  for (const s of slices) {
    const png = PNG.sync.read(s.buf);
    const h = Math.min(png.height, height - s.y);
    if (h > 0) PNG.bitblt(png, out, 0, 0, Math.min(VW, png.width), h, 0, s.y);
  }
  const outFile = path.join(outDir, `${name}.png`);
  fs.writeFileSync(outFile, PNG.sync.write(out));
  console.log(`✓ ${route} → ${outFile}`);
}

await browser.close();
server.close();
