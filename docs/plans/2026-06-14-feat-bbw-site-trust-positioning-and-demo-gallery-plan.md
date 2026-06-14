---
title: BBW Agency Site — Trust, Positioning & Demo Gallery (Tier 1 + Demo Rationale)
type: feat
date: 2026-06-14
product: better-business-web
status: plan
source: docs/products/better-business-web/competitor-teardown-2026.md
---

# ✨ BBW Agency Site — Trust, Positioning & Demo Gallery

## Overview

Apply the **adopt-the-structure / invert-the-proof-and-price** strategy from the
[competitor teardown](../products/better-business-web/competitor-teardown-2026.md)
to the live BBW landing experience. Scope is deliberately narrow: the **Tier 1
messaging/trust/CTA layer** plus one Tier 2 item — a **demo gallery with a
design-rationale breakdown per demo**. Everything else is parked in the companion
brainstorm (`docs/brainstorms/2026-06-14-bbw-agency-site-transformation-part-2-brainstorm.md`).

The whole point: those six agencies prove themselves with client logos,
testimonials, and quantified case studies. **We have zero clients.** So we prove
ourselves a different way — a free working preview, real sample sites with the
thinking shown, and loud risk reversal — and we lean into the one thing they
structurally can't do: **transparent pricing and "the person who builds it is the
person you talk to."**

## Problem Statement / Motivation

The current landing ([LandingV2.astro](../../products/better-business-web/site/src/components/LandingV2.astro))
is clean and on-voice but under-converts because it leaves proven levers on the table:

1. **The hero has no CTA button at all.** The strong headline just sits there; the
   only path to the `#review` form is scrolling. (Confirmed: `v2-actions` is styled
   but never populated.)
2. **Risk reversal is implied, not stated as a unit.** "$0 before you say yes /
   cancel anytime / you own it" is the single strongest trust signal for a no-client
   studio, and it's scattered across prose instead of being a scannable bar.
3. **No positioning against the alternative.** A visitor has no frame for *why*
   we're cheaper than a "real" agency. The underdog/affordability story is missing.
4. **The demo page is a flat grid.** [demos.astro](../../products/better-business-web/site/src/pages/demos.astro)
   shows name + type + "Open" with no explanation of *why each site works* — so the
   demos prove "they can make a nice page" but not "they understand what makes a
   small-business site sell." The design thinking is invisible.

## Proposed Solution

Six Tier-1 edits to the landing + a demo-rationale layer on the demos page. No new
pages, no new dependencies, no pricing-number changes (those are in the brainstorm).

### Scope (in)
- **T1-1** Hero CTA buttons (primary + secondary), keep the existing headline.
- **T1-2** First-scroll demo proof made explicit and clickable.
- **T1-3** Risk-reversal trust bar (new scannable unit).
- **T1-4** Nav accent CTA + standardized preview CTA label sitewide.
- **T1-5** Honest stats block refinement (no invented numbers).
- **T1-6** Founder-direct line on the landing (not just the footer).
- **T1-7** Underdog / affordability differentiator section (the new positioning copy).
- **T1-8** Clarify **preview vs review** on the form section: fix the conflated
  terminology, add a "Free preview" explainer card **above** the existing "Review
  map" card, and decide the form's placement (keep near bottom vs. surface near hero).
- **T2-7** Demo gallery: add `rationale` + `highlights` to each demo and render a
  "why this works" breakdown on the demos page.

### Scope (out — see brainstorm)
Before/after teardowns, the metric-ready case-study template, qualifying-form
fields, teaching FAQ, all Tier 3 SEO/content, and every pricing-number decision
(price reduction, promo anchoring, $0-down, Conversion Lab placement).

## ✅ Decision (resolved 2026-06-14) — Voice: hybrid "we" + "I"

Resolved with the founder. The hybrid:
- **"We"** for company/marketing sections (hero subhead, underdog/affordability,
  trust bar) — matches the live site and the underdog positioning.
