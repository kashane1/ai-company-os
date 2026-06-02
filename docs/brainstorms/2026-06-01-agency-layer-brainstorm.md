# Brainstorm: Local-SMB Agency Layer

**Date:** 2026-06-01
**Status:** Draft for review
**Lane:** Web / Prospecting / GTM (cross-lane)
**Next step:** `/workflows:plan` — turn the build order below into a phased plan under `docs/plans/`

## What we're building

A new angle for `ai-company-os`: turn the platform into an **internal operating
system for a local-SMB agency**. The long-term goal is not "I sell websites." It
is **"we operate the digital presence for local businesses."** Once it's framed
that way, the website is only the *first* product in a much larger service stack,
and the recurring services above it are where the real money lives.

The website is the entry product and the trust anchor. After we become a
business owner's "tech person," we move up a value ladder of increasingly
valuable services — hosting, Google Business, booking, reviews, local SEO,
reporting, ads, automation — and eventually become their de-facto fractional
CTO. Codex builds and maintains the assets, skills encode the repeatable
workflows, and we sell simple monthly *outcomes* (more calls, more bookings,
more revenue) to plumbers, med spas, barbers, gyms, landscapers, tutors,
dentists, roofers, etc.

## The core thesis: the website is the lowest-value thing they buy

A business owner thinks they need a website. What they actually want is more
customers, more bookings, more phone calls, more revenue. The website is just
one tool. So the value ladder inverts the usual mental model:

- **One-time builds** (website, booking setup, email setup) are the *cheapest*
  things we sell and the easiest to commoditize. Thousands of people can build a
  website.
- **Recurring management** (hosting, reviews, local SEO, reporting, ads,
  automation) is where margin and defensibility live. These are retainers.
- **Fractional CTO** work (internal tools, integrations, AI automation, vendor
  selection) often pays more than everything below it combined.

Our edge is not "we can build websites." It's **AI leverage**: a traditional
agency needs 20–40 hours to launch and optimize a local business; we should be
able to do much of that in 2–6 hours, then operate it cheaply month over month.
That's the whole bet — see "The AI-leverage angle" below.

## The reframe (most of the website lane already exists)

The website piece is the most-built part of the stack today — three of the five
"obvious" website deliverables are already shipped. The honest gap is not "build
a site factory"; it's the **client lifecycle layer** plus the **services above
the website**.

| Website-lane deliverable | Reality in the repo today |
|---|---|
| Static site factory | **Shipped.** `packages/web/scaffold.py` materializes an Astro static-first landing site from `packages/web/scaffold/astro-landing/`; `landing-page-build` skill drives it (commit `c2cfd85`). |
| QA / audit | **Shipped.** `packages/web/ux_audit.py` + `web-ux-audit` skill score responsive evidence, heading order, labeled inputs, page weight, title/description/OG (commit `c755511`). |
| Monetization / lead validation | **Shipped.** `packages/web/stripe_monetization.py` + Netlify deploy with DNS/spend approval gates (commits `8b8e02d`, `bcfcd31`, `6304eca`). |
| Deploy / hosting | **Shipped.** `DeployTarget` seam + Netlify adapter + `webdeploy` worker, gated on `DEPLOY_DNS_NOT_APPROVED` / `DEPLOY_SPEND_NOT_APPROVED`. |
| Client discovery | **Shipped, aimed exactly here.** The prospecting pipeline (Phase 1–2) scans local SMBs via Google Places, classifies who has *no owned website*, cohorts them (`A_gold`, `A2_marketplace_review`, `B_stale_maps`…), and supports manual `human_verified` spot-checking. See `docs/founder/prospecting-phase1.md`, `prospecting-phase2.md`. |

**What is missing is (a) the client lifecycle seam that turns a verified prospect
into a paying retainer client, and (b) the rest of the service stack above the
website.** That's the work this brainstorm scopes.

## The full service stack, mapped to the architecture

