# Demo Site Build Playbook (per business)

How we build **one genuinely good demo website** for a prospect — grounded,
specific, and not cookie-cutter. This is the deep procedure behind Stage 5 of
`docs/waas-prospecting-lane.md`. It replaces the old "fill one template with
genre-default copy" approach, which produced generic, invented-sounding pages.

**Worked reference example:** Skyline Nails & Spa, Fort Worth —
`state/prospects/sites/ChIJIYKyBuFzToYRpKQSc6Yf9ks/` (live:
https://skyline-nails-fortworth.netlify.app).

## The quality bar (non-negotiable)

1. **Every line on the page traces to real evidence** about *this* business. If
   we can't source it, it doesn't ship.
2. **No invented "business words."** No "Fast by default," no fabricated
   testimonials, no fake trust logos, no superlatives we can't back.
3. **Real photos** (theirs), real services, real hours, real reviews-as-input.
4. **Honest guardrails** — we actively decide what *not* to claim (see step 2).
5. **Looks bespoke**, genre-appropriate — not one template reskinned.

## Hard rules

- **Reviews are input, paraphrased — never quoted verbatim** on the page
  (default posture; revisit per ToS before a production launch).
- **No "lowest price / cheapest"** unless evidence supports it — and check the
  *negative* reviews so we don't claim something customers dispute.
- **No invented services.** Only services we can confirm (reviews, photos,
  booking menu, the business's own pages).
- **Don't claim "award-winning"** off low-tier directory badges (BusinessRate,
  etc.).
- **Photos:** Google/owner photos are fine for a private preview shown to the
  owner; for a **published** site use owner-provided or explicitly-licensed
  images and honor source attribution/ToS.

## Data sources (ranked — what each gives, how, caveats)

| Source | What it uniquely gives | Access | Caveat |
|---|---|---|---|
| **Google Place Details** (baseline) | name, address, phone, hours, rating+count, **up to 5 review texts**, **up to 10 photos**, type, payments, price level, editorial summary | `GooglePlacesConnector.fetch_profile` (rich mask) + Photos media endpoint | review-text/photos ToS for *published* use |
| **Yelp** | **more review depth**, owner-written **"About / Specialties / History / Meet the Owner"**, more photos, service attributes (parking, kids, etc.), price range | read the public business page (manual, per-business); Yelp Fusion API for facts | don't bulk-scrape (ToS); per-business read is fine |
| **Booking platform** (Fresha / Booksy / Vagaro / Square) | the **actual service menu with prices**, staff names, service descriptions, durations | the booking URL from contact-enrichment | best source for accurate services |
| **Instagram** | their **real work portfolio** + captions (voice, aesthetic, what they push), highlights | their handle (from contact-enrichment) | use for understanding + image *direction*; get rights before publishing their posts |
| **Facebook page** | owner-written **About**, services, hours, story, sometimes email; owner voice | their FB URL | same content-rights note |
| **BBB / Chamber** | **founding year**, owner name, real accreditation/awards | web search | facts only; low-tier "awards" ≠ credentials |
| **Local press / news** | real awards, the founding story, community angle | web search | only cite verifiable items |
| **The owner (once engaged)** | logo, brand colors, real photos, the true service list & prices, corrections | direct, after first contact | the highest-quality source — replaces guesses at sale time |

Priority order in practice: **Google (baseline) → Yelp + booking menu (depth &
services) → IG/FB (photos & voice) → BBB/press (story & credibility) → owner
(truth, at engagement).**

## The process

### 1. Deep-gather → `sites/<place_id>/source/`  (mostly automated)
- Rich Place Details JSON (`place-details.json`) incl. reviews + photos (API).
- Download photos → `source/photos/` and **look at every one** (Read the images).
- **Auto-pull Yelp + booking + FB-public via the browser** per
  `docs/demo-site-gather-automation.md` (Chrome MCP, paced/anti-bot, read-only).
  Yelp gives the owner About, full service list, amenities, and all reviews +
  owner replies — capture the negatives, they're the best guardrail material.
- Human adds only what's gated/judgment: IG/FB *full* content (if logged in),
  best-photo picks, brand vibe.

### 2. Evidence → content brief  → `source/content-brief.md`
- List **verified facts** (with source).
- List **what's true about the work** (services/specialties) — each with the
  review/photo/menu line that proves it.
- Draft **paraphrased** testimonials from the best real reviews.
- Write the **guardrails** section: what NOT to claim, from the negative reviews
  and weak signals.

### 3. Curate photos
- Pick a hero, an interior/"the space" shot, and a work gallery. Rename
  semantically into `dist/assets/` (`hero.jpg`, `work-chrome.jpg`, …).

### 4. Build bespoke → `sites/<place_id>/dist-v2/index.html`
- **Palette from visual cues first** — derive it from the business's storefront /
  signage / logo / photos (dominant canvas + one sharp accent), not an invented
  scheme. (King: hand-painted red storefront → red/white/minimal-blue.)
- Genre-appropriate design (type system, palette, layout). Self-contained HTML +
  inlined CSS + the real photos. Real CTAs (`tel:` / verified booking), real hours
  table, live map embed.
- Copy comes **only** from the brief.
- **Run the Craft Pass** (`_scaffold/05-craft-pass.md`) before final preview:
  distinctive type, palette+grain+glow (kill the flat look), real elevation/depth,
  reduced-motion-gated scroll reveals, micro-interactions, an on-message hero, and
  section polish. **Every demo gets this granular refinement** — it's the
  difference between "clean template" and "premium custom build."

### 5. Verify + LOCAL preview (iterate here — do NOT deploy yet)
- Grep for template ghosts: `Northwind`, `Fast by default`, `paid for itself`,
  `{{`. Must be **zero**.
- Re-read every headline/claim against the brief; cut anything ungrounded.
- **Serve locally** and review in a browser: `python scripts/agency/preview_site.py
  --place-id <PID>` → open `http://localhost:8011`. Give notes, edit the HTML,
  refresh. **Repeat as many rounds as needed.** Nothing is published in this step.
- **Capture a full-page screenshot every iteration** →
  `python scripts/agency/screenshot_demo.py --place-id <PID> --label <iter>`.
  It serves the build on localhost, captures top-to-bottom, versions the PNG in the
  business's `screenshots/` folder, and mirrors the newest into the flat
  **`state/prospects/review-gallery/`** so a batch of businesses can be reviewed
  from one folder. Re-run after each accepted change.

### 6. Deploy — separate, explicit, operator-approved
- **Last action before deploy: capture the final full-page screenshot** (step 5
  command) so the review gallery reflects exactly what ships. Operator reviews the
  gallery PNG; deploy only after that.
- Only when the operator says "ship it." Run
  `python scripts/agency/build_prospect_site.py --place-id <PID> --deploy`
  (requires `dist-v2/` — the script refuses legacy `dist/`). Uses Netlify draft
  deploy to the shared preview site; confirm the page serves `text/html` and
  photos `image/jpeg`.
- The script writes `mockup_url` on the record and `outreach-with-mockup.md`.

## Artifact layout (per business)

```
state/prospects/sites/<place_id>/
  source/
    place-details.json        # raw Google data
    photos/                    # all downloaded photos + _meta.json
    content-brief.md           # the evidence layer — every claim sourced
    yelp-notes.md, social-notes.md   # depth from other sources
  dist-v2/
    index.html                 # the bespoke page
    assets/                    # curated, renamed real photos
```

## Human-in-the-loop workflow (current phase)

We are deliberately **human-first** until the process is proven, then we automate.
Each build runs through four checkpoints; copy the scaffold templates from
`state/prospects/sites/_scaffold/` into the business's `source/` folder and fill
them in order.

| Checkpoint | Template | Agent | Human (operator) |
|---|---|---|---|
| **A · Gather** | `01-gather-packet.md` | **Google + Yelp + booking + FB-public — auto** (see `demo-site-gather-automation.md`) | **IG/FB *full* content (if logged in), best-photo picks, brand vibe** |
| **B · Brief** | `02-content-brief.md` | draft sourced brief | **approve facts, pick lead-with, confirm guardrails** |
| **C · Design** | `03-design-direction.md` | propose options | **palette from visual cues, choose aesthetic/hero, brand assets** |
| **D · Build + Craft Pass + LOCAL preview** | `04-qa-checklist.md` + `05-craft-pass.md` | build, **run craft pass**, checks, screenshot, **serve locally** | **review on localhost, give notes — iterate** |
| **E · Deploy** *(separate, gated)* | — | deploy **only when told** | **explicit "ship it" approval** |

> **Deploy is NOT part of the build loop.** We build → preview on localhost
> (`scripts/agency/preview_site.py`) → iterate → and push to Netlify only on an
> explicit operator go. Do not auto-deploy a bespoke build.

After each build, append what worked / what burned us to
**`docs/demo-site-learnings.md`**. That file is the bridge to automation: when a
rule holds across ≥3 builds, it graduates into a default, a check, or a template.

## Manual vs automatable (be honest)

- **Automatable:** the gather (Place Details, photo download, booking/Yelp fetch),
  the verify grep, the deploy.
- **Judgment (human or strong agent + verify loop):** photo curation, reading
  reviews to find what's *really* true, writing grounded copy, and the design.
  The quality bar here wants a review loop, **not** blind templating — that's the
  whole point of moving off v1.

## Status

- v1 (template-fill) — deprecated for client demos; produced generic copy.
- v2 (this playbook) — proven on Skyline Nails. Next: decide how much of steps
  1–3 to systematize behind an agent without losing genuineness.
