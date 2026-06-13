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
- **No scaffold or sales/meta vocabulary in shipped copy — fail closed.** The
  page speaks to the business's *customers, as the business* — never about our
  build, our funnel, or the sales process. Banned anywhere a visitor can see:
  "prospect", "preview", "category-safe", "marketplace-only signal", "verified
  as having", "owned website/web page", "the pitch", and any placeholder/TODO
  left in body copy ("confirm exact availability before using this as production
  copy", "included as a … starting point"). No third-person framing of the
  owner ("this business has…"). **If a section can't be filled with real,
  sourced content, delete the section — never ship the placeholder.** (The
  2026-06 bulk "marketplace-only" batch shipped exactly this; 473 of 586 built
  pages were unsendable as a result — see the audit in the funnel work.)
- **Don't claim "award-winning"** off low-tier directory badges (BusinessRate,
  etc.).
- **Photos:** Google/owner photos are fine for a private preview shown to the
  owner; for a **published** site use owner-provided or explicitly-licensed
  images and honor source attribution/ToS.
- **Voice is per-business, never templated.** Copy follows
  `docs/products/better-business-web/gtm/demo-voice-framework.md` (lead-with
  angle, attribution, anti-slop) + the "Banned everywhere" list in
  `docs/products/better-business-web/gtm/voice.md`. No AI-tell phrasing
  ("unlock", "elevate", "it's not just X, it's Y") on a small-business page.
- **Responsive edge padding — verify at mobile width.** Every section must keep the
  same left/right padding at 390px, header and hero included. **Never override a
  container's padding with a `padding` shorthand that zeroes the horizontal sides**
  (`padding: 2rem 0` / `padding: 3rem 0 2rem` → left/right become `0`, so that section
  runs to the screen edge on mobile while the rest of the page looks fine). Use
  **`padding-block`** for vertical-only overrides. The two usual offenders are the header
  nav and the hero wrapper. (Caught on Five Star + Duval; baked into `05-craft-pass.md` §8.)
- **Blur license plates & PII in every gathered photo (privacy/security).** Google photos routinely
  show readable license plates (and sometimes faces/personal docs). Before a photo ships, bake an
  **irreversible blur+pixelate into the image file itself** — never a CSS overlay (bypassable). Use
  `scripts/agency/blur_plates.py` (Pillow): set per-file fractional boxes, it backs up pristine
  originals to `assets/_orig/` and reprocesses from them (idempotent). **Verify by cropping each
  plate region at high res** — boxes read off a scaled preview are easy to mis-place (e.g. hitting a
  door instead of the plate). Plates in the lot count, not just the subject car. (Caught on Motor City.)
- **Full-bleed strips must keep content off the viewport edge.** Any edge-to-edge band —
  scrolling marquee/trust strip, ticker, ribbon — will let its text butt right against the
  screen edge. Give it breathing room: an **edge fade** (a `var(--bg)`-to-`transparent`
  gradient pseudo-element pinned left & right, `width: clamp(1.75rem,7vw,4.5rem)`, so the
  text fades into the band) for a scrolling marquee, or `padding-inline` for a static strip.
  (Caught on Nghia's trust-strip marquee; baked into `05-craft-pass.md` §8.)

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

### 1. Deep-gather → `sites/<place_id>/source/`  (agent-driven by default)
**Default posture: the agent gathers everything it can itself; the human steps in
only for genuine gaps and judgment.** Don't pre-emptively hand a research checklist
to the human — try the browser first, then escalate what's actually missing.
- Rich Place Details JSON (`place-details.json`) incl. reviews + photos (API).
- Download photos → `source/photos/` and **look at every one** (Read the images;
  a contact-sheet montage is a fast way to view all 10 at once).
- **Agent pulls Yelp + BBB + Birdeye + booking + FB-public via the browser**
  (Chrome MCP, paced/anti-bot, read-only) per `docs/demo-site-gather-automation.md`.
  Work slowly (scroll, wait, one source at a time) to avoid IP bans. Yelp gives the
  owner About, full service list, amenities, and all reviews + owner replies.

- **⛔ Integrity check (mandatory, do NOT skip).** Pull the *other* rating sources,
  not just Google — Google can be gamed, and a glowing 5.0 there can hide a 3.x with
  fraud reports elsewhere. Read the negatives across Yelp/BBB/Birdeye. If you see
  **scam / "took my money, no delivery" / fake-or-manipulated-review / threatened-
  the-customer** signals, **STOP — log an `⛔ INTEGRITY FLAG` at the top of the gather
  packet and escalate to the operator before any brief or build.** Disqualify-or-
  proceed is an operator decision, never the agent's. (Worked case: Duval Notary —
  Google 5.0/440 looked clean; Yelp 3.7/6 carried two detailed fraud allegations.)

- Human steps in only for what's truly gated/judgment: IG/FB *full* content behind a
  login, best-photo picks, final brand vibe, and the integrity disquaify/proceed call.

### 2. Evidence → content brief  → `source/content-brief.md`
- List **verified facts** (with source).
- List **what's true about the work** (services/specialties) — each with the
  review/photo/menu line that proves it.
- Draft **paraphrased** testimonials from the best real reviews.
- Write the **guardrails** section: what NOT to claim, from the negative reviews
  and weak signals.
