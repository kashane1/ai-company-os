# Better Business Web V2 Landing Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build the Better Business Web v2 homepage at `/` and preserve the current homepage at `/v1`.

**Architecture:** The current homepage becomes a versioned archive page. The v2 landing content lives in a small data module and renders through one reusable Astro component so future versioning and design changes are easier.

**Tech Stack:** Astro 4, CSS custom properties, existing Better Business Web site shell, static JSON/module data, Netlify-compatible build.

---

### Task 1: Preserve V1

**Files:**
- Create: `products/better-business-web/site/src/pages/v1.astro`
- Read: `products/better-business-web/site/src/pages/index.astro`

**Steps:**
1. Copy the current homepage source into `v1.astro`.
2. Change the SEO title/description and `current` prop so it is clearly the archived v1 page.
3. Keep all existing v1 markup and scripts intact.

**Verify:**
- `npm run check`

### Task 2: Add V2 Data

**Files:**
- Create: `products/better-business-web/site/src/data/landing-v2.mjs`

**Steps:**
1. Add arrays for proof stats, story sections, package cards, and palette tokens.
2. Keep copy concise and aligned to the preview-before-you-pay offer.

**Verify:**
- Import from an Astro component without type/runtime errors.

### Task 3: Build Reusable V2 Component

**Files:**
- Create: `products/better-business-web/site/src/components/LandingV2.astro`

**Steps:**
1. Import `landing-v2.mjs` and `portfolio.json`.
2. Render hero, dimensional studio preview, proof strip, feature bands, package cards, and closing CTA.
3. Scope the dark aquatic token system under `.landing-v2`.
4. Add responsive rules for mobile, tablet, and desktop.
5. Respect reduced-motion preferences.

**Verify:**
- `npm run check`
- Visual inspection in browser.

### Task 4: Wire Homepage

**Files:**
- Modify: `products/better-business-web/site/src/pages/index.astro`

**Steps:**
1. Replace inline v1 homepage markup with the v2 component.
2. Keep the existing `Site` layout and set homepage SEO for v2.
3. Do not alter unrelated routes.

**Verify:**
- `npm run check`
- `npm run build`

### Task 5: Local Demo

**Files:**
- No source changes unless verification reveals a defect.

**Steps:**
1. Start `npm run dev -- --host 127.0.0.1`.
2. Open `http://127.0.0.1:<port>/` in the in-app browser.
3. Capture/inspect desktop and mobile layouts.
4. Fix visible overlap, text-fit, or rendering defects.

**Verify:**
- Browser shows v2 at `/`.
- Browser shows preserved v1 at `/v1`.
