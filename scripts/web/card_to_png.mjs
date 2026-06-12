#!/usr/bin/env node
// Render a single local HTML file → PNG. Used for the teardown-teaser annotated
// card (their homepage screenshot + 3 finding callouts laid over it). shoot.mjs
// can't do this — it screenshots a whole served distDir at a route, whereas here
// we want one self-contained HTML file (with a local image referenced relatively)
// captured at its natural size.
//
//   node scripts/web/card_to_png.mjs <htmlFile> <outPng> [--width <px>]
//
// The HTML file is served from its own directory (so a relative <img src> to the
// homepage PNG resolves), loaded, and captured full-page. --width sets the layout
// width (default 1200).
//
// Example:
//   node scripts/web/card_to_png.mjs \
//     state/prospects/sites/PID/teaser-card.html \
//     state/prospects/sites/PID/teaser-card.png --width 1200

import http from "node:http";
import fs from "node:fs";
import path from "node:path";
import { chromium } from "playwright";

const rawArgs = process.argv.slice(2);
let widthArg = 1200;
const positional = [];
for (let i = 0; i < rawArgs.length; i++) {
  const a = rawArgs[i];
  if (a === "--width") { widthArg = parseInt(rawArgs[++i], 10); continue; }
  if (a.startsWith("--width=")) { widthArg = parseInt(a.slice(8), 10); continue; }
  positional.push(a);
}
const [htmlFile, outPng] = positional;
if (!htmlFile || !outPng || !Number.isFinite(widthArg)) {
  console.error("usage: node card_to_png.mjs <htmlFile> <outPng> [--width <px>]");
  process.exit(2);
}
if (!fs.existsSync(htmlFile)) {
  console.error(`! no such file: ${htmlFile}`);
  process.exit(2);
}

const serveDir = path.dirname(path.resolve(htmlFile));
const entry = path.basename(htmlFile);

const MIME = {
  ".html": "text/html", ".css": "text/css", ".js": "application/javascript",
  ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
  ".webp": "image/webp", ".svg": "image/svg+xml", ".woff2": "font/woff2",
};

const server = http.createServer((req, res) => {
  const rel = decodeURIComponent((req.url || "/").split("?")[0]);
  const fp = path.join(serveDir, rel === "/" ? entry : rel);
  if (!fp.startsWith(serveDir) || !fs.existsSync(fp) || !fs.statSync(fp).isFile()) {
    res.writeHead(404); res.end("not found"); return;
  }
  const body = fs.readFileSync(fp);
  res.writeHead(200, { "content-type": MIME[path.extname(fp)] || "application/octet-stream" });
  res.end(body);
});
await new Promise((r) => server.listen(0, r));
const port = server.address().port;

let browser;
try {
  browser = await chromium.launch();
  const ctx = await browser.newContext({
    viewport: { width: widthArg, height: 900 },
    deviceScaleFactor: 2,
  });
  const page = await ctx.newPage();
  await page.goto(`http://localhost:${port}/`, { waitUntil: "load", timeout: 20000 });
  await page.evaluate(() => document.fonts && document.fonts.ready).catch(() => {});
  await page.evaluate(() =>
    Promise.all([...document.images].map((im) => (im.decode ? im.decode().catch(() => {}) : 0)))
  ).catch(() => {});
  await page.waitForTimeout(300);
  fs.mkdirSync(path.dirname(path.resolve(outPng)), { recursive: true });
  await page.screenshot({ path: outPng, fullPage: true });
  console.log(JSON.stringify({ html: htmlFile, png: outPng }));
  await browser.close();
} catch (err) {
  console.error(`! card render failed: ${err && err.message ? err.message : err}`);
  if (browser) { try { await browser.close(); } catch {} }
  server.close();
  process.exit(1);
}
server.close();
