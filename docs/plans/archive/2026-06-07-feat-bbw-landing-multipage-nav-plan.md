---
title: BBW landing — split into multi-page site with a scroll-away brand banner + sticky nav
type: feat
date: 2026-06-07
status: done
owner: kashane
related:
  - products/better-business-web/site/src/components/LandingBody.astro
  - products/better-business-web/site/src/pages/index.astro
  - products/better-business-web/site/src/pages/build.astro
  - products/better-business-web/site/src/styles/global.css
  - products/better-business-web/site/netlify/functions/website-review.mjs
  - docs/agency/README.md
---

# 🧭 BBW landing → multi-page + scroll-away banner + sticky nav

> **TL;DR.** Today the BBW funnel is **one 343-line single page** (`LandingBody.astro`)
> held together by `#anchor` links and a scroll-reveal system, and four pages each
> re-declare their own `<head>`. This splits it into **focused short pages** —
> *Intro · Demos · Pricing · Free review* — with shared chrome: a **scroll-away
> brand banner** (the *b* icon + "Better Business Web", large on desktop) above a
> **uniform nav** (no accent CTA) that **rests under the banner on load and pins to
> the top once the banner scrolls past** via native `position: sticky` — **zero JS
> for the pin**. A *b* mark **fades into the nav when it pins** (opacity-only, a
> permanently-reserved fixed-width slot so the bar **never shifts**), and a faint
> shadow appears when stuck — both driven by **one sentinel + IntersectionObserver**.
> Anchors → real routes; scroll-reveal/progress-bar/header-shrink removed (content
> renders statically). The keystone is a shared **`Site.astro` layout** (head +
> banner + nav + footer + `<slot/>`).
>
> **Deepened + reviewed 2026-06-07** — 3 best-practice research passes (CSS sticky,
> accessible nav, Astro layout) + 3 reviews (architecture, simplicity, frontend/a11y).
> All P1/P2 folded in; cited specifics in [Research insights](#research-insights).

## Enhancement summary (what the review changed)

- **Form-redirect model corrected (P1):** the review form posts to
  `action="/.netlify/functions/website-review"` (verbatim) and the redirect to
  `/thanks/` is **server-side** (a 303 from the function). Migration rule: move the
  `<form>` markup **unchanged** — do *not* repoint the action to a page route.
- **Silent-content-loss landmine (P1):** `[data-reveal]` is `opacity:0` by default
  in `global.css` and only un-hidden by JS. Removing the reveal JS while leaving
  any `data-reveal` attribute + that CSS makes content **permanently invisible**.
  Fix: strip the attributes, the JS, and the CSS **in lockstep, per page**.
- **Script entanglement (P1):** the carousel IIFE reads a shared `reduce` const, and
  a `.pf-thumb` image-loader is wedged in the same `<script>` and belongs on
  `/demos`, not Intro. Each page's script must be made self-contained.
- **`build`/`welcome`/`thanks` are full HTML docs (P1):** `welcome`/`thanks` import
  the *editorial* fonts and render without `theme-luminous` — wrapping them in the
  layout is a **visible (correct) restyle**, not a no-op; flag it for the screenshot
  review. `BundleBuilder.css` stays page-local.
- **Sticky-killer list expanded + verified against the real CSS (P1/P2):** the
  enemy is broader than `overflow`/`transform`, and `body { overflow-x: hidden }`
  already exists (line 72) — must be validated against the pin.
- **CSS strategy split (P2):** new chrome (nav/banner) → **component-scoped**
  `<style>`; shared section/card/form/footer classes → stay in `global.css`. Delete
  the old `.site-header`/`.nav-cta` block once all pages migrate.
- **Sequencing reordered (P2):** "split content" and "strip dead JS/CSS" are the
  **same operation, per page** — not two phases.
- **Deferred to "Later":** `@astrojs/sitemap`, old-anchor redirects, Astro View
  Transitions, and the CSS `scroll-state(stuck:)` progressive enhancement.

**Two reviewer recommendations I'm *not* taking (they conflict with your explicit
choices):** (1) the simplicity pass argued to **drop the `b`-mark fade + sentinel
entirely** — you explicitly want it, so it stays (built carefully per the no-shift
spec below). (2) It argued to **keep the form on Intro** and make `/free-review` a
redirect — but your goal is shorter pages + scrap anchors + Free-review as a nav
destination, so `/free-review` stays a real page. Noted tradeoff: a dedicated form
page adds one click vs. an on-page form; the in-page CTA bands + terminal nav
position carry the "primary action" weight that the now-uniform bar no longer signals.

