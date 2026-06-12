#!/usr/bin/env node
// Screenshot + text-extract an EXTERNAL live URL → PNG + TXT.
//
//   node scripts/web/shoot_url.mjs <url> <outDir> [--name <slug>] [--width <px>]
//
// Unlike shoot.mjs (which serves a local distDir and only screenshots builds we
// made), this loads an arbitrary public URL — a prospect's own homepage — and
// writes two artifacts the teardown-teaser lane needs:
//
//   <outDir>/<name>.png   full-page screenshot of their live homepage
//   <outDir>/<name>.txt   rendered innerText (becomes Conversion Lab page_copy)
//
// The page-prep (reduced-motion, scroll-through to fire reveals + lazy images,
// neutralize sticky/fixed) mirrors shoot.mjs so the capture is comparable. Exit
// code is non-zero on a dead/blocked/timeout load so the caller can skip the
// prospect instead of emitting a blank artifact.
//
// Example:
//   node scripts/web/shoot_url.mjs https://casolas.com state/prospects/sites/PID --name homepage

import fs from "node:fs";
import path from "node:path";
import { chromium } from "playwright";

const rawArgs = process.argv.slice(2);
let widthArg = 1440;
let nameArg = "homepage";
const positional = [];
for (let i = 0; i < rawArgs.length; i++) {
  const a = rawArgs[i];
  if (a === "--width") { widthArg = parseInt(rawArgs[++i], 10); continue; }
  if (a.startsWith("--width=")) { widthArg = parseInt(a.slice(8), 10); continue; }
  if (a === "--name") { nameArg = rawArgs[++i]; continue; }
  if (a.startsWith("--name=")) { nameArg = a.slice(7); continue; }
  positional.push(a);
}
const [url, outDir] = positional;
if (!url || !outDir || !Number.isFinite(widthArg)) {
  console.error("usage: node shoot_url.mjs <url> <outDir> [--name <slug>] [--width <px>]");
  process.exit(2);
}

fs.mkdirSync(outDir, { recursive: true });

const VW = widthArg, VH = 900, MAX_PX = 16000;

// Hard wall-clock guard: a single external homepage must never hang the batch.
// Bot-walled or animation-heavy sites can keep a Promise pending forever (a broken
// image's decode(), a never-idle network), so we cap the whole capture and exit.
const HARD_TIMEOUT_MS = 45000;
const withTimeout = (p, ms, label) =>
  Promise.race([
    p,
    new Promise((_r, rej) => setTimeout(() => rej(new Error(`timeout: ${label}`)), ms)),
  ]);
const watchdog = setTimeout(() => {
  console.error(`! hard timeout (${HARD_TIMEOUT_MS}ms) capturing ${url}`);
  process.exit(4);
}, HARD_TIMEOUT_MS);
watchdog.unref();

let browser;
try {
  browser = await chromium.launch();
  const ctx = await browser.newContext({
    viewport: { width: VW, height: VH },
    deviceScaleFactor: 1,
    reducedMotion: "reduce",
    userAgent:
      "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 " +
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36",
  });
  const page = await ctx.newPage();
  page.setDefaultTimeout(20000);
  // External sites can hang on third-party network; cap the load and fall back to
  // whatever painted. "domcontentloaded" + settle beats "load" for flaky CDNs.
  const resp = await page.goto(url, { waitUntil: "domcontentloaded", timeout: 25000 });
  const status = resp ? resp.status() : 0;
  if (status >= 400) {
    console.error(`! ${url} returned HTTP ${status}`);
    await browser.close();
    process.exit(3);
  }
  await page.evaluate(() => document.fonts && document.fonts.ready).catch(() => {});
  await page.waitForTimeout(900);

  // Scroll-through so JS reveals fire and lazy images load, then back to top.
  // Bounded: a page-script that never yields can't stall the whole run.
  await withTimeout(page.evaluate(async () => {
    document.documentElement.style.scrollBehavior = "auto";
    const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
    const docH = () => Math.max(document.body.scrollHeight, document.documentElement.scrollHeight);
    for (let y = 0; y < docH(); y += Math.round(window.innerHeight * 0.8)) {
      window.scrollTo(0, y);
      await sleep(120);
    }
    window.scrollTo(0, 0);
  }), 12000, "scroll").catch(() => {});

  // Neutralize sticky/fixed so nothing smears/covers the full-page capture.
  await page.evaluate(() => {
    for (const el of document.querySelectorAll("*")) {
      const pos = getComputedStyle(el).position;
      if (pos === "fixed" || pos === "sticky") el.style.position = "static";
    }
  }).catch(() => {});

  // Decode images so the shot isn't half-blank — but a broken image's decode()
  // can hang forever, so race each one against a short in-page timeout.
  await withTimeout(page.evaluate(() => {
    const cap = (p) => Promise.race([p, new Promise((r) => setTimeout(r, 2500))]);
    return Promise.all(
      [...document.images].map((im) => (im.decode ? cap(im.decode().catch(() => {})) : 0))
    );
  }), 8000, "decode").catch(() => {});
  await page.waitForTimeout(500);

  // Extract the rendered, human-visible text (drops script/style noise).
  const text = await withTimeout(page.evaluate(() => {
    const title = document.title || "";
    const body = document.body ? document.body.innerText : "";
    return `${title}\n\n${body}`.replace(/\n{3,}/g, "\n\n").trim();
  }), 8000, "extract-text");
  const txtFile = path.join(outDir, `${nameArg}.txt`);
  fs.writeFileSync(txtFile, text);

  const height = await page.evaluate(() =>
    Math.max(document.body.scrollHeight, document.documentElement.scrollHeight));
  const opts = height > MAX_PX
    ? (console.warn(`! ${url}: ${height}px tall, capping at ${MAX_PX}px`),
       { clip: { x: 0, y: 0, width: VW, height: MAX_PX } })
    : { fullPage: true };
  const buf = await withTimeout(page.screenshot(opts), 20000, "screenshot");
  const pngFile = path.join(outDir, `${nameArg}.png`);
  fs.writeFileSync(pngFile, buf);

  console.log(JSON.stringify({
    url, status, png: pngFile, txt: txtFile,
    text_chars: text.length, height_px: height,
  }));
  clearTimeout(watchdog);
  await browser.close();
} catch (err) {
  clearTimeout(watchdog);
  console.error(`! capture failed for ${url}: ${err && err.message ? err.message : err}`);
  if (browser) { try { await browser.close(); } catch {} }
  process.exit(1);
}