Each service below is tagged with: **bill** (one-time vs recurring), **repo
mapping** (reuse existing lane / new skill / external integration), and the
**AI-leverage** note (where our time advantage comes from). The pattern that
matters: lower tiers are mostly *content + config* (high AI leverage, our
scaffold/audit lanes already exist); higher tiers are mostly *integrations +
ad/automation accounts* (these need connectors/MCPs and stronger approval gates,
not source code).

### Tier 1 — easy add-ons (offer immediately)

| Service | Bill | Repo mapping | AI leverage |
|---|---|---|---|
| **Google Business Profile** cleanup (claim, hours, services, photos, categories, descriptions, booking links) | $250–500 setup, or bundle | New `gbp-optimize` skill; needs a Google Business Profile connector + operator approval to edit a live profile. | AI drafts categories/descriptions/services from the intake; operator approves. |
| **Hosting & maintenance** (hosting, SSL, backups, content updates, broken-link fixes, form monitoring) | $49–149/mo | **Reuse** the web/webdeploy lane. Add a recurring maintenance checklist + uptime/broken-link checks (extend `web-ux-audit`). | Automated link/uptime/form checks; AI drafts content updates. |
| **Business email** (info@ / support@ / sales@, Google Workspace) | $150–300 setup | New `business-email-setup` skill; mostly a guided/operator-run procedure + Workspace connector. | Low — checklist automation only. Mostly trust/convenience value. |
| **Contact forms & lead routing** (form → email → SMS → CRM) | bundle / setup | Extend the scaffold's form to fan out via webhook → email + SMS (Twilio) + CRM. | AI configures routing + drafts auto-responses. |

### Tier 2 — high value (where retainers start)

| Service | Bill | Repo mapping | AI leverage |
|---|---|---|---|
| **Online booking** (Calendly / Square / Vagaro / Acuity / Mindbody) | $300–1,000 setup | New `booking-setup` skill; integration/config against the chosen booking provider. A few hours of work for high perceived value. | AI maps services → bookable offerings, drafts confirmations. |
| **Local SEO** (city / service / location / FAQ pages — e.g. "Roof Repair Dallas", "Emergency Roof Repair Dallas") | **retainer** | **Reuse + extend** `landing-page-build` to mass-generate templated, locally-targeted pages from a service × geo matrix. This is the highest-leverage AI service. | Huge — generate dozens of high-quality, differentiated local pages in minutes. |
| **Review generation** (served customer → SMS → review request → Google review) | **retainer** | New `review-system` skill; SMS provider (Twilio) + GBP review link + scheduling. | AI personalizes request copy and timing. |
| **Analytics dashboard** (owner-friendly: *phone calls: 27, form submissions: 14, bookings: 8* — not sessions/bounce rate) | **retainer** | **Reuse** the report-generator pattern; surface as a live artifact the owner can re-open. Blocked on the analytics-source decision. | AI writes the plain-English "what changed and what to do next." |

### Tier 3 — recurring-revenue goldmine (often worth more than the website)

| Service | Bill | Repo mapping | AI leverage |
|---|---|---|---|
| **Google Ads** management | $500–2,000/mo | New lane; Google Ads connector + **spend approval gates**. Entire agencies are built on this alone. | AI drafts ad copy, keyword sets, negative lists; human owns spend. |
| **Meta (FB/IG) Ads** (med spas, gyms, dentists, restaurants, realtors) | $500–2,000/mo | Same as above with the Meta API. | AI drafts creative variants + audiences. |
| **Promo landing pages** (owner says "summer promotion" → `summer.company.com` in 30 min) | $250–500 each | **Reuse** `landing-page-build` directly — this is the existing scaffold's sweet spot. | Very high — minutes per page. |
| **CRM setup** (HubSpot / GoHighLevel / Zoho / Pipedrive) | setup + retainer | New integration work; positions us inside sales ops. | AI configures pipelines/fields from intake. |
| **Automated follow-up** (lead → auto text → auto email → 2-day reminder) | **retainer** | New `follow-up-automation` skill; SMS + email + scheduler. Underrated; big conversion lift. | AI writes sequences, branches, timing. |

