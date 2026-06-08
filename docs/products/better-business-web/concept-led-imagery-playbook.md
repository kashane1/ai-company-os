---
title: Concept-Led Demo Playbook (AI-Generated Bespoke Imagery)
type: playbook
date: 2026-06-08
owner: kashane
related:
  - docs/demo-site-build-playbook.md
  - products/better-business-web/site/public/work/plumbing/
---

# 🎨 Concept-Led Demo Playbook — AI-Generated Bespoke Imagery

> **TL;DR.** When we build a demo and there's **no clear direction** from the
> images/data we can find online (a fictional showcase business, or a real
> prospect with a thin/ugly web presence), we **invent the brand concept
> ourselves** and **generate bespoke, art-directed imagery** (Gemini "Nano Banana
> Pro") to match it — instead of leaning on weak stock or literal photos.
> Pipeline: **concept → image brief → generate (consistent style suffix) →
> curate → optimize to webp → build the page on the concept → verify.** First
> run: the **TrueLine Plumbing** revamp (the weakest of our 8 demos), turned from
> a loud blue/orange template into a premium navy + copper, cinematic site.

This is the **complement** to [demo-site-build-playbook.md](../../demo-site-build-playbook.md).
That one is for **real prospects grounded in real evidence** ("every line traces
to a real fact about this business; real photos, real services"). **This one is
for the opposite case** — when there's nothing good to ground on, so we make our
best guess at positioning and **generate the look**.

## When to use this mode

- A **fictional showcase demo** for the BBW site (the `/work/<genre>/` samples —
  "business details are made up, the design work is real").
- A **real prospect with no usable imagery** (no site, dated site, only a blurry
  Facebook photo) where we're pitching a *direction* before they give us assets.
- Any time the bottleneck on a demo is **"the photos are killing it."**

> ⚠️ Honesty guardrail carries over from the main playbook: a published showcase
> demo must read as a **sample** (the demos page already says so). For a **real**
> client's published site, swap generated imagery for owner-provided/licensed
> photos before go-live — generated imagery is for the *pitch/preview* and for
> our own fictional samples.

## The pipeline

### 1 — Positioning & concept (invent it)
Write a **one-line creative concept** that everything else serves, then derive
palette, type, and voice from it.

- **Concept (1 line):** the angle that separates this brand from the genre
  cliché. _TrueLine → "precision you can see; the calm craftsman, not the
  panicked emergency."_
- **Palette:** 1 dark base + 1 warm metal/accent usually reads premium. _TrueLine
  → deep navy/slate `#0b1320` + copper `#c47e4e` / brass `#d6a96a`_ (replacing the
  cliché trades blue+orange).
- **Type:** pick a display face that **escapes the genre default**. _TrueLine →
  an editorial serif (**Fraunces**) over plumbing is unexpected = premium; kept a
  mono (**Spline Sans Mono**) for the `/ 01` technical labels to signal precision._
- **Voice:** sentence-case and confident, not all-caps shouting. _"Plumbing done
  with precision." not "WE FIX IT RIGHT THE FIRST TIME."_

### 2 — Art-direction brief (the image list)
Decide the shots and **write one shared style suffix** so the whole set is
cohesive. Rules that make AI imagery look pro, not generated:

- **No people** (avoids uncanny AI faces — the #1 tell).
- **No text, no logos, no brand marks** in the image (we add real type in HTML).
- **One consistent style suffix** appended to every prompt — same palette,
  lighting, mood, lens feel. This is what makes 6 images look like one photoshoot.
- **Right aspect ratio per slot** (hero `4:5`, wide gallery `3:2`, square `1:1`).

TrueLine's shared suffix:
> _"Cinematic editorial product photography, deep navy-slate background (#0e1726),
> warm copper and brass tones, dramatic directional rim light, premium and moody,
> shallow depth of field, crisp high detail, subtle reflections. No people, no
> text, no logos, no brand marks."_

TrueLine's shot list (subject → aspect): hero copper-grid `4:5` · brass faucet
`4:5` · soldered T-joint macro `1:1` · fittings flat-lay `1:1` · under-sink
install `3:2` · tankless + manifold `3:2`.

### 3 — Generate (Gemini "Nano Banana Pro")
Skill: `compound-engineering:gemini-imagegen`. Model **`gemini-3-pro-image-preview`**,
**2K**, `response_modalities=['TEXT','IMAGE']`, per-image `aspect_ratio`. Needs
`GEMINI_API_KEY` (in repo `.env`); SDK `google-genai` (`pip install google-genai`).
Save as **`.jpg`** (Gemini returns JPEG). Loop the shot list, retry 3× on error.
A copy of the working generator lives in the git history of this commit
(`/tmp/gen_trueline.py` pattern: load key from `.env` → loop `(name, ar, prompt)`
→ `prompt + STYLE` → save `<name>.jpg`).

### 4 — Curate
View every output. Keep the on-concept ones; regenerate any that drift (wrong
palette, stray text, people). 6/6 held on the first TrueLine pass.

### 5 — Optimize to webp
Resize to display size + `webp` q≈82 (PIL). Targets: hero ~1200w, wide ~1500w,
square ~820w. TrueLine result: **2–3 MB JPEGs → 24–64 KB webp**. Delete the raw
`_gen/` JPEGs after.

### 6 — Build the page on the concept
Recolor/retype the page to the concept; make the **generated hero the showpiece**
(clean frame, not a busy collage); swap the gallery to the new set; soften any
"loud template" tics (hard shadows, rotations, all-caps). Keep the real content
(services, hours, honest review paraphrase).

### 7 — Verify
`npm run build`; screenshot **desktop + mobile**; regenerate the demos-page
thumbnail (`/portfolio/<genre>.webp`) and OG image from the new design; check the
hero, gallery, and mobile sticky CTA.

## Reusable assets (copy these)

- **Style-suffix technique** (§2) — the single highest-leverage trick for cohesion.
- **Generator pattern** (§3) — `(name, aspect, prompt)` loop + shared `STYLE`.
- **Optimize step** (§5) — PIL resize → webp q82.
- **No-people / no-text rules** (§2) — the quality guardrails.

## Worked example — TrueLine Plumbing (first run, 2026-06-08)

- **Files:** `products/better-business-web/site/public/work/plumbing/` (page +
  `assets/*.webp`). Thumbnail: `public/portfolio/plumbing.webp`.
- **Before:** loud blue + orange neo-brutalist template, dim literal sink photo
  (the weakest hero of all 8 demos).
- **After:** deep navy + copper, Fraunces serif, 6 cinematic generated images,
  cohesive and premium.
- **Screenshots:** `docs/products/better-business-web/screenshots/` —
  `multipage`/`_tl-*` captures from this session.

## Open questions / next

- Roll this to the other demos only where the imagery is the weak link (don't
  fix what isn't broken).
- For **real** clients: generated imagery = preview only; collect real assets
  before publishing (licensing/honesty).
- Consider a tiny committed `scripts/web/gen-imagery.py` if we run this often.
