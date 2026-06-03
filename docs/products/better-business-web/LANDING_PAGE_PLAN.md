# Better Business Web — Landing Page Plan (v2)

**Status:** plan — approved direction; technical review incorporated. Not built.
**Product id:** `better-business-web`
**Related:** [todos/064](../../../todos/064-pending-p3-netlify-funnel-page-for-agency.md) · [WaaS prospecting lane](../../waas-prospecting-lane.md) · [agency catalog](../../../packages/agency/catalog.yaml) · [smarter-demos-plan](../../agency/smarter-demos-plan.md)

This is the agency's **own** public funnel/landing page (the "validation asset"
the wedge brief calls for), distinct from the per-client preview demos built by
`packages/agency/prospect_site.py`.

> **v2 changelog** — this revision folds in the technical review:
> pre-render (no Node build), two new template sections, catalog-driven pricing
> with a mirror generator, `/work/[slug]` first-party portfolio pages, real
> Netlify Forms wiring, and a first-party launch gate. See §9 for the
> finding-by-finding resolution.

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
and reappears in the CTA.

**Promise → delivery (must stay traceable).** The hero sells "a real preview link
first," so v1 fulfillment cannot be an audit alone. An inbound request is
fulfilled by **generating a first-party preview of the requester's own site via
the existing prospect-site lane** (`packages/agency/prospect_site.py` /
`scripts/agency/build_prospect_site.py`) — operator-triggered for v1 — exactly as
the agency already builds previews before contact. The Stage-2 audit (§10) is a
secondary enrichment, not the thing the hero promised. If the preview step is not
in v1, the hero copy must be narrowed to "free website review" instead — do not
ship a promise v1 cannot keep.

## 2. Pricing — halve the catalog (source-of-truth change)

Zero customers today, so prices are reset to a clean starting point. Pricing is
**bundle-anchored**: the operator picks the three productized package ladders
(A/B/C) as round "from" numbers, and the per-service prices are set so each
bundle's `quote_bundle()` total lands exactly on its anchor. The change is made
in [`packages/agency/catalog.yaml`](../../../packages/agency/catalog.yaml)
itself — the typed, validated source of truth — so signed `OFFER.md`, the
service-catalog mirror, and the landing page never drift.

**Why bundle-anchored, not per-service-halved:** `quote_bundle` computes a bundle
as the *exact sum of its component services* ([`offer.py`](../../../packages/schemas/offer.py)
— no bundle-level price field). To show clean ladder prices without drift, the
component prices must sum to them. All values are whole dollars, so the `_money`
formatter (`{value:,.0f}`) is a no-op and totals are exact.

| Service | Old | New |
|---|--:|--:|
| Professional Website (setup) | $999 | **$499** |
| Hosting & Maintenance (mo) | $99 | **$49** |
| Google Business Profile | $350 | **$125** |
| Business Email | $200 | **$75** |
| Contact Forms & Lead Routing | $150 | **$75** |
| Online Booking | $500 | **$300** |
| Review Generation (mo) | $99 | **$50** |
| Local SEO (mo) | $249 | **$125** |
| Analytics & Reporting (mo) | $49 | **$25** |
| Promo Landing Page | $350 | **$400** |
| Google Ads mgmt (mo) | $750 | **$375** |
| Meta Ads mgmt (mo) | $750 | **$375** |
| CRM Setup | $500 | **$250** |
| Automated Follow-Up (mo) | $99 | **$50** |

> **Promo Landing Page note:** it lands at **$400** (up from $350), not halved,
> because it is the only setup-billed service unique to Package C, so its price is
> forced by `C_setup − B_setup = 1399 − 999`. If à-la-carte prices should stay
> independent of the bundle ladder, add an optional bundle-level price override to
> the schema instead — logged as a follow-up.

Bundle "starting at" anchors (computed by `ServiceCatalog.quote_bundle()` — these
mirror its exact output, verified):