### Tier 4 — "fractional CTO for small business"

At some point the owner stops seeing us as "website guy" and starts seeing us as
"technology guy." Requests become: *automate this spreadsheet, connect
QuickBooks, help with AI, build an internal tool, build a customer portal,
evaluate software vendors, set up a new computer system.* These are scoped
project engagements, not a productized skill — they pay far more than websites
and are the natural endgame of the relationship. In repo terms this is **bespoke
Codex engineering against a client engagement**, gated and quoted per project,
not a catalog SKU. Worth naming as a destination so the earlier tiers are built
to lead here (own the relationship, own the data, own the integrations).

## Productized packages → the service catalog

Don't sell a la carte first. Sell three bundles, then expand. These map directly
to the typed service catalog (below), and "avoid ads initially" stays the
default unless we deliberately choose to learn them.

- **Package A — presence:** Website + Hosting + Google Business + Business Email.
- **Package B — presence + capture:** Package A + Review system + Booking system.
- **Package C — presence + capture + growth:** Package B + Local SEO + Landing
  pages + Monthly reporting.

Because the recurring tiers are where margin lives, every package is a
*setup fee + monthly retainer*, not a one-time sale.

## Service catalog: typed config + policy, not just an OFFER.md

Put the catalog where the rest of the platform's contracts live — a typed schema
in `packages/schemas/` plus a config file — not only in markdown. The catalog
encodes both individual services *and* the A/B/C bundles, so the launch
checklist, monthly-report generator, and billing all read the same source of
truth for what a tier includes, its edit limits, hosting, ownership,
cancellation, and support.

```
packages/schemas/offer.py        # Service + OfferTier dataclasses:
                                 #   service_id, bill_type (one_time|recurring),
                                 #   setup_fee, monthly_fee, edit_limit, includes[],
                                 #   ownership, cancellation, support_sla
packages/agency/catalog.yaml     # services + bundles (package_a/b/c)
docs/agency/service-catalog.md   # human-readable render of the same data
```

A client's `OFFER.md` *renders* from `catalog.yaml` + the chosen bundle, so the
signed terms can never silently drift from the catalog.

## Architectural decision: extend the product model, don't fork a `clients/` tree

A client engagement *is* a managed product; forking a parallel `docs/clients/`
tree would duplicate the registry, scaffold, deploy, audit, and report plumbing.
Reuse the existing product convention instead.

- Add a `type` field to `infra/products.json`: client engagements get
  `"type": "client-site"` (the anchor asset) and grow a `services[]` list as they
  buy up the stack.
- Reuse the documented locations from `REPO_MAP.md`: source →
  `products/<client-slug>-site/`, artifacts → `docs/products/<client-slug>-site/`,
  runtime → `state/artifacts/<lane>/<run-id>/`.
- The **ownership distinction** is the one genuinely new field. Owned iOS
  products and client engagements differ in who owns the asset:

```jsonc
{
  "id": "joes-plumbing-site",
  "name": "Joe's Plumbing",
  "type": "client-site",
  "platform": "web",
  "source_path": "products/joes-plumbing-site",
  "docs_root": "docs/products/joes-plumbing-site",
  "phase": "onboarding",              // onboarding | building | live | offboarding
  "client": {
    "ownership": "client-owned",      // we operate, client owns the asset
    "bundle": "package_b",            // FK into the service catalog
    "services": ["website", "hosting", "gbp", "booking", "reviews"],
    "from_prospect": "<prospect-id>", // backlink into state/prospects/
    "billing_status": "active"        // trial | active | past_due | cancelled
  }
}
```

## The crown jewel: the prospect → client seam

Both ends already exist; nothing connects them. The prospecting warehouse
produces exactly the businesses this agency targets (no owned website, real
demand signal, already human-verified). The web lane can already build and ship a
site. **The seam is the highest-leverage thing to build.**

