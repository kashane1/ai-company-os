# Smarter Demo Sites — Plan

**Status:** in progress. Runs *before* the Better Business Web landing page
(it improves both the client previews and that page's portfolio).
**Related:** [prospect_site.py](../../packages/agency/prospect_site.py) ·
[scaffold.py](../../packages/web/scaffold.py) ·
[waas-prospecting-lane.md](../waas-prospecting-lane.md) ·
[LANDING_PAGE_PLAN.md](../products/better-business-web/LANDING_PAGE_PLAN.md)

## Goal

Today every preview demo is the **same template** with only copy/colors swapped —
244 sites that look identical. Make each demo feel purpose-built for its business
and genre, so a prospect sees a credible, tailored site (and the landing-page
portfolio shows real variety).

## Decisions (operator, locked)

1. **Heuristic only — no Places Photo API.** We do **not** fetch photos, read
   signs, or analyze real imagery (avoids per-fetch billing + ToS). Instead the
   engine derives a distinct, genre-appropriate identity **deterministically**
   from data already in the scan (genre, business name, place_id). *Honest
   caveat: this is not "reading their actual branding from photos" — it is a
   smart, varied, genre-matched look generated offline.*
2. **Fonts: genre style-class → curated Google Font.** Each genre maps to a
   style class (industrial / trades / vintage / elegant / warm / playful / calm /
   friendly / professional); each class has a curated heading+body Google Font
   pairing. No exact-typeface guessing.
3. **Multiple real layout variants.** Several genuinely different layouts
   (e.g. split / centered / banner / editorial), assigned per business, not just
   recolored sections.

## Design

A new pure module **`packages/agency/demo_theme.py`** (no network, deterministic):

- `DemoTheme` dataclass: palette (CSS-var overrides), heading/body fonts +
  Google Fonts import URL + font stacks, and a `layout` variant name.
- `STYLE_PROFILES: dict[genre_id, StyleProfile]` — per-genre base hue, neutral
  temperature (warm/cool), font pairing(s), and eligible layouts.
- `theme_for_record(record) -> DemoTheme` — deterministic from a stable hash of
  `place_id`, so re-runs are stable and two same-genre businesses still differ
  (hue rotation + layout/pairing pick).
- `theme_style_block(theme) -> str` — emits the `<link>`/`<style>` that overrides
  `:root` palette vars, sets `--font-heading`/`--font-body`, and carries the
  per-layout CSS.
- Pure helpers: HSL→hex, relative luminance → pick `--brand-contrast`, derive
  `--brand-strong`/accent, keep WCAG-ish contrast.

**Integration** stays inside the agency layer (generic `scaffold.py` untouched):
`prospect_site.render_preview_html` post-processes the rendered HTML — appends the
theme style block after the inlined `global.css` (cascade wins), and stamps
`data-layout="…"` on `<body>` so the layout CSS applies. `preview.json` records
the chosen `theme` (layout, fonts, palette) for transparency.

**Layout variants** are CSS-driven over the existing semantic markup (hero
arrangement, type scale, section emphasis/order, hero-visual motif) so they look
distinct without forking the template per business.

## Genre → style map (initial)

| Genre(s) | Style class | Heading / Body | Mood |
|---|---|---|---|
| auto_repair, garage_door | industrial | Oswald / Inter | steel + bold accent |
| plumber, electrician, roofer, landscaper, house_cleaning | trades | Archivo / Inter | utility blue/green |
| barber_shop | vintage | Bebas Neue / Inter | dark + amber/cream |
| beauty_salon, nail_salon, massage_therapy | elegant | Playfair Display / Nunito Sans | rose/mauve |
| bakery, coffee_shop, restaurant | warm | Fraunces / Nunito | warm browns/terracotta |
| dog_groomer | playful | Baloo 2 / Nunito | teal/coral |
| yoga_studio | calm | Cormorant Garamond / Mulish | sage/stone |
| tutoring, music_lessons | friendly | Poppins / Inter | bright primary |
| accountant, notary | professional | Spectral / Inter | navy/slate |
| (fallback) | default | Manrope / Inter | indigo |

## Build steps

1. `demo_theme.py` + unit tests (determinism, contrast, every genre maps, valid
   layout names). ← start here
2. Integrate into `render_preview_html`; record `theme` in `preview.json`; render
   guard still rejects unfilled tokens.
3. Layout-variant CSS (split / centered / banner / editorial).
4. Regenerate all built demos locally (no network, no cost) and spot-check.

## Out of scope (this task)

- Any real photo fetching / vision analysis (explicitly declined above).
- The landing page itself (separate, after this).
