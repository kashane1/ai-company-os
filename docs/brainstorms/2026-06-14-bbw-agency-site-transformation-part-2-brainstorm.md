---
date: 2026-06-14
topic: bbw-agency-site-transformation-part-2
product: better-business-web
status: brainstorm
source: docs/products/better-business-web/competitor-teardown-2026.md
related_plan: docs/plans/2026-06-14-feat-bbw-site-trust-positioning-and-demo-gallery-plan.md
---

# BBW Agency Site Transformation — Part 2 (Deferred Backlog)

## What this is

The parking lot for everything from the [competitor teardown](../products/better-business-web/competitor-teardown-2026.md)
that we deliberately pulled **out** of the first plan. Part 1 (now a plan) ships the
Tier 1 trust/positioning/CTA layer plus the demo-rationale gallery. This doc holds
the rest so it isn't lost: the Tier 2 leftovers, all of Tier 3, and the open pricing
decisions. Nothing here is committed; it's a ranked idea set for future planning.

**Guiding frame (unchanged from Part 1):** we adopt the agencies' *structure,
outcome positioning, and SEO engine*, but invert their *proof* (demonstration, not
testimonials — we have zero clients) and their *price* (transparent and simple, the
underdog wedge). No fabricated proof, ever.

---

## A. Pricing decisions (highest priority — these gate other copy)

You rejected the three forks I first proposed (promo strikethrough, $0-down option,
Conversion-Lab-as-entry). Your direction instead:

1. **Reduce prices a bit more.** Open: by how much, and on which packages?
   - Current: A $600+$50/mo · B $900+$90/mo · C $1,800+$550/mo (`packages.json`).
   - Decide whether to cut setup, monthly, or both; and whether the cut is permanent
     or a "founding customer" rate. The **underdog/affordability copy in the Part 1
     plan should quote whatever the final numbers are** — so this decision feeds that
     section's final wording.
2. **Lean the whole pricing story into the underdog position.** Transparent, simple,
   "a fraction of what a top agency charges." This is the deliberate differentiator
   vs. the five hide-the-price agencies.
3. **Conversion Lab ($100/$250) placement** — still open: keep it as a clearly
   secondary section/sub-page (an "already have a site?" entry + client upsell), not
   a primary funnel CTA. (Revisit when Tier 3 #15 below is planned.)

**Open question:** is there a floor below which "cheap" starts to *cost* trust for a
no-client studio? Worth a deliberate take — lower price helps conversion but can
signal "unproven." The underdog copy is what lets a low price read as "hungry and
fair" instead of "cut-rate."

---

## B. Tier 2 leftovers (proof system, beyond the demo gallery)

### B1. Before/after teardowns *(strong — your existing teardown-teaser lane)*
A real local business's current site next to our rebuilt preview, side by side. This
is arguably the **best proof asset we can have without clients**: visual, concrete,
honest, implies no client relationship. Ties directly to the existing
`build_teardown_teaser.py` lane and the no-invented-findings gate. Likely the first
thing to promote out of this backlog once Part 1 ships.

### B2. Metric-ready case-study template *(build the slot now, fill later)*
A case-study layout (challenge → approach → result bar → quote) that ships populated
with demo/teardown content today, with empty metric+quote slots ready for client #1.
The teardown's sharpest finding: all six agencies have metric-light case studies, so
the moment we have one real quantified result we out-prove a 25-year-old agency. Build
the container before the content exists.

### B3. Qualifying lead form
Add intent/budget selector + service-interest checkboxes to
[ReviewForm.astro](../../products/better-business-web/site/src/components/ReviewForm.astro)
so leads self-segment (DD.NYC / 500designs pattern). Keep it short and conversational;
don't add friction that hurts the free-preview conversion. Decide whether a budget
field even fits a transparent-pricing brand (maybe not — we already show prices).

### B4. Teaching FAQ
Answer the real objections of a skeptical SMB buying from a new shop: "How can it be
free?", "What if I don't like it?", "Do I own it?", "Why a monthly fee?". Doubles as
SEO (People-Also-Ask) and objection-handling. On-voice, calm, specific.

---

## C. Tier 3 — SEO + content engine (ongoing, compounding)

### C1. Programmatic service × industry × city pages
The actual ranking engine all six use (Lounge Lizard's 44 industry pages, Upqode's 32
cities). Scaled to our reality: start with our existing demo trades (dog grooming,
auto repair, restaurants, etc.) × a few target cities. Each a small conversion page.
Highest-leverage SEO move; also the biggest build. Needs its own plan.

### C2. Buyer-intent, transparent-by-design blog
Our positioning unlocks content the agencies can't write honestly: **"How much should
a small-business website actually cost in 2026?"** answered with real numbers, funneling
to our transparent packages. Use the Dotlogics article template (Key-Highlights box →
scannable H2s → FAQ). A handful of high-intent posts beats volume.

### C3. Light lead magnet
A gated "small-business website checklist" or scorecard to capture the not-ready-yet
visitor (everyone in the teardown has one; we have none). Keep it genuinely useful and
low-friction (3 fields).

### C4. Conversion Lab as its own funnel
Give the $100/$250 products a dedicated page targeting "my site isn't working"
searchers — a lower-commitment entry that can upsell into a rebuild. Resolves the
Conversion-Lab placement question (A3) by giving it a real home off the main funnel.

---

## D. Explicitly NOT doing (from the teardown, rejected for our model)

- **Client logo walls / named testimonials / quantified client case studies** — we
  have no clients; copying these would mean faking proof. Revisit only when real.
- **Awards walls, "senior team," enterprise/Fortune-500 signaling** — wrong tier;
  we're SMB-accessible, not prestige.
- **Hide-the-price "contact us for a quote"** — the opposite of our wedge.
- **12,000-word self-ranking "best agencies" listicles** — overkill at our stage;
  a lighter "best [trade] website examples" angle could work later.

---

## Suggested promotion order (when Part 1 ships)

1. **Pricing decision (A1)** — unblocks the underdog copy's final numbers.
2. **Before/after teardowns (B1)** — best no-client proof, lane already exists.
3. **Metric-ready case-study template (B2)** — cheap to build, huge once a client lands.
4. **Teaching FAQ (B4)** — quick, on-voice, SEO + trust.
5. **Buyer-intent cost-guide post (C2)** — leans straight into the transparent wedge.
6. **Programmatic SEO pages (C1)** — biggest build; its own plan.
7. **Lead magnet (C3)** + **Conversion Lab funnel (C4)** + **qualifying form (B3)**.

## Next step

→ Ship the Part 1 plan first. Then run `/workflows:plan` on items in promotion order,
starting with the pricing decision (A1) since it feeds copy already in Part 1.
</content>
