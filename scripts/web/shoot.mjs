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
// It serves the dist locally (no asset-path breakage), loads each route with a
// real headless browser, emulates reduced-motion so scroll-reveal content is
// fully visible, waits for fonts, and writes a full-page PNG per route.

import http from "node:http";
import fs from "node:fs";
import path from "node:path";
import { chromium } from "playwright";

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
  // Pretty routes: /foo -> /foo/index.html, / -> /index.html
  const idx = path.join(distDir, p, "index.html");
  if (fs.existsSync(idx)) return idx;
  if (fs.existsSync(fp + ".html")) return fp + ".html";
  return null;
}

const server = http.createServer((req, res) => {
  const fp = resolveFile(req.url);
  if (!fp) { res.writeHead(404); res.end("not found"); return; }
  res.writeHead(200, { "content-type": MIME[path.extname(fp)] || "application/octet-stream" });
  fs.createReadStream(fp).pipe(res);
});

await new Promise((r) => server.listen(0, r));
const port = server.address().port;
const base = `http://localhost:${port}`;

fs.mkdirSync(outDir, { recursive: true });

const browser = await chromium.launch();
const ctx = await browser.newContext({
  viewport: { width: 1440, height: 900 },
  deviceScaleFactor: 2,
  reducedMotion: "reduce", // reveal-on-scroll content shows immediately, no mid-animation
});
const page = await ctx.newPage();

for (const arg of routeArgs) {
  const [route, name] = arg.includes(":") ? [arg.slice(0, arg.lastIndexOf(":")), arg.slice(arg.lastIndexOf(":") + 1)] : [arg, arg.replace(/\W+/g, "-")];
  const url = base + route;
  await page.goto(url, { waitUntil: "networkidle" });
  await page.evaluate(() => document.fonts && document.fonts.ready);
  await page.waitForTimeout(350);
  const out = path.join(outDir, `${name}.png`);
  await page.screenshot({ path: out, fullPage: true });
  console.log(`✓ ${route} → ${out}`);
}

await browser.close();
server.close();