- **"I / Kashane"** reserved for the founder-direct line (T1-6) and footer (personal corners).
- **`voice.md` must be reconciled** to the evolved brand (relax the strict
  first-person / studio-of-one rule to permit "we" in marketing copy while keeping
  the studio-of-one honesty intent), and its **`copy-review` fixtures re-run** (the
  file header requires this). Treat as a coordinated change tracked in Phase 1, not a
  casual edit. Until reconciled, `/copy-review` will flag the "we" copy — expected.

## Technical Considerations

- **Astro, static.** All work is `.astro` components + `.mjs`/`.json` data + CSS.
  No runtime, no new deps. Mirrors existing patterns exactly.
- **Where copy lives:** stats and story panels already live in
  [landing-v2.mjs](../../products/better-business-web/site/src/data/landing-v2.mjs);
  hero copy is currently inline in `LandingV2.astro`. **Decision:** put all *new*
  structured copy (risk bar, underdog block, founder line) in `landing-v2.mjs` so
  copy-review has one file to scan and the component stays presentational.
- **Copy-review gate.** Every new/changed string must pass `/copy-review` against
  `voice.md` before commit: no banned words (elevate, transform, seamless, robust…),
  em-dash budget ~1 per 500 words, no rule-of-three padding, no AI-tell constructions.
- **No invented proof.** Per integrity rules: demo rationales describe *design
  intent*, never claimed client results or metrics (we have no clients). No fake
  stats, no fabricated testimonials, no implying demos are paying customers.
- **Mobile.** Recent commits fixed mobile horizontal scroll; the trust bar and
  underdog section must be verified at ~380px (no overflow).
- **Accessibility.** CTA buttons need discernible text; trust-bar chips are text,
  not icon-only.

## Detailed Work Items

### T1-1 — Hero CTA buttons
**File:** `LandingV2.astro` (hero block ~L13–57), reusing the existing `.v2-actions` container.
- Add primary CTA **"Get my free preview →"** → `/#review`.
- Add secondary (ghost) CTA **"See pricing"** → `/pricing`.
- Keep headline `"See your new website before you pay for it."` (already on-voice).
- House rule says CTAs belong at section *bottom*; the hero is the exception every
  competitor makes (above-the-fold primary action). Keep it to the two buttons.

### T1-2 — First-scroll demo proof
**File:** `LandingV2.astro` (device stage already rotates 4 featured demos).
- Add a short, clickable label under/beside the rotating device: **"Real sample
  sites we've built →"** linking to `/demos`. Turns ambient animation into an
  explicit, navigable proof point.

### T1-3 — Risk-reversal trust bar
**Files:** new `riskBar` array in `landing-v2.mjs`; new section in `LandingV2.astro` (after stats).
- Three factual chips (proposed copy, pending copy-review):
  - "$0 before you say yes"
  - "Cancel the monthly anytime"
  - "You own your site and everything on it"
- Plain text chips, responsive wrap, no icons required.

### T1-4 — Nav accent CTA + label standardization
**Files:** `SiteNav.astro`, plus a sweep of `demos.astro` / `ReviewForm.astro`.
- Add an accent button to nav (currently Intro / Demos / Pricing with no CTA):
  **"Get a free preview"** → `/#review`.
- Standardize the preview CTA wording. Today there are two variants — demos uses
  "Get a free preview →" and the form button says "Get my free review →". Pick one
  family. Proposed: **"Get my free preview →"** for navigation/links; keep the form
  submit button distinct ("Get my free review →" is fine on the form itself).

### T1-5 — Honest stats block
**File:** `landing-v2.mjs` (`stats`, L5–10).
- Keep the three true stats ("2 days", "$0", live demo count).
- Optional 4th only if true (e.g. flat-rate transparency). **No invented numbers.**
  If nothing else is honestly available, leave at three.

### T1-6 — Founder-direct line
**Files:** `landing-v2.mjs` (`founder` copy); `LandingV2.astro` (small block, likely near underdog section).
- One short first-person line, e.g. **"Hi, I'm Kashane. I build every site myself,
  so the person you talk to is the person doing the work."**