- Set the **lead-with angle + voice** from
  `docs/products/better-business-web/gtm/demo-voice-framework.md` (genre-specific;
  derive from the business's own data, never a template phrase). Pull its genre
  lead-with row + the say-this-not-that examples into the build prompt so the
  draft is on-voice from the start — fix the input, not just the output.

### 3. Curate photos
- Pick a hero, an interior/"the space" shot, and a work gallery. Rename
  semantically into `dist/assets/` (`hero.jpg`, `work-chrome.jpg`, …).

### 4. Build bespoke → `sites/<place_id>/dist-v2/index.html`
- **Palette from visual cues first** — derive it from the business's storefront /
  signage / logo / photos (dominant canvas + one sharp accent), not an invented
  scheme. (King: hand-painted red storefront → red/white/minimal-blue.)
  When cues are weak, fall back to a genre-matched triad + a vibe-fit font pairing
  from `packages/web/design_reference/` (palettes / font_pairings / ux_rules,
  curated from UI UX Pro Max, MIT) — fallback, never an override.
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
- **AI-tell voice gate (the real gate) — iterate until clean:**
  1. Whitelist the business's own name tokens, then `grep -iF` the "Banned
     everywhere" words/openers from
     `docs/products/better-business-web/gtm/voice.md`. English-only — skip
     non-English body copy. Any non-whitelisted hit → fix.
  2. Secondary LLM self-critique — re-read as a skeptical local owner and flag the
     judgment tells: banned constructions ("it's not just X, it's Y"), em-dash
     budget (~1 per 500 words — count, don't ban), uniform rhythm / rule-of-three
     spam, clichés, and any claim not in the brief. Don't attach a real reviewer's
     name to a paraphrase.
  3. Rewrite and re-run 1–2. Loop until both pass.
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

**Staging vs sending — two deploy modes:**

| Mode | Command | URL | Gate | When |
|---|---|---|---|---|
| **Shared draft** (default) | `--deploy` / `--batch` | `<deploy_id>--bbw-previews.netlify.app` | ungated | staging, iteration, bulk — one Netlify site for unlimited previews |
| **Named production** | `--named-site --approve` | `<business>-<city>.netlify.app` (clean root) | **approval-gated** | the handful you actually SEND a prospect |

- The clean root-subdomain URL requires a **production** deploy to a per-business
  named site, which is approval-gated by `packages/policies/deploy_readiness.py`.
  Pass `--named-site --approve` only after the gallery PNG is reviewed and you've
  decided to ship it live; without `--approve` the script refuses at the gate.
  Both the scaffold-copy and secret-leak gates still run on this path.
- **Don't bulk `--named-site`:** each business spends one Netlify site (accounts
  are site-count capped). Keep staging on the shared draft; switch to
  `--named-site` only for sends. Same `mockup_url`/`mockup_site_id`/
  `mockup_deploy_id` backfill as the draft path.

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

**Agent-first, human-on-gaps.** The agent runs each stage as far as it can on its
own (browser gather included) and pulls the human in only for gated content and
judgment calls — not as a default checkpoint on every step. Copy the scaffold
templates from `state/prospects/sites/_scaffold/` into the business's `source/`
folder and fill them in order.

| Checkpoint | Template | Agent | Human (operator) |
|---|---|---|---|
| **A · Gather** | `01-gather-packet.md` | **Google + Yelp + BBB + Birdeye + booking + FB-public — agent-driven via browser** (see `demo-site-gather-automation.md`); **run the ⛔ integrity check** | only **login-gated IG/FB content, best-photo picks, brand vibe**, and the **integrity disqualify/proceed call** if flagged |
| **B · Brief** | `02-content-brief.md` | draft sourced brief | **approve facts, pick lead-with, confirm guardrails** |
| **C · Design** | `03-design-direction.md` | propose options | **palette from visual cues, choose aesthetic/hero, brand assets** |
| **D · Build + Craft Pass + LOCAL preview** | `04-qa-checklist.md` + `05-craft-pass.md` | build, **run craft pass**, checks, screenshot, **serve locally** | **review on localhost, give notes — iterate** |
| **E · Deploy** *(separate, gated)* | — | deploy **only when told** | **explicit "ship it" approval** |

> **Deploy is NOT part of the build loop.** We build → preview on localhost
> (`scripts/agency/preview_site.py`) → iterate → and push to Netlify only on an
> explicit operator go. Do not auto-deploy a bespoke build.

> **Build-spec is a regenerated mirror.** `state/prospects/batch/SUBAGENT-BUILD-SPEC.md`
> is gitignored and hand-synced from this playbook + `demo-site-learnings.md`.
> Whenever the **Hard rules**, **§5 Verify**, or any subagent-facing rule changes
> here, re-port the deltas into the spec (its "Read first" list + the §F gate)
> before the next batch. No generator script exists yet — a stale spec means
> subagents build voiceless.

After each build, append what worked / what burned us to
**`docs/demo-site-learnings.md`**. That file is the bridge to automation: when a
rule holds across ≥3 builds, it graduates into a default, a check, or a template.

## Manual vs automatable (be honest)

- **Agent-driven (default):** the gather end-to-end — Place Details, photo download,
  **and the browser pull of Yelp/BBB/Birdeye/booking/FB-public** (proven on Duval:
  the agent ran the full Yelp read itself), the integrity check, the verify grep,
  and the deploy.
- **Judgment (human, or strong agent + verify loop):** photo curation, reading
  reviews to find what's *really* true, writing grounded copy, and the design.
  The quality bar here wants a review loop, **not** blind templating — that's the
  whole point of moving off v1.
- **Operator-only (never the agent):** the **integrity disqualify/proceed call**,
  the brand sign-off, the **ship-it** approval, and the **send** approval.

## Status

- v1 (template-fill) — deprecated for client demos; produced generic copy.
- v2 (this playbook) — proven on Skyline Nails + Café Ollama. Gather is now
  **agent-first** (browser-driven, with a mandatory integrity check) as of the
  Duval run; human-in-loop is reserved for gaps and judgment.
