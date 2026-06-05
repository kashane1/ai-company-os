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
- `[COPY]` **Per-business voice + AI-tell self-critique gate** (0 builds — graduates
  at ≥3). Derive voice from THIS business's data via
  `docs/products/better-business-web/gtm/demo-voice-framework.md`; never a template
  phrase. At generation, pull the genre lead-with row + say-this-not-that examples
  into the prompt (fix the input). In verify, run the AI-tell gate: whitelist the
  business's own name tokens, `grep -iF` the "Banned everywhere" words from
  `gtm/voice.md`, then an LLM pass for constructions / em-dash budget (~1/500) /
  rhythm / clichés / unbacked claims — **iterate until clean**. English-only list;
  don't grep non-English body copy. Don't attach a real reviewer's name to a
  paraphrase (unattributed / aggregate only).
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

## Batch build — 2026-06 (34 sites, 15 genres, local-only)

Ran the playbook at scale: one bespoke local demo per business across bakery,
barber, beauty/hair, dog groomer, massage, notary, restaurant, roofer, tutoring,
music, house-cleaning, electrician, plumber, accountant, landscaper (+ the earlier
nail/auto/coffee). All local builds + local screenshots, **no deploy**.

- `[PROCESS]` **Google rich-gather alone is enough to build a grounded bespoke page**
  at volume. New committed script `scripts/agency/gather_place.py` pulls an extended
  Place Details mask (5 review texts + up to 10 photos + attributes/payments/hours)
  and downloads photos — mirrors the Skyline layout. Yelp/IG/FB add depth but are
  **not required per-business at scale, and unsafe to parallelize** across one
  account. Reserve the browser pass for flagships.
- `[PROCESS]` **Per-business subagents don't converge on a template** when each is
  told to *derive the palette + fonts from THAT business's own photos* and is shown
  ≥2 differently-styled exemplars as "match the craft, not the look." Spec lives in
  `state/prospects/batch/SUBAGENT-BUILD-SPEC.md`. Proof: three barbershops (bold
  black/red, late-night crimson, parchment/navy/gold), two roofers (terracotta vs
  sky-blue), two landscapers (KY lush-green vs AZ travertine), two accountants
  (cream/star-red vs hunter-green) all read as different businesses.
- `[DESIGN]` **(graduate to craft-pass) Masked gradient borders + lifted children.**
  A 1px gradient-border `::before` overlay MUST use
  `-webkit-mask:linear-gradient(#000 0 0) content-box,linear-gradient(#000 0 0);
  -webkit-mask-composite:xor;mask-composite:exclude` **and** card children must be
  `position:relative;z-index:1`. Without both, the overlay's solid fill paints over
  the card content → **blank white cards** (bit us once on a massage build; the
  Skyline/Ollama exemplars already do this — make it explicit in the spec).
- `[PROCESS]` **Service-area trades need their own structure** (roofer, plumber,
  electrician, cleaning, landscaper): NO "come visit"/map-as-destination; hero +
  services + why-us/trust + reviews + **named service area (the metro)** + process +
  FAQ; CTA = **Call + Request a quote**. Distinct from storefront/visit genres.
- `[PROCESS]` **Headless map artifact:** the Google Maps `output=embed` iframe renders
  **blank** in Playwright/Chromium full-page capture; it paints in a real browser.
  Don't treat a blank map tile in the screenshot as a defect.
- `[PROCESS]` **Contact-sheet QA:** montage the top region of every
  `review-gallery/*.png` into one grid image to eyeball a whole batch for blank/
  broken/converged pages in a single look (`state/prospects/batch/contact-sheet.png`).
- `[PROCESS]` IG and `localhost` both need a **per-domain permission grant** in the
  connected Chrome — can't be done autonomously while the operator is away.

## Genre notes (from the batch)
- **Bakery/cafe:** lead with the case/signature items + the room's character; mine
  signage/packaging photos for real menu words (Bliss: sausage bread, "fire" bread,
  macarons, vinyl/Hi-Fi interior, the "All I ever wanted was everything" neon).
- **Barber:** the differentiator is hours/walk-in/era — derive palette from the
  chair capes + sign; avoid invented prices unless a board is legible.
- **Trades (roof/plumb/electric/lawn/clean):** photos are work-shots, not storefronts
  → lean editorial/typographic, use the 1–2 best result shots big; lead on the real
  trust driver (family/generations, responsiveness, on-time) only if reviews say so.
- **Professional services (notary/accountant):** credential-forward but only *real*
  credentials; appointment framing, not retail; no fake CPA/award claims.

## Scale notes — 2026-06 (grew to 152 demos, 20 genres)

- `[FACTUAL]` **Generic Google display name → derive the real brand from reviews/photos.**
  Several listings are named "landscaping service" / "Notary Public" etc.; the true
  brand (e.g. "Arturo & Yessi Landscaping", owner names) lives in the review text and
  photo attribution. Use it, and flag the mismatch for the operator.
- `[FACTUAL]` **Watermarked work photos = independent booth renters, not the owner's
  work.** In salons/nail/lash especially, gallery photos carry other artists' IG
  handles. Use them as ambient visual proof but don't attribute them to the named
  owner; only name staff the reviews actually name.
- `[FACTUAL]` **Mine in-photo service boards for real services + prices** (Adobe
  Accounting: notary $10, translations from $35, passport photos $15; Detroit auto:
  full posted service list + 10% senior discount). Strongest grounding there is.
- `[FACTUAL]` **DBA / cross-listed names are common** (Brothers Leon ↔ "Lindsay
  Roofing"; Memphis ↔ Anchor). Keep copy attribution-safe and flag for outreach.
- `[PROCESS]` **Sub-genre routing matters:** mobile mechanic / mobile notary = "we
  come to you" (service-area), not a shop-visit; "& Sons"/"Brothers" ≠ a confirmed
  family story unless reviews say so; "Spa" in a salon name ≠ spa services without
  evidence; multiservice/notary often = Latino community one-stop (taxes+translation
  +notary). Each got its own structure/CTA.
- `[PROCESS]` **Throughput:** Google-only rich gather + one sonnet build-subagent per
  business held the bar across 152 sites. Issue the whole wave's `Agent` calls in a
  SINGLE message (they run concurrently); verify against disk
  (`ls sites/*/dist-v2/index.html | wc -l`), not narration. ~4% of businesses came
  back with <6 photos or 0 photos — swap 0-photo picks, build <6 editorially.

## Graduation log (rule → automation)
When a rule is reliable across ≥3 builds, note here what it became:
- "rich Place Details + photo download" → **`scripts/agency/gather_place.py`** (Checkpoint A).
- "per-business bespoke build" → **`state/prospects/batch/SUBAGENT-BUILD-SPEC.md`** (fan-out spec).
- "masked gradient border + lifted children" → make a hard line in `05-craft-pass.md`.
- "per-business voice + AI-tell self-critique" → wired into playbook §5 + spec §F
  (authority: `gtm/demo-voice-framework.md` + `gtm/voice.md` "Banned everywhere").
  0 builds behind it — at ≥3 clean builds, graduate the literal grep into a check
  and the self-critique into a `copy-review` call.
- _e.g. "negative-review price check" → automated guardrail in the brief step_