- This is the natural home for first-person voice even under the hybrid resolution.

### T1-7 — Underdog / affordability section *(the new positioning)*
**Files:** `landing-v2.mjs` (`pitch`/`underdog` copy); `LandingV2.astro` (new section, lower on page near the pricing hand-off).
- Company "we" voice, concrete, earnest (not hype). Proposed copy (pending copy-review):
  > "A top agency would charge $8,000 to $15,000 to build a site like this, then
  > bill you every month after. We're a newer, smaller studio still building our
  > name, so we charge a fraction of that. You get the same careful work, and you
  > deal with the person actually building your site."
- **Trade-off to weigh:** "still building our name" is honest and pairs the lower
  price with personal attention, but could read as "unproven." The mitigation is to
  lead with the *value* (lower price + you talk to the builder) and let "growing"
  be the *reason*, not an apology. Keep the agency comparison number defensible.
- **Voice risk:** the word "agency"/"studio still building our name" brushes against
  `voice.md`'s studio-of-one rule — covered by the blocking decision above.

### T1-8 — Clarify preview vs review + add the preview offer card
**Files:** `ReviewForm.astro` (copy + a second aside card); optionally `index.astro` (placement).

**Canonical definitions to encode (from LANDING_PAGE_PLAN §1):**
- **Free preview** = we *build* a real, clickable preview of a *new* site for their
  business; output is a link to their own new site; delivered within ~2 business
  days (operator-built, not instant). The spine of the offer.
- **Free review** = we *look at* their *existing* site against the 6-point map;
  output is plain-English feedback (what's working / what's costing customers /
  what to fix first). Secondary entry point.
- **Both** = review the current site, then preview a better version.