`packages/schemas/prospect.py` already has a `ProspectStatus` enum
(`raw → maps_enriched → http_enriched → error`) and a `human_verified` flag — the
lifecycle hook is sitting there. Proposed:

- Add an `engagement_status` track for the sales states deferred to Phase 3:
  `contacted → replied → proposal_sent → won → onboarded` (and `lost`).
- A `promote_prospect_to_client(prospect_id, bundle)` operation that asserts
  `human_verified = true`, writes a `type: client-site` record into
  `infra/products.json`, scaffolds `docs/products/<slug>-site/`, and backlinks
  `client.from_prospect`.

This preserves the strict Phase 1–2 compliance boundary: prospecting still does
not *send* outreach; promotion is an operator-initiated, approval-gated
transition.

## Client workspace convention

Split *business relationship* docs from *technical asset* docs, and let the
commercial terms render from the catalog. Under `docs/products/<client-slug>-site/`:

```
CLIENT_BRIEF.md       # intake: business type, services, location, ideal customer, hours, photos, reviews, competitors
OFFER.md              # the signed bundle + terms (renders from catalog)
SITE_MAP.md           # pages + structure
COPY.md               # page copy
LOCAL_SEO.md          # GBP, citations, target keywords, service × geo page matrix
BOOKING.md            # provider, services mapped to bookable offerings
REVIEWS.md            # request cadence, SMS templates, review link
MAINTENANCE_PLAN.md   # what the retainer covers, edit limits, SLA
LAUNCH_CHECKLIST.md   # domain, DNS, SSL, form, mobile test, SEO metadata, GBP link, analytics
reports/
  MONTHLY_REPORT-YYYY-MM.md
```

## Recurring retainer = scheduled tasks + report generator