- **Package A — Presence:** from **$699 setup + $49/mo**
- **Package B — Presence + Capture:** from **$999 setup + $99/mo**
- **Package C — Presence + Capture + Growth:** from **$1,399 setup + $249/mo**

**Technical constraints to honor when halving (from review):**

- The schema ([`packages/schemas/offer.py`](../../../packages/schemas/offer.py))
  requires a `one_time` service keep a **positive** `setup_fee` and a `recurring`
  service a **positive** `monthly_fee`. All halved values are > 0, so validation
  passes — but never round one to $0.
- **Halving re-quotes existing signed `OFFER.md` files** (they render from the
  same catalog via `templates.render_offer`). This is intended, but it is a
  global effect, not cosmetic.
- The mirror [`docs/agency/service-catalog.md`](../../agency/service-catalog.md)
  is a *generated render* and **no generator exists yet**. Build a small
  `render_service_catalog(catalog) -> str` in `packages/agency/templates.py`
  (peer of `render_offer`) + a `scripts/agency/render_catalog_md.py`, so halving
  regenerates the mirror instead of silently desyncing it. Add a unit test that
  the committed mirror matches the generator output (drift guard).

## 3. v1 scope — minimal cut

One page (`/`) plus the portfolio sub-pages, these sections only:

1. **Hero** (copy above) + two CTAs: `Get a free website review` (primary) /
   `See demo sites` (anchor to portfolio).
2. **Problem** — short, constructive: no site / outdated / social-only, customers
   can't self-serve. Never implies a specific business is failing.
3. **How it works** — 4 steps ending in the preview promise.
4. **Packages** — the three bundles, rendered from the catalog (new section, §5).
5. **Portfolio** — grid of the demo genres linking to first-party `/work/<slug>`
   pages (§6).
6. **About** — attribution line, personal-operator angle.
7. **Contact / CTA** — real Netlify Form (§7): "Request your free website review."

**Deferred to later (logged, not started):** full à-la-carte services matrix,
scheduling / Stripe / CRM embeds. (Per-demo `/work/[slug]` pages are pulled
**into** v1 — see §6.)

## 4. Build mechanism — Astro build, scoped exception (decided 2026-06-02)

> **Decision update (supersedes the original no-build stance; resolves todos
> 076 + 071).** This **first-party** site is built with `astro build`, *not* the
> Python no-Node render path. Rationale: this is one rarely-changed marketing
> site, so the build-minute cost is negligible — unlike the per-prospect,
> high-frequency preview lane where the no-build clamp earns its keep. Letting
> Astro build (a) removes the duplicate render path (one Astro source-of-record,
> no Python `render_*_section` twin to keep in sync — todo 076), and (b) makes
> native **Netlify Forms detection** the supported happy path instead of a thing
> to verify against a file-digest upload (todo 071).

**The prospect-preview lane is unchanged** — it stays on the no-Node /
file-digest path. The clamp applies where builds are frequent; this one site is
the scoped exception.

**This site is its own Astro project**, not the shared `astro-landing` scaffold:
that scaffold is a tokenized template copied for every prospect preview and by
`render_landing_html`, so agency-specific Packages/Portfolio sections must not
live in it. BBW gets a dedicated workspace (e.g. `products/better-business-web/site/`).

## 5. New template sections (review finding 1)

Two new sections, authored as **Astro components** in the dedicated BBW site
(per the §4 decision), not Python partials:

- **Packages pricing table** — three bundle cards (A/B/C) with name, blurb,
  included services, and the "from $X setup + $Y/mo" anchor. **Pricing is fed
  from the catalog (SoT), never hand-typed in Astro:** a generator
  (`render_catalog_json(catalog) -> dict`, peer of `render_service_catalog`, +
  `scripts/agency/render_catalog_json.py`) emits the bundle quotes to the Astro
  project's `src/data/packages.json`, regenerated whenever the catalog changes
  (same drift discipline as the markdown mirror). The Astro component reads that
  JSON at build.
