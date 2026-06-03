# web/shoot — screenshots for built sites

Reusable headless-browser screenshotter. **Run this for every demo / prospect /
landing site we build** so there's always a saved visual record under
`docs/products/<product-id>/screenshots/` (don't rely on an ephemeral live
preview).

## Setup (once)

```bash
cd scripts/web
npm install
npx playwright install chromium
```

## Use

Build the site first (`astro build`), then point the tool at its `dist/`:

```bash
# from repo root
node scripts/web/shoot.mjs <distDir> <outDir> <route:name> [route:name ...]
```

Example — the Better Business Web landing site + its design options:

```bash
node scripts/web/shoot.mjs \
  products/better-business-web/site/dist \
  docs/products/better-business-web/screenshots \
  "/:editorial-warm" \
  "/compare/luminous:luminous-dark"
```

Each `route:name` writes `<outDir>/<name>.png` — a full-page capture at 1440px
wide, retina (2×). It serves the `dist/` locally (so asset paths resolve) and
emulates reduced-motion so scroll-reveal content is fully visible, not caught
mid-animation.