The retainer is the business. Two existing capabilities make it cheap: a
**monthly report generator** (mirror the existing report patterns; owner-friendly
metrics — calls, form leads, bookings, edits done, recommended next action) and
**scheduled tasks** (a per-client monthly cron drafts the report and routes it to
the operator before it's sent). Surface the report as a **live artifact** the
owner can re-open between cycles.

**Dependency:** reporting needs a real analytics source — decide early between
privacy-light (Plausible/Umami) and GA4, plus form-submission capture and
optional call-tracking. The report generator and the Tier-2 analytics dashboard
are both blocked on this.

## Skills mapping (reuse before building)

| Workflow | Skill status |
|---|---|
| Build the site | **Reuse** `landing-page-build` (extend inputs to take intake + service-category theme). |
| QA before launch | **Reuse** `web-ux-audit` as the delivery/launch gate. |
| Local SEO pages | **Reuse + extend** `landing-page-build` for service × geo mass generation. |
| Promo landing pages | **Reuse** `landing-page-build` directly. |
| Client intake | **New** `client-intake`. |
| Promote prospect → client | **New** `prospect-to-client`. |
| Launch checklist | **New** `launch-checklist` (composes `web-ux-audit`). |
| Monthly report | **New** `monthly-report`. |
| GBP optimize | **New** `gbp-optimize` (+ connector). |
| Booking / reviews / follow-up / ads | **New**, mostly integration + approval-gated; build as demand proves out, not upfront. |

All new skills follow the canonical → adapter → `registry.yaml` → `.claude/skills/`
wiring (`skills/WIRING.md`). Per CLAUDE.md's binding disambiguation rule, new
agency trigger phrases must not collide with existing ones; ambiguous prompts ask
rather than guess.

## Approvals & compliance (load-bearing as we climb the stack)

The repo is approval-gated by design, and the higher tiers touch exactly the
irreversible/external actions that must be gated:

- Existing gates carry over: `DEPLOY_DNS_NOT_APPROVED`,
  `DEPLOY_SPEND_NOT_APPROVED`, `PAYMENTS_LIVE_NOT_APPROVED`,
  `DISCOVERY_OUTREACH_SPEND_UNAPPROVED`, `DISCOVERY_BULK_CRAWL_NOT_APPROVED`.
- New approval-worthy actions to add to `packages/policies/approvals.py`: sending
  a proposal, promoting a prospect to a billing client, deploying to a
  client-owned domain, **editing a client's live Google Business Profile**,
  **launching or adjusting ad spend** (Google/Meta), and **any action touching
  client financial systems** (QuickBooks) — read-only/categorize only, never move
  money, consistent with the platform's financial-action rule.
- New compliance regimes appear as we climb: **TCPA** (review-request and
  follow-up SMS), **CAN-SPAM** (email follow-up), platform **ToS** for Google
  Business / Google Ads / Meta. Outreach *sending* stays deferred (already Phase
  3) until these gates exist. The agency angle must not quietly cross the line the
  prospecting pipeline drew.

## The AI-leverage angle

This is the actual moat. Restated as a constraint the whole system should be
designed around: a traditional agency spends 20–40 hours to launch and optimize a
local business and is then expensive to operate per client. Our target is **2–6
hours to launch** and near-zero marginal cost to operate, because:

- **AI-assisted site + content generation** — scaffold + `landing-page-build` +
  copy generation from intake.
- **AI-assisted SEO pages** — service × geo matrix generated in minutes.
- **AI-assisted landing pages** — promo pages on demand.
- **AI-assisted reporting** — plain-English monthly reports, scheduled.
- **AI-assisted automations** — follow-up sequences, review requests, routing.

Every service in the stack should be evaluated by *how much of it AI can do*. The
high-leverage services (local SEO pages, landing pages, reporting, content) are
where we lead; the integration-heavy services (booking, CRM, ads) are where AI
assists but a human owns the account and the spend.

## Revised build order

Re-sequenced around what's shipped and what unblocks the most:

1. **Service catalog as typed config** — `packages/schemas/offer.py` +
   `catalog.yaml` (services + A/B/C bundles) + `docs/agency/service-catalog.md`.
   Smallest, unblocks everything downstream.
2. **Client model in the registry** — add `type: client-site` + `client {}` block
   to `infra/products.json` and the product tooling.
3. **Prospect → client promotion** — extend engagement states +
   `promote_prospect_to_client`, behind an approval gate. Connects the two
   existing halves; highest leverage.
4. **Client intake + scaffold** — `client-intake` feeding an extended
   `landing-page-build`. Delivers Package A's website.
5. **Launch checklist** — `launch-checklist` composing `web-ux-audit`.
6. **Local SEO page generator** — extend `landing-page-build` for service × geo.
   First high-margin recurring service; pure AI leverage.
7. **Monthly report generator** — `monthly-report` + per-client scheduled task.
   Blocked on the analytics-source decision.
8. **Then, demand-driven:** GBP, booking, reviews, follow-up, ads — built as
   clients buy up the stack, each behind its own connector + approval gate. Avoid
   ads until we choose to learn them.

## Open questions / decisions needed

- **Analytics source** (blocks steps 6–7 and the Tier-2 dashboard):
  Plausible/Umami vs GA4; how form leads and calls are captured.
- **Billing system of record**: does Stripe (already wired for monetization
  experiments) become the retainer biller, or stay a proof-of-concept?
- **SMS/email provider** for reviews + follow-up (Twilio?), and the TCPA/CAN-SPAM
  consent model before any message sends.
- **Domain & DNS ownership model**: client-owned registrar we manage vs we hold
  it — affects offboarding and `ownership` semantics.
- **Offboarding / cancellation**: what happens to a `client-owned` asset when a
  retainer cancels — export, freeze, or hand over? Define before the first paying
  client.
- **How far up Tier 4 to go**: fractional-CTO work is lucrative but bespoke and
  hard to systematize — decide whether it's an explicit offering or an
  opportunistic upsell.
- **Geographic scope**: prospecting is Seattle-only today; national scale-out is
  still deferred Phase 3 in the pipeline.