- **Portfolio grid** — one card per genre (thumbnail + business type + "concept
  demo" label) linking to its `/work/<slug>` page, fed by the portfolio manifest
  (§6).

Reuse the existing design-system CSS vars; add focus states + contrast checks on
themed cards (finding 7, a11y). Because Astro builds the site, the web gate
validates the *built* `dist/` rather than a Python partial.

## 6. Portfolio integration — first-party `/work/<slug>` pages (review finding 5)

Drop the separate `bbw-portfolio` draft site and the screenshot approach. Instead
publish the 6 concept demos as **first-party pages of the landing site**:
`/work/auto-repair`, `/work/barbering`, `/work/baked-goods`,
`/work/dog-grooming`, `/work/plumbing`, `/work/nails`.

Why: clean first-party URLs (not `…--bbw-portfolio.netlify.app`), one production
deploy, no headless-screenshot pipeline, and it pulls the v2 `/work/[slug]` route
forward at lower cost than embedding screenshots. The existing
`build_portfolio_demos.py` already renders these pages; point its output at the
site's `dist/work/<slug>/index.html` instead of a separate draft site, and have
the portfolio grid (§5) link to them. Demos stay fictional + "concept demo"
labeled (guardrails unchanged).

## 7. Contact form — real Netlify Forms wiring (review finding 6)

The scaffold's `netlify/functions/` are **Stripe stubs**, not a forms handler,
and the CTA form posts to `#`. For v1:

- Convert the CTA form to a **Netlify Form**: `name="website-review"`,
  `data-netlify="true"`, a hidden honeypot field (`netlify-honeypot`), and the
  real fields (name, business, current site/none, contact).
- Netlify detects forms from the **deployed HTML**, so detection works with our
  file-digest upload **as long as the attributes are present at deploy** — but
  this must be **test-deployed and verified** before launch (don't assume).
- **Capture each submission as a typed record the platform can act on**, not just
  an inbox line. A Netlify form-submission webhook writes a `WebsiteReviewRequest`
  (a typed dataclass, peer of `ClientIntake` in
  [`packages/agency/intake.py`](../../../packages/agency/intake.py)) via `JsonStore`
  into `state/prospects/inbound/`, mirroring the outbound `ProspectRecord` pattern
  (`packages/prospecting/run.py`). The email/Slack notification is **secondary**,
  not the system of record. "Manual for v1" then means *manual trigger of an
  automatable step* (preview/audit), not manual data re-entry.
- **Treat the submitted "current site" URL as untrusted input** (it later feeds an
  automated fetch — preview build and/or §10 audit). Before any fetch: allow only
  `http`/`https` schemes; resolve the host and **reject loopback, link-local
  (169.254/16) and RFC-1918 ranges**; re-validate after every redirect; cap
  response size and timeout. This guard lives at the fetch boundary
  (`packages/tools/primitives/verification_loop_runner.py` and the prospect-site
  build) — see todo 065. Without it the form is an SSRF lever against the
  always-on Mac.
- Configure a **notification** (email/Slack) so submissions reach the operator.
  Notifications are configured **server-side in Netlify form settings only** — the
  webhook/email secret is never committed, never in `dist/`, never in client JS
  (the file-digest deploy uploads `dist/` wholesale — see todo 075).
- No automated *outbound-to-the-prospect* sending in v1; a submission enqueues an
  internal, **operator-gated** preview/audit (honesty boundary — reconciled with
  §10/§11 so "nothing auto-sends" is true of prospect-facing actions, not of
  internal fulfillment).

## 8. Deploy & launch gate — first-party path (review finding 4)

This is a **production** site (unlike previews), so it goes through the
`deploy_readiness` gate: **build → preview → operator approves → production**.
Custom domain / DNS is a separate approval gate; v1 can launch on the Netlify
subdomain and add a domain later.

**The existing `launch.py` checklist is written for client sites** — it failed
closed not only on `gbp_link`/`analytics_id` but also on `dns_approved`, which
unconditionally required DNS approval *even with no custom domain*. So the
"launch on the subdomain" path could never go green. **Resolved (implemented):**
`run_launch_checklist` now takes `first_party: bool = False`
([`packages/agency/launch.py`](../../../packages/agency/launch.py)) that records
`gbp_link`, `analytics` **and `dns_approved`** as passed-with-reason ("relaxed:
first-party …") — visible in the report, never silently dropped. The hard items
(`ux_audit`, `contact_form`, `seo_title`, `deploy_approved`) stay enforced; a
unit test covers first-party-ready-vs-client-fails. The agency site launches with
`first_party=True`.

**Reviewed-preview artifact under the no-build path:** §4 publishes via
file-digest upload, so there is no Netlify build-preview to review. The
`deploy_approved` gate's `preview_reviewed` is satisfied by the operator
reviewing either a Netlify **draft/branch deploy** URL or the locally rendered
`dist/` walkthrough before approving production. Name which in the runbook.

## 9. Review findings → resolution (traceability)

| # | Finding | Resolution |
|--:|---|---|
| 1 | Template lacks packages/portfolio sections | §5 — author two new testable partials |
| 2 | Astro build burns Netlify minutes | §4 — pre-render locally, file-digest upload, no Node build |
| 3 | Halving not done; mirror desync; OFFER re-quote | §2 — edit YAML, build mirror generator + drift test, note OFFER effect |
| 4 | `launch.py` gate assumes client (GBP/analytics) | §8 — first-party relaxation of gbp_link/analytics |
| 5 | Portfolio integration unspecified; ugly draft URLs | §6 — first-party `/work/<slug>` pages, no screenshots |
| 6 | Netlify Forms not wired; wrong stubs | §7 — data-netlify + honeypot + notification, test detection |
| 7 | Analytics choice; CTA fulfillment; a11y | §7/§5 — pick analytics; wire CTA to Stage-2 verification loop; focus/contrast on new cards |

## 10. Smaller / operational (review finding 7)

- **Analytics:** choose a script-tag analytics (e.g. Plausible or GA4) — avoids
  Node build; satisfies the (relaxed) launch checklist if `analytics_id` is set.
- **CTA fulfillment (delivers the hero promise).** The submission (captured as a
  typed record, §7) feeds two operator-triggered steps that consume the same
  record: **(a) generate a first-party preview of the requester's site via the
  prospect-site lane** — this is what "a real preview link first" (§1) actually
  delivers; and **(b) a Stage-2 live website audit** (the existing verification
  workflow) as enrichment. Both run behind an explicit operator gate with a daily
  cap (todo 074), so the CTA isn't a dead end and isn't an abuse/denial-of-wallet
  lever. Manual trigger for v1; automatable later because the input is typed.
- **A11y/perf:** the scaffold is fluid + reduced-motion aware; carry the same
  care into the new sections (keyboard focus, color contrast on themed cards).

## 11. Guardrails (carried from the wedge brief)

- No real prospect business appears on the page (all demos fictional, labeled
  "concept demo").
- Demos never implied as live client work.
- Problem copy stays constructive — never "your business is failing."
- Nothing auto-sends **to the prospect**: a submission triggers no outbound
  contact. It captures a typed inbound record (§7) and enqueues an internal,
  **operator-gated** preview/audit (§10) — no prospect-facing action happens
  without the operator.

## 12. Sequencing

1. **Halve `catalog.yaml`** + build the mirror generator (`render_service_catalog`
   + `scripts/agency/render_catalog_md.py`) + drift test; regenerate the mirror.
2. **Author the two new partials** (`render_packages_section`,
   `render_portfolio_section`) with render guards + unit tests.
3. **Repoint `build_portfolio_demos.py`** to emit `/work/<slug>` pages into the
   site `dist` (first-party), and link them from the portfolio grid.
4. **Wire Netlify Forms** (data-netlify + honeypot + notification); test-deploy to
   confirm form detection with file-digest upload.
5. **Relax the launch gate** for first-party (gbp/analytics optional).
6. **Build the page `dist` locally**, then **build → preview → approve →
   production** (subdomain first; custom domain later via DNS gate).