**Work:**
1. **Fix the conflated copy.** The section eyebrow says "Free review" while the H2
   says "Get a free preview" — make the section clearly offer *both* (e.g. eyebrow
   "Free preview & review", and a header line that names the two). The three radio
   intents already encode the split correctly (keep them; they're well-written).
2. **Add a "Free preview" card above the existing "Review map" card.** The aside
   becomes a two-card stack:
   - **New — "Free preview"** (on top): what you get is a real new website for your
     business, built before you pay, sent within ~2 business days. Proposed copy
     (pending copy-review): "Tell us about your business and we build a real,
     clickable preview of a new site, just for you. You see the finished look before
     you pay anything. It lands in your inbox within two business days."
   - **Keep — "Review map"** (below): the existing 6-point list for the current-site
     review. Unchanged.
3. **Form placement decision.** Currently the form sits at the page bottom
   (`ReviewForm` after `LandingV2` in `index.astro`). Options: (a) keep at bottom,
   (b) lift the whole block to just below the hero, (c) leave the form where it is
   but add a hero CTA that anchors to it (already covered by T1-1). **Recommend (c)
   for this plan** — the hero CTA gives early access without a layout overhaul; a
   full move to (b) can be a fast follow if we want the form higher.
4. **Keep the free offers visually distinct from the paid Conversion Lab** — don't
   let the two free cards read as the same thing as the $100/$250 audits.

**Constraint:** the preview card must not promise instant/self-serve delivery
(it's operator-built ~2 days) — honesty per LANDING_PAGE_PLAN §1.

### T2-7 — Demo gallery with design-rationale breakdown
**Files:** `portfolio.json` (add fields to each demo); `demos.astro` (render them).
- Add to each demo object:
  ```json
  {
    "name": "Ironside Auto Works",
    "type": "Auto repair",
    "rationale": "Most auto shops bury their phone number and hours. This one leads with a tap-to-call button and a plain 'what we fix' list, so a driver with a check-engine light knows in five seconds they can call right now.",
    "highlights": ["Tap-to-call in the header", "Plain 'what we fix' list", "Reviews near the top", "Reads well on a phone"]
  }
  ```
- Render a short rationale + 3–4 `highlights` under each demo card on `demos.astro`
  (Clay's "named themed vignette" idea, shrunk to a card).
- **Content task, on-voice, no claimed results.** Write rationales for the **4
  featured demos first** (`dog-grooming`, `fish-tacos`, `auto-repair`, `gun-store`),
  then backfill the remaining 6. Featured-4 is the launch bar; all-10 is the
  done bar.

## Acceptance Criteria

### Functional
- [ ] Hero renders a primary "Get my free preview →" CTA (→ `/#review`) and a ghost "See pricing" CTA (→ `/pricing`).
- [ ] A clickable "Real sample sites we've built →" proof link points to `/demos`.
- [ ] A risk-reversal trust bar with three factual chips renders after the stats.
- [ ] Nav shows an accent "Get a free preview" CTA; preview CTA wording is consistent across nav/links.
- [ ] Stats block contains only true values (no invented numbers).
- [ ] A first-person founder line appears on the landing.
- [ ] The underdog/affordability section renders with the agreed (copy-reviewed) copy.
- [ ] The form section names **both** offers clearly (no preview/review conflation), and a "Free preview" card sits above the kept "Review map" card.
- [ ] The preview card sets honest expectations (built within ~2 business days, not instant); the two free offers stay visually distinct from the paid Conversion Lab.
- [ ] Each demo on `demos.astro` shows a rationale + highlights; all 10 populated (featured 4 minimum to ship).

### Quality gates
- [ ] All new/changed copy passes `/copy-review` against `voice.md` (no banned words, em-dash budget, no AI tells).
- [ ] No fabricated metrics, testimonials, or client claims anywhere.
- [ ] Verified at ~380px (no horizontal scroll) and desktop.
- [ ] `npm run build` succeeds; landing + demos verified in preview before deploy.
- [ ] The "I vs we" blocking decision is resolved and `voice.md` reconciled (fixtures re-run if edited).

## Implementation Phases

**Phase 1 — Decision + data (fast).** Resolve the voice fork; add `riskBar`,
`founder`, `pitch` copy to `landing-v2.mjs` and `rationale`/`highlights` to the 4
featured demos in `portfolio.json`. Run `/copy-review` on the drafts.

**Phase 2 — Landing wiring.** Hero CTAs, proof link, trust bar, founder line,
underdog section in `LandingV2.astro`. Nav accent CTA in `SiteNav.astro`. Label sweep.

**Phase 3 — Demo gallery.** Render rationale/highlights on `demos.astro`; backfill
the remaining 6 demo rationales.

**Phase 4 — Verify + ship.** Mobile + desktop preview check, `npm run build`,
screenshots per the demo-site screenshot habit, then `netlify deploy --prod`.

## Dependencies & Risks

- **Voice spec conflict** (blocking decision above) — highest risk; resolve first.
- **Underdog copy trust trade-off** — "growing/unproven" framing; mitigated by
  value-first wording, but get a human gut-check on the final line.
- **Agency price-comparison must stay defensible** — $8k–$15k is reasonable for
  bespoke top-tier; don't inflate.
- **Writing 10 on-voice rationales** is the real effort sink in T2-7; phased so the
  featured 4 unblock launch.
- **Deploy is manual CLI** (`npm run build` + `netlify deploy --prod --dir=dist`),
  needs `netlify login` (founder-only step).

## References

- Strategy: [competitor-teardown-2026.md](../products/better-business-web/competitor-teardown-2026.md)
- Voice gate: [gtm/voice.md](../products/better-business-web/gtm/voice.md), [copy-voice brainstorm](../brainstorms/2026-06-05-bbw-copy-voice-system-brainstorm.md)
- Deferred scope: `docs/brainstorms/2026-06-14-bbw-agency-site-transformation-part-2-brainstorm.md`
- Files: `LandingV2.astro`, `landing-v2.mjs`, `pricing.astro`, `demos.astro`, `portfolio.json`, `SiteNav.astro`, `SiteFooter.astro`, `ReviewForm.astro`
</content>
