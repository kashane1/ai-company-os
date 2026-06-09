# astro-premium — the premium build stack

Phase 0 of the design engine ([docs/plans/2026-06-08-feat-design-engine-plan.md](../../../../docs/plans/2026-06-08-feat-design-engine-plan.md)).
The opt-in surface for **select, five-figure builds** — not cold-outreach demos
(those stay on `astro-landing` / the bespoke playbook).

## Shape

- **Astro, static-first** → portable `dist/`, validated by the web gate, shipped by
  the deploy lane (same as `astro-landing`).
- **Interactive/WebGL islands** via per-page `<script>` imports (Astro tree-shakes
  GSAP/Lenis/Three.js out of pages that don't use them).
- **Role-token theme** — `src/styles/design-system.css` is the theme layer the
  **design-system synthesizer** (`packages/web/design_system.py`) overwrites per
  build. `global.css` consumes only role tokens, so re-synthesis re-themes the
  whole site. Never hard-code color/type in a page or block.
- **Reduced-motion safe by construction** — every page is complete and readable
  with zero JS; `src/scripts/motion.ts` only enhances.

## What lands here later

- **Phase 2** — the full motion layer (GSAP + ScrollTrigger choreography) and the
  Three.js/WebGL hero kit expand `src/scripts/` + `src/motion/`.
- **Phase 3** — the block library (`src/blocks/`) + composer replace the inline
  sections in `index.astro` with art-directed, token-driven blocks.

## Build

Materialized into a product dir by `packages.web.scaffold.scaffold_site(target,
context, template="astro-premium")`, then `npm install && npm run build`.
