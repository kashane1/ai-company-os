# {{SITE_NAME}} — web product

Astro static-first landing site, scaffolded by the platform's WEB lane
(`packages/web/scaffold.py`). Built and validated by `apps/worker-web`, shipped
by `apps/worker-webdeploy` behind the deploy gate.

## Local

```bash
npm ci
npm run build      # → dist/  (what the web gate validates)
npm run preview    # serve the built site locally
```

## Structure

- `src/pages/index.astro` — the landing page (plain, responsive HTML).
- `src/styles/global.css` — the fluid, themeable design system. Change `--brand`
  in `:root` to re-skin; everything else scales from there.
- `astro.config.mjs` — static output; `site` is set at deploy time.

## Design notes

Mobile-first and responsive by construction: fluid `clamp()` type, `auto-fit`
grids, comfortable touch targets, dark-mode via `prefers-color-scheme`, and
`prefers-reduced-motion` honored. The web gate enforces a `width=device-width`
viewport and baseline accessibility on every page.
