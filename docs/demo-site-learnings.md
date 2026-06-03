# Demo Site Learnings — rules we're discovering

The living rulebook for building genuine demo sites. Every build adds what
worked and what burned us. **When a rule here becomes reliable, it graduates
into scaffolding/automation** (a default, a check, a template choice). This file
is the bridge from "human judgment" to "repeatable process."

Companion to `docs/demo-site-build-playbook.md`. Each rule tagged:
`[FACTUAL]` truth/grounding · `[COPY]` voice · `[DESIGN]` look · `[PROCESS]` workflow.

---

## Universal rules (apply to every business)

- `[DESIGN]` **Derive the palette from the business's own visual cues** — storefront
  paint, signage, logo, recurring photo colors. One dominant canvas + ONE sharp
  accent. (King: hand-painted red storefront → red/white/minimal-blue. It reads
  authentic and local, not invented.)
- `[DESIGN]` **Scroll-triggered count-ups must carry their final value as static
  text** (e.g. `<span ...>4.5</span>`, not `0`). The count-up is a live
  enhancement only — if you start at `0`, the number renders "0" in screenshots
  and on first paint before it scrolls into view. (Bit us on King's stats band.)
- `[DESIGN]` **Every demo gets the granular Craft Pass** (`_scaffold/05-craft-pass.md`):
  distinctive type + tabular price numerals, palette + ~3% grain + soft glow (kill
  the flat-AI look), multi-layer elevation + gradient borders + bento grids,
  reduced-motion-gated scroll reveals + count-ups, micro-interactions, an
  on-message hero, section polish (device frames, animated FAQ, favicon/OG). This
  is the line between "clean template" and "premium custom build."
- `[FACTUAL]` **Mine the photos for hard data, not just vibes** — read signage in
  the images. (King's storefront photo gave a real price menu + dealer comparison;
  another photo gave ASA membership + NC inspection-station credentials.)
- `[COPY]` **The "lead-with" angle is genre-specific.** Nails → the work + the
  experience. Auto repair → honesty / transparent pricing / no-upsell (the genre's
  core distrust). Don't reuse one value prop across genres.
- `[PROCESS]` **Yelp + booking + FB-public are agent-automatable** via the
  operator's connected Chrome (read-only, paced — see
  `demo-site-gather-automation.md`). Yelp loads with **no captcha** and
  `get_page_text` returns more than a human quick-paste (all reviews + owner
  replies + full service/amenity lists). FB shows public Intro/tagline/price even
  behind its login wall; full FB/IG feed needs the operator logged in. The agent
  **never enters credentials or solves captchas** — if a wall appears, flag it.
- `[PROCESS]` **Triangulate sources** — Google (facts/photos/5 reviews) + Yelp
  (neighborhood, owner About, full service list, more reviews, amenities) +
  storefront photo (prices/credentials) + human (brand call). Each fills a gap the
  others miss.


- `[FACTUAL]` **Every claim cites a source in the brief.** No source → cut it.
- `[FACTUAL]` **Read the *negative* reviews before writing.** They tell you what
  NOT to claim. (Skyline: 1–2★ complained about price → we did not claim "cheap".)
- `[FACTUAL]` **Verify any booking link is owner-managed before using it as a CTA.**
  Aggregators (Fresha/Booksy/etc.) host "unaffiliated" listings that look real but
  don't reach the owner. (Skyline: Fresha page said "not affiliated" → we switched
  the CTA to Call + walk-in.)
- `[FACTUAL]` **Don't feature services found only on an unaffiliated aggregator's
  auto-list** (likely a category default, not their real menu). Needs a 2nd source.
- `[FACTUAL]` **Don't use low-tier directory "awards"** (BusinessRate-type plaques)
  as credentials.
- `[COPY]` **Reviews are input → paraphrase, never verbatim.** First-name + "Google/
  Yelp" attribution.
- `[COPY]` **Named staff are a real trust signal** — if reviews name techs/owners,
  use them ("Nikki took her time…").
- `[PROCESS]` **CTA matches how they actually take customers.** Phone-only/walk-in
  businesses → lead with Call + walk-in, not a booking button.
- `[PROCESS]` **Full-page screenshot is a required step, captured from localhost
  before Netlify** — `scripts/agency/screenshot_demo.py` (engine: `shoot.mjs`).
  Versions every iteration in the business `screenshots/` folder and mirrors the
  newest into the flat `state/prospects/review-gallery/` so a batch of businesses
  is reviewable from one folder. The **final screenshot is the last action before
  deploy**; supports `--all` to batch. Capture from localhost, not the live site.
  (Playwright/Chromium full-page beats driving the visible Chrome, which is
  viewport-only — and our localhost builds render identically headless.)
- `[PROCESS]` **Build → preview locally → iterate → deploy is a SEPARATE, gated step.**
  Never auto-deploy a bespoke build. Preview with `scripts/agency/preview_site.py`
  (localhost); push to Netlify only on an explicit "ship it."
- `[PROCESS]` **Deploy with the file-digest method, not zip** (zip serves the page
  as text/plain). One clean Netlify subdomain per business.

## Photos

- `[DESIGN]` Google photos are customer-submitted — expect hands-in-cars, mixed
  quality. **Curate hard**: pick shots that show the craft + 1–2 interior/space.
- `[DESIGN]` They skew **portrait** → use a masonry/column gallery, not a fixed
  square grid.
- `[PROCESS]` Best photo source for visual genres (nails/hair/bakery) is usually
  the owner's **Instagram** — a human pick beats the Google set. (Human-in-loop slot.)

## Genre notes

### Nail salon / beauty (from Skyline Nails)
- `[DESIGN]` Lead with the **work gallery** — it's a visual-proof genre.
- `[DESIGN]` Warm, boutique palette (blush/plum/cream), elegant serif display +
  clean sans read as "salon," not "SaaS."
- `[COPY]` Real hooks that landed: complimentary drink, walk-ins welcome, "sets
  that last weeks without a chip," chrome & cat-eye specialty, custom art.
- `[FACTUAL]` Confirmed services to anchor on: custom nail art, acrylic full sets,
  gel & dip, pedicures, chrome/cat-eye finishes.

### Auto repair (TBD — biggest genre, 11 sites)
- _add after first auto build_

### Bakery / cafe (TBD)
- _add after first bakery build_

---

## Graduation log (rule → automation)
When a rule is reliable across ≥3 builds, note here what it became:
- _e.g. "negative-review price check" → automated guardrail in the brief step_
