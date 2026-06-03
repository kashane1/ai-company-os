# Better Business Web — Landing Page Plan (v1)

**Status:** plan only — not started. Read and approve before any build work.
**Product id:** `better-business-web`
**Related:** [todos/064](../../../todos/064-pending-p3-netlify-funnel-page-for-agency.md) · [WaaS prospecting lane](../../waas-prospecting-lane.md) · [agency catalog](../../../packages/agency/catalog.yaml)

This is the agency's **own** public funnel/landing page (the "validation asset"
the wedge brief calls for), distinct from the per-client preview demos built by
`packages/agency/prospect_site.py`.

---

## 1. Name & positioning (locked)

**Better Business Web**

- **Tagline:** Web design for small businesses — previewed before you pay.
- **Hero H1:** A better website for your business — previewed before you pay.
- **Hero sub:** I build clean, modern websites for small businesses. You'll get
  a real preview link first, so you can see exactly what your new site looks
  like before paying.
- **Attribution:** A small web studio run by Kashane Sakhakorn.

The "previewed before you pay" promise is the spine of the page — it is the real,
defensible edge (preview sites are built before contact), so it leads the hero
and reappears in the CTA. Everything else supports it.

## 2. Pricing — halve the catalog (source-of-truth change)

Zero customers today, so every price is halved and that becomes the agency's real
starting point. The change is made in [`packages/agency/catalog.yaml`](../../../packages/agency/catalog.yaml)
itself — **not** as a display-only markdown on the page — so signed `OFFER.md`
and the landing page never drift.

| Service | Now | Halved |
|---|--:|--:|
| Professional Website (setup) | $999 | **$499** |
| Hosting & Maintenance (mo) | $99 | **$49** |
| Google Business Profile | $350 | **$175** |
| Business Email | $200 | **$100** |
| Contact Forms & Lead Routing | $150 | **$75** |
| Online Booking | $500 | **$250** |
| Review Generation (mo) | $99 | **$49** |
| Local SEO (mo) | $249 | **$125** |
| Analytics & Reporting (mo) | $49 | **$25** |
| Promo Landing Page | $350 | **$175** |
| Google Ads mgmt (mo) | $750 | **$375** |
| Meta Ads mgmt (mo) | $750 | **$375** |
| CRM Setup | $500 | **$250** |
| Automated Follow-Up (mo) | $99 | **$49** |

Bundle "starting at" anchors at halved prices (bundles already exist in the
catalog as `package_a/b/c`):

- **Package A — Presence:** from **$774 setup + $49/mo** (website, hosting, GBP, business email)
- **Package B — Presence + Capture:** from **$1,024 setup + $98/mo** (A + booking + reviews)
- **Package C — Presence + Growth:** from **$1,199 setup + $247/mo** (B + local SEO + promo page + reporting)

The page renders these from the catalog at build time so they cannot go stale.

## 3. v1 scope — minimal cut

One page, these sections only:

1. **Hero** (copy above) + two CTAs: `Get a free website review` (primary) /
   `See demo sites` (anchor to portfolio).
2. **Problem** — short, constructive: no site / outdated / social-only, customers
   can't self-serve. Never implies a specific business is failing (wedge-brief
   honesty boundary).
3. **How it works** — 4 steps ending in the preview promise: Review your current
   presence → I build a preview → You see the real link → Approve & launch.
4. **Packages** — the three bundles, rendered from catalog, "starting at" pricing.
5. **Portfolio** — the rebranded demos (see §4).
6. **About** — attribution line, personal-operator angle.
7. **Contact / CTA** — Netlify Form: "Request your free website review."

**Deferred to v2 (logged, not started):** per-demo `/work/[slug]` case-study
pages, full à-la-carte services matrix, scheduling / Stripe / CRM embeds.

## 4. Portfolio — 6 genres, rebranded so nothing is real or cookie-cutter

Showcase **6 genres** (trimmed from the 18 built):

> auto repair · barbering · baked goods · dog grooming · plumbing · nails

Two non-negotiable transforms on each demo before it goes on a public page:

- **Anonymize (consent/honesty).** The built demos use real Places data for real
  businesses not yet signed — real names, hours, ratings. None of that can be
  published. Each portfolio demo gets a **fictional business name + fictional
  town** and swapped hours/services/review counts. Labeled honestly as
  *"Concept demo — [genre]."*
- **De-cookie-cutter.** Today every demo uses the same template, so they would
  look like one page in 18 hats. Each portfolio demo needs **meaningful visual
  variation** — palette, layout/hero treatment, section ordering. This is
  upgraded by the smarter-demo work that runs first (see
  [smarter-demos-plan.md](../../agency/smarter-demos-plan.md)) and benefits the
  portfolio directly.

## 5. Structure & tech

Per repo product convention and todos/064:

- **Source:** `products/better-business-web/` — built from the existing
  `packages/web/scaffold/astro-landing` scaffold (Astro static +
  `netlify/functions/` already stubbed).
- **Artifacts/brief:** `docs/products/better-business-web/` (this folder).
- **Form:** Netlify Forms to start.
- **Demos:** rendered as static pages / screenshots embedded in the portfolio.

## 6. Ship workflow (gated)

**build → preview (disposable `preview-…netlify.app`) → operator approves → production.**

Matches the `deploy_readiness` production gate. Custom domain / DNS is a separate
approval gate; v1 can launch on the Netlify subdomain and add a domain later.

## 7. Guardrails (carried from the wedge brief)

- No real prospect business appears on the page (all demos fictional).
- Demos labeled "concept demo," never implied as live client work.
- Problem copy stays constructive — never "your business is failing."
- Nothing auto-sends; the contact form only collects inbound for the operator.

## 8. Sequencing

1. **Smarter-demo generator upgrade runs first** (separate task) — better demos
   improve both client previews and this portfolio.
2. Then: halve catalog → scaffold `products/better-business-web/` → build v1
   sections → preview → approve → production.
