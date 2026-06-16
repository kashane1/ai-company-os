# scripts/agency — runnable entrypoints (WaaS lane)

CLI entrypoints for the Website-as-a-Service agency lane. Business logic lives in
[`packages/agency/`](../../packages/agency/README.md); site machinery in
[`packages/web/`](../../packages/web/README.md). For the lane map and pipeline
stages start at [docs/agency/README.md](../../docs/agency/README.md).

Most scripts print a JSON/Markdown result and exit non-zero on failure. Outward or
irreversible actions (deploys, custom-domain changes, ad go-live, charging) are
**approval-gated** in `packages/policies/` — these CLIs surface the gate, they
don't bypass it.

## Prospecting & demo build (paths A/B)

| Script | Purpose |
|---|---|
| `gather_place.py` | Rich Place Details gather for a demo-site build (Checkpoint A). |
| `build_prospect_site.py` | Deploy bespoke prospect preview sites (`dist-v2`) to Netlify. |
| `redeploy_existing_sites.py` | Redeploy the current themed build onto already-existing prospect sites. |
| `retheme_sites.py` | Re-generate legacy token-fill `dist/` previews (**deprecated**, path A). |
| `preview_site.py` | Serve a demo site's build locally to preview + iterate before deploying. |
| `screenshot_demo.py` | Full-page screenshot of a demo build — the mandatory pre-Netlify review step. |
| `build_outreach.py` | Generate per-prospect outreach copy for every lead with a live preview site. |
| `build_teardown_teaser.py` | Owned-site flip (item 7): `prepare` captures a prospect's live homepage + writes Conversion Lab prompts; fill `teaser/reviews.json` + `teaser/findings.json`; `finish` validates findings and renders `teaser.md` + annotated card + a `variant=teaser` audit-pitch draft. |
| `outreach_lane.py` | Refresh/list/log the human-gated outreach client-status ledger. |
| `gen_gunstore_images.py` | Generate imagery for the Blue Ridge Gun & Ammo portfolio demo via Gemini. |

## Premium design engine (opt-in, design engine v3)

The autonomous **build → judge → revise** loop for select premium builds. Core
machinery lives in [`packages/web/`](../../packages/web/README.md)
(`design_loop.py`, `premium_build.py`, `gemini_judge.py`); these CLIs are the
operator-facing entrypoints. Contract + gates: [docs/agency/design-studio-lane.md](../../docs/agency/design-studio-lane.md).

| Script | Purpose |
|---|---|
| `design_loop.py` | Quality-loop CLI: `run` (build→judge→revise until the visual bar is met), `judge` (score screenshots with Gemini), `calibrate` (halt on judge drift). |
| `design_studio.py` | Premium-track plumbing for one chosen build: `packet` (art-direction packet), `shoot` (desktop/mobile screenshots), `review` (ingest rubric scores → visual-review report), `status`. |

## Portfolio & the BBW agency site

| Script | Purpose |
|---|---|
| `build_portfolio_demos.py` | Build portfolio demos for the Better Business Web landing page (anonymized). |
| `render_catalog_json.py` | Emit the BBW Astro site's `src/data/packages.json` from the catalog. |
| `render_catalog_md.py` | Regenerate `docs/agency/service-catalog.md` from `packages/agency/catalog.yaml`. |
| `verify_landing_inbound.py` | Verify BBW landing form + inbound pipeline contracts (offline). |

## Sale → client (Phases 4–6)

| Script | Purpose |
|---|---|
| `client_intake.py` | Phase 4 — apply client intake and scaffold the paid client Astro project. |
| `launch_client.py` | Phase 5 — run the client launch checklist and mark the engagement live. |
| `run_local_seo.py` | Phase 6 — generate approved local SEO pages for a client Astro site. |

## Domain & hosting (bring-your-own-domain)

| Script | Purpose |
|---|---|
| `domain_recon.py` | Readiness recon — read a client's public DNS + registration state (RDAP + DoH). |
| `attach_domain.py` | Attach a client's own domain to their Netlify site (www-primary + apex-alias), gated. |
| `verify_domain.py` | Verify a domain points at Netlify **without breaking the client's email**. |
| `setup_business_email.py` | Emit the business-email (Google Workspace) runbook — G5. |
| `inject_booking.py` | Inject a booking provider's embed into a client site file (idempotent) — G6. |
| `inject_ordering.py` | Inject a POS "Order Online" button (Square/Clover; Toast gated) into a client site file (idempotent). |

## Retainer ops & growth drafts

| Script | Purpose |
|---|---|
| `run_retainer.py` | Plan a monthly retainer run for a client site. |
| `run_monthly_report.py` | Render a draft monthly report for a client site. |
| `draft_gbp_changeset.py` | Draft a `GBP_CHANGESET.md` from client intake — G7. |
| `draft_google_ads.py` | Draft a Google Ads campaign (`ADS.md`) from client intake — G8. |
| `draft_meta_ads.py` | Draft a Meta (Facebook/Instagram) Ads campaign from client intake. |
| `generate_ad_creative.py` | Generate ad creative — real client photos first, AI (Gemini) fallback. |
| `build_promo_page.py` | Build a single-offer promotional landing page — G4. |
| `list_retainer_approvals.py` | List pending retainer approvals grouped by client product. |

## Lead-pipeline health (hosting SLA)

| Script | Purpose |
|---|---|
| `check_lead_health.py` | Check one client site's contact-form lead pipeline (the `hosting` SLA). |
| `check_all_lead_health.py` | Lead-pipeline health across the agency's own funnel + every form-having client. |

## Money & the transaction loop

| Script | Purpose |
|---|---|
| `create_checkout.py` | Create a Stripe Checkout link for a bundle OR a custom service set — G1. |
| `process_inbound_review.py` | Audit + (optionally) build a preview for one captured inbound lead — G2b. |
| `process_inbound_order.py` | Promote one pulled self-serve order into a client-site registry record. |
| `reconcile_stripe_billing.py` | Apply verified Stripe billing events to the local agency ledger. |
| `stripe_bootstrap.py` | Idempotently create Stripe Products + Prices for every bundle; emit `STRIPE_PRICE_MAP`. |
| `verify_inbound_fulfillment.py` | Offline verification for the G2 lead-activation slice. |

## Maps / utilities

| Script | Purpose |
|---|---|
| `smoke_test_maps_key.py` | Smoke-test the live `GOOGLE_MAPS_DEMO_API_KEY` against Google's Maps APIs. |

> Keep this index in sync when adding a script. The `scripts/web/` Node drains
> (`pull-inbound`/`pull-orders`/`pull-leads`, `shoot.mjs`) are documented in
> [scripts/web/README.md](../web/README.md).