## Why

- One long page mixes audiences (cold browser vs ready buyer vs "show me proof").
  Short, single-purpose pages convert better, scan faster, and each gets its own
  URL/title/share card.
- No shared layout today → `<head>`, fonts, theme class, nav, footer are copy-pasted
  across `index/build/welcome/thanks`. A layout fixes that and is the prerequisite
  for consistent chrome.

## Information architecture (the page split)

| New page | Route | Content moved in | Primary CTA |
|---|---|---|---|
| **Intro** (home) | `/` | hero (headline + sub + preview **carousel** + stats) · the 4-step *"previewed before you pay"* how-it-works · closing CTA band | Free review |
| **Demos** | `/demos` | the live-demos-by-business-type grid (today's `#portfolio`) + the `.pf-thumb` loader | Free review / Pricing |
| **Pricing** | `/pricing` | the 3 package cards + the two-audience intro copy + the build-your-own line | Build your own (`/build`) / Free review |
| **Free review** | `/free-review` | the request **form** (today's `#get-started`), focused conversion page | (submit) |

- **Nav (uniform, sticky):** **Intro · Demos · Pricing · Free review** — all four
  links styled **identically, no accent CTA pill**. Brand lives in the banner above.
- **"The problem"** folds into the Intro hero/how narrative; **"About"** → footer.
- **Untouched routes:** `/build` (linked from Pricing) and `/welcome`, `/thanks`
  (post-submit) get wrapped in the layout. `/compare/*` are standalone theme refs —
  **do NOT wrap them** in the layout (it would force the luminous theme and defeat
  their purpose); just add `<meta name="robots" content="noindex">`.

## Design: scroll-away brand banner + sticky uniform nav

Three pieces, **direct flow siblings of `<body>`** (load-bearing for the pin — see
sticky-killers below):

```
<body>
  <header class="brand-banner"> b icon + "Better Business Web" — large, scrolls away
  <div class="sticky-sentinel" aria-hidden="true">  1px sibling; drives is-stuck
  <nav class="site-nav">  position: sticky; top: 0 — rests under banner, then pins
  <main id="main"><slot/>   (skip-link target lives here)
  <footer class="site-footer">
```

**Banner (`brand-banner`):** *b* icon + wordmark, **large on desktop** (generous
padding, `clamp()` wordmark), stepping to a **compact strip on mobile** with a stable
`min-height` so it doesn't reflow on font-swap. Static, in flow, scrolls away. No JS.
(On the one-line `/thanks`/`/welcome` utility pages, consider a compact banner
variant so it doesn't feel heavy.)

**Nav (`site-nav`):**
- **`position: sticky; top: 0`** — natively gives "rest under the banner, pin on
  scroll." No JS for the pin, no body-padding hack (sticky keeps its flow space — a
  CLS win over `position: fixed`).
- **Fully uniform:** all four links one style, no accent pill. Terminal position
  ("Free review" last) carries mild primary weight without color.
- **Look:** translucent **blurred** bar via `-webkit-backdrop-filter` **+**
  `backdrop-filter` (keep the prefix in 2026), paired with a **semi-opaque dark
  tint** (blur alone won't give text contrast) + a hairline bottom border. Fallback
  opaque tint under `@supports not (backdrop-filter…)`. One backdrop-filtered
  element only; never animate the blur radius.
- **Active state:** current link gets `aria-current="page"` (driven by a `current`
  prop via `class:list`) + a **non-color** underline (shape, with real contrast).
  `current` may be **unset** (build/welcome/thanks aren't in the nav → no active item).
- **Stuck state (the *b*-mark fade + shadow):** a **1px sentinel** placed between the
  banner and the nav; one `IntersectionObserver` (root = viewport, `threshold: 0`)
  toggles `is-stuck` when the sentinel leaves the top — driving **both** the *b*-mark
  opacity fade **and** the faint shadow, with a short **~180ms ease** so it *settles*
  rather than snaps (professional). No scroll handlers.

**The *b*-mark fade — smooth, with zero horizontal shift (your explicit requirement):**
- The mark sits in a **permanently-present, fixed-width slot** at the nav's left edge
  (`width: 2rem; flex: 0 0 2rem` — an **explicit** width, **never `auto`**, so glyph/
  font load can't resize it). The links' positions are byte-identical stuck vs unstuck.
- **Only `opacity` transitions** (0→1) — never `width`/`display`/`visibility`/
  insertion (each would reflow the bar). Use **inline SVG** for the mark (no network
  round-trip / FOUT, no `<img>` CLS).
- `prefers-reduced-motion`: `transition: none` (snap), **slot still reserved** — same
  layout, only the animation differs.

**Mobile nav (hamburger — the one genuinely new interactive piece):** the four links
don't fit a phone bar, so the sticky nav collapses to a **disclosure** (not a menu,
not a modal):
- `<button type="button" aria-expanded="false" aria-controls="primary-menu">` with an
  **accessible name** ("Menu"; icon `aria-hidden="true" focusable="false"`).
- The panel is `hidden` (or `inert`) when closed so its **links are not tabbable/
  announced** while invisible (the most-botched part of this pattern). Visual icon
  swap (☰↔✕) keyed off `[aria-expanded="true"]` in CSS only.
- **Escape closes and returns focus to the toggle**; a link tap closes it; optional
  close on outside-click. **No focus trap** (it's non-modal). Targets ≥44px;
  `touch-action: manipulation`. If the open panel overlays content, give it an
  **opaque** background (contrast over arbitrary content) + sufficient `z-index`.
- On resize to desktop, the inline link list must show regardless of prior toggle state.

## What gets removed / kept (scroll behavior)

**Remove — together, per page, in lockstep (see the landmine in the summary):**
- `data-reveal` attributes **+** the `IntersectionObserver` reveal JS **+** the
  `[data-reveal]{opacity:0…}` / `.is-visible` CSS (`global.css:138-139`). Grep for
  any residual `data-reveal`/`is-visible` before building — orphaned `opacity:0` with
  no observer = permanently hidden content.
- the **scroll-progress** bar (`#scroll-progress` + its CSS) — pointless on short pages.
- the header **shrink-on-scroll** (`#site-header.is-stuck`, the old `.site-header`/
  `.nav`/`.nav-cta` block) — replaced by the banner + sticky-nav pattern.
- the **magnetic-buttons** block and the **`countUp()`** function + its
  `data-countup`/`data-prefix` attributes — **delete** them (render stats as static
  text); don't leave dead-but-wired code.

**Keep:** the **hero carousel** (strong proof; self-contained IIFE — but it reads
`reduce`, so carry a local `const reduce = matchMedia('(prefers-reduced-motion: reduce)').matches`
into whichever page hosts it). Verify it pauses under reduced-motion.

## Technical plan

1. **`src/layouts/Site.astro`** (keystone) — owns the whole `<html><head>…</head>
   <body class="theme-luminous">` shell with typed `Props` (`title`, `description`,
   `ogTitle`, `current?`, `noindex?`). **Imports fonts + `global.css` + theme CSS
   once here** (delete the per-page imports). Renders, as body siblings:
   `BrandBanner` markup, the sentinel, `<SiteNav current={current} />`, `<main
   id="main"><slot/></main>` (the skip-link target), `<SiteFooter/>`. *(The banner
   markup can live inline in the layout — it's propless; a separate component is
   optional.)*
2. **`src/components/SiteNav.astro`** — `position: sticky; top: 0`, uniform links,
   `class:list` active state, real route `href`s, mobile hamburger, and the
   sentinel-driven `is-stuck` JS (shadow + *b*-mark fade). **Component-scoped
   `<style>`.**
3. **`src/components/SiteFooter.astro`** — extract today's footer; add repeated nav
   links + the About/studio line + copyright. Component-scoped `<style>`.
4. **Pages** — rewrite `index.astro` (Intro) on the layout; add `demos.astro`,
   `pricing.astro`, `free-review.astro`. Move each section's markup **and its scoped
   `<style>`** (Astro scoped styles do **not** follow markup when cut — co-locate
   them) into the owning page/section. Retire `LandingBody.astro`. Keep shared
   section/card/form classes in `global.css`.
5. **Scripts** — use **plain processed `<script>`** (bundled + deduped once per page);
   pass any server values via **`data-*`**, not `define:vars` (which forces inline).
   Make each script self-contained + null-safe (`querySelectorAll`, re-declare
   `reduce`). Carousel → Intro; `.pf-thumb` loader → Demos; form handler travels with
   the form.
6. **Form** (Free review) — move the `<form>` **verbatim**, keeping
   `action="/.netlify/functions/website-review"`; the function's **server-side 303 →
   `/thanks/`** keeps working. Preserve `<label>`s, `required`, `<button
   type="submit">`, an `<h1>`, and announce errors (`aria-live`/`aria-describedby`).
7. **Scrap anchors** — `#how|#packages|#portfolio|#about|#get-started` → `/`,
   `/pricing`, `/demos`, `/free-review`. In-page CTAs repointed (hero "Get a free
   review" → `/free-review`, "See demos" → `/demos`; "Start this package" already →
   `/build?preset=…`). Keep `html { scroll-padding-top: var(--nav-h) }` so the
   **skip-link** (`#main`) and any residual jump lands below the pinned bar.
8. **`/build`** — strip its `<html>/<head>`/font+theme imports (keep
   **`BundleBuilder.css` page-local** + the island in the slot); **drop the
   `byo-back` "← Better Business Web" link** (redundant with the banner), keep
   `byo-hero` as a page-title block. Wrap `welcome`/`thanks` in the layout (accept
   the intended restyle to luminous). Leave `/compare/*` standalone + `noindex`.

## Sequencing

1. **Layout + banner + nav + footer** (Site.astro, SiteNav, SiteFooter) — build the
   chrome and **validate the pin on existing Intro content first** (esp. that
   `body { overflow-x: hidden }` doesn't neutralize sticky — if it does, switch it /
   the hero wrapper to `overflow-x: clip`).
2. **Per page (one commit each): move markup + strip its dead `data-reveal`/scroll
   attrs + carry only that page's scripts (self-contained) + co-locate its scoped
   styles.** Do split-and-strip together — never leave moved content with `opacity:0`
   and no observer.
3. **Delete orphaned global.css** (`[data-reveal]`, `.scroll-progress`,
   `.site-header.is-stuck`, old `.site-header`/`.nav`/`.nav-cta`) and the `countUp()`/
   magnetic blocks, once no page references them.
4. **Wrap** `/build` (drop byo-back) + `welcome`/`thanks`; `noindex` `/compare/*`.
5. **Verify:** `npm run build`; **screenshot every page at desktop + phone widths**;
   confirm the nav pins, the *b*-mark fades with **no horizontal shift**, the mobile
   menu opens/closes/Escapes with focus return and untabbable-when-closed links, no
   dead links, the review form submits → `/thanks/`. Deploy **separately** (not part
   of this plan).

## Risks / watch-items

- **Sticky-killers (highest-risk, silent):** the pin breaks if **any ancestor between
  `<nav>` and `<body>`** has `overflow: hidden|scroll|auto` (use **`clip`** instead),
  `transform`, `filter`, `backdrop-filter`, `perspective`, `will-change:
  transform/filter/perspective`, or `contain: paint|layout|content|strict`. Keep
  banner/sentinel/nav/main as **direct body siblings** (a max-width wrapper is OK only
  if it uses `margin/max-width` and never those props). `backdrop-filter` **on the nav
  itself is fine**; on an ancestor it isn't. `global.css` has `html{overflow-x:clip}`
  (fine) and `body{overflow-x:hidden}` — **test the pin against it**; flex parents need
  `align-self: start` on the nav.
- **Reveal lockstep** (above) — grep `data-reveal`/`is-visible` after the split.
- **Scoped styles don't transfer** when moving sections out of `LandingBody.astro` —
  co-locate each into its new owner; reclassify genuinely-global rules to `global.css`.
- **welcome/thanks restyle** is an intended visible diff (editorial→luminous) — don't
  mistake it for a regression in the screenshots.
- **CLS:** stable banner `min-height`; **preload the brand font** (above the fold on
  every page) with `font-display: swap`; inline-SVG *b* mark so it can't shift the slot.
- **iOS Safari:** any full-height banner sized in `vh` → use **`dvh`**; watch
  address-bar resize repositioning sticky; `-webkit-overflow-scrolling: touch` on a
  wrapper re-introduces the overflow scroll-container trap.

## Research insights

**CSS sticky / banner-then-pin** — `position: sticky; top:0` on a flow sibling below
the banner is the canonical zero-JS pattern; it pins to the nearest scrolling ancestor
(the viewport, unless an ancestor creates a scroll/containing context — the "killers"
above). Prefer **`overflow: clip` over `hidden`** to tame horizontal overflow without
breaking sticky. `backdrop-filter` is Baseline but **keep `-webkit-` in 2026** (Safari
≤17) with a `@supports not` opaque fallback; don't animate the blur. Detect "stuck"
with a **sentinel + IntersectionObserver** (no scroll listeners); CSS
`@container scroll-state(stuck: top)` is the future but Chromium-only today (defer as
progressive enhancement). Use **`scroll-padding-top`** for anchored/skip targets;
**`dvh`** for full-height boxes on iOS.
([Polypane](https://polypane.app/blog/getting-stuck-all-the-ways-position-sticky-can-fail/),
[Frontend Masters](https://frontendmasters.com/blog/the-weird-parts-of-position-sticky/),
[Chrome — sticky event](https://developer.chrome.com/docs/css-ui/sticky-headers),
[MDN backdrop-filter](https://developer.mozilla.org/en-US/docs/Web/CSS/backdrop-filter),
[CSS-Tricks scroll-margin-top](https://css-tricks.com/fixed-headers-and-jump-links-the-solution-is-scroll-margin-top/))

**Accessible nav** — it's the **WAI-ARIA Disclosure** pattern, **not** menu/menubar
(`role="menu"` forces app-mode + breaks link semantics) and **not** a dialog/focus-trap
(only trap if it's a full-screen page-obscuring overlay). `<nav aria-label="Primary">`
+ real `<a>` links; **`aria-current="page"`** (most specific) for the active link;
toggle `<button aria-expanded aria-controls>` with a real accessible name; **`hidden`/
`inert` when closed** so links aren't tabbable; Escape closes + restores focus; targets
≥44px; `touch-action: manipulation` + `width=device-width` kill the iOS tap delay
(never disable zoom).
([WAI-ARIA APG Disclosure](https://www.w3.org/WAI/ARIA/apg/patterns/disclosure/),
[Adrian Roselli](https://adrianroselli.com/2019/06/link-disclosure-widget-navigation.html),
[Scott O'Hara — inclusively hidden](https://www.scottohara.me/blog/2017/04/14/inclusively-hidden.html),
[MDN aria-current](https://developer.mozilla.org/en-US/docs/Web/Accessibility/ARIA/Reference/Attributes/aria-current))

**Astro v4/v5** — one `src/layouts/Site.astro` with typed `Props` + `<slot/>`; **import
fonts/CSS once** in the layout (Astro inlines <4kB, extracts shared CSS into a cached
chunk). Plain `<script>` is **compiled, bundled, deduped, once per page**; `is:inline`/
`define:vars` opt out of bundling — **pass data via `data-*`** instead. **Scoped
`<style>` does NOT transfer** when you move markup — co-locate. Drive active state with
**`class:list`**. **Keep full page loads (no `<ClientRouter/>`) for v1** — View
Transitions would require re-initing every script on `astro:page-load`; not worth it
for 4 pages.
([Astro Layouts](https://docs.astro.build/en/basics/layouts/),
[Client-side scripts](https://docs.astro.build/en/guides/client-side-scripts/),
[Styling](https://docs.astro.build/en/guides/styling/),
[View transitions](https://docs.astro.build/en/guides/view-transitions/))

## Later (explicitly deferred — not v1)

- `@astrojs/sitemap` (4 nav-linked pages crawl fine without it).
- Old-anchor → route Netlify redirects (add only if analytics show hash 404s).
- Astro View Transitions / `<ClientRouter/>` (would force script re-init refactor).
- CSS `scroll-state(stuck:)` to replace the sentinel/IO (Chromium-only today).

## Open choices (defaults; all reversible)

- *b*-mark fades into the pinned nav → **on** (opacity-only, fixed-width reserved
  slot, inline SVG, ~180ms, reduced-motion snaps) · stuck-shadow → **on** (shares the
  one sentinel/IO) · magnetic buttons → **dropped** · count-ups → **static text** ·
  "How it works" → **on Intro** · About → **footer** · brand banner → markup inline in
  the layout (separate component optional).
