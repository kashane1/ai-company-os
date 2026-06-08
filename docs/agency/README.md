# Agency / Web lane — map & entry point

The **WaaS (Website-as-a-Service) agency lane**: find local small businesses
without good websites, build a genuinely good demo site for each, reach out, and
on a sale, scaffold + launch their real site and run monthly retainer ops.

This is the doc the orientation spine (REPO_MAP → preflight) points to for any
prospecting / demo-site / client-site / retainer work. Start here, then jump to
the stage doc you need.

## Pipeline at a glance

| Stage | What happens | Lead doc | Key code |
|---|---|---|---|
| 1–4 Prospect & qualify | discover businesses, enrich contacts, verify "no real site" | [waas-prospecting-lane.md](../waas-prospecting-lane.md) | `scripts/agency/gather_place.py`, `packages/agency/prospect_site.py` |
| 5 Demo build | hand-build a bespoke mockup per business → `dist-v2/` | [demo-site-build-playbook.md](../demo-site-build-playbook.md) · [demo-site-gather-automation.md](../demo-site-gather-automation.md) | `state/prospects/sites/<place_id>/`, `scripts/agency/build_prospect_site.py` |
| — Portfolio | curate anonymized demos onto the BBW landing page | (this doc, below) | `scripts/agency/build_portfolio_demos.py`, `products/better-business-web/` |
| Outreach | channel × genre templates, send, track replies | [waas-prospecting-lane.md](../waas-prospecting-lane.md) (stages 6–8) | `packages/agency/outreach.py`, `scripts/agency/build_outreach.py` |
| 3–6 Sale → client | promote prospect → intake → scaffold → launch → SEO | [agency/client-lifecycle.md](client-lifecycle.md) · [agency/go-live-checklist.md](go-live-checklist.md) | `packages/agency/client_lifecycle.py`, `intake.py`, `launch.py`, `local_seo.py` |
| Domain & hosting (bring-your-own-domain) | point the client's own domain at the Netlify site **without breaking their email**: recon → DNS instructions → gated attach → verify | [agency/domain-dns-runbook.md](domain-dns-runbook.md) | `packages/agency/domain_recon.py`, `domain_verify.py`, `domain_attach.py`; `scripts/agency/{domain_recon,verify_domain,attach_domain}.py` |
| Retainer ops | monthly report, ads, GBP, email, billing, follow-up, CRM | [agency/operator-ads-playbook.md](operator-ads-playbook.md) | `packages/agency/retainer_ops.py`, `retainer_executor.py`, `monthly_report.py`, `billing.py`, `follow_up.py`, `crm_setup.py` |
| Lead monitoring (own funnel + lead-capture clients) | drain the agency funnel + each lead-form client → flag leads captured but never emailed; form-less sites skipped | (this doc) | `scripts/web/pull-leads.mjs` → `scripts/agency/check_all_lead_health.py` (`packages/agency/lead_health.py`); scheduled by `infra/launchd/com.ai-company-os.lead-health.plist` |

Lessons learned from real runs: [demo-site-learnings.md](../demo-site-learnings.md).
Service/genre definitions: [agency/service-catalog.md](service-catalog.md).

## The three web build paths (important — they are NOT interchangeable)

This is the distinction that's easy to get wrong. Only the latter two are live.

| Path | Builds | Status | How | Lives in |
|---|---|---|---|---|
| **A. Legacy token-fill** | `dist/` | **Deprecated** for prospects (kept for `--legacy-build` bulk + some portfolio) | `packages/agency/demo_theme.py` + `render_landing_html()` + `apply_theme()` | `state/prospects/sites/<place_id>/dist/` |
| **B. Bespoke playbook** | `dist-v2/` | **Live** — the demos sent to prospects | Hand-built per business via the playbook checklists; **no code generator** | `state/prospects/sites/<place_id>/dist-v2/` |
| **C. Astro scaffold** | `products/<slug>-site/dist/` | **Live** — paid client sites | `packages/web/scaffold.py` (`scaffold_site`) → Astro project, `npm run build` | `products/<slug>-site/` |

`resolve_prospect_dist_dir()` (`packages/agency/prospect_site.py`) refuses to fall
back to `dist/` — it requires `dist-v2/`. If you're improving demo design, edit the
**playbook checklists** (path B) and/or the **design reference** (below), not
`demo_theme.py`.

## Prospect data layout — `state/prospects/`

`state/` is runtime-owned and **gitignored** (this map is the tracked source of truth
for its shape). Per-business data hubs:

| Path | What it holds |
|---|---|
| `records/<place_id>.json` | The warehouse record per business: name, address, phone, rating, genre, web-status, verification fields, `mockup_url` |
| `sites/<place_id>/source/` | Gathered raw inputs: `place-details.json`, downloaded `photos/`, content brief |
| `sites/<place_id>/dist-v2/` | The **bespoke built mockup** (path B) — `index.html` + inlined CSS + real photos |
| `sites/_scaffold/` | The bespoke-build **checklists** (gather → brief → design-direction → QA → craft-pass) — see [demo-site-build-playbook.md](../demo-site-build-playbook.md) |
| `review-gallery/` | Full-page PNG contact sheets for reviewing mockups before deploy |
| `outreach/` | Outreach template library by channel × genre |
| `records/`, `batch/`, `contacted/`, `inbound/`, `runs/` | Warehouse, fan-out batch specs, outreach state, inbound replies, run logs |

## Portfolio demos (the BBW landing page)

The agency's own marketing site curates a few anonymized demos as proof of work.

- `products/better-business-web/` — the agency funnel site (`site/` is the Astro source)
- `products/better-business-web/portfolio/curated.json` — registry: one curated demo
  per genre (auto_repair, bakery, barber_shop, …), each mapping a real `place_id` to an
  anonymized `portfolio_name`/address/phone
- `scripts/agency/build_portfolio_demos.py` — copies each business's `dist-v2/`,
  **anonymizes** it (real name → portfolio name), publishes to `site/public/work/<slug>/`,
  and writes thumbnails + full-page PNGs to `docs/products/better-business-web/screenshots/`
- See [products/better-business-web/portfolio/README.md](../../products/better-business-web/portfolio/README.md)

## Design reference (shared design intelligence)

Curated, MIT-licensed palettes / font pairings / UX rules + a palette module, used by
both the bespoke playbook (path B, as fallback guidance) and the Astro scaffold (path C):

- `packages/web/design_reference/` — `palettes.md`, `font_pairings.md`, `ux_rules.md`
  (+ `LICENSE`, `ATTRIBUTION.md`). See [packages/web/README.md](../../packages/web/README.md).
- `packages/web/palette.py` — WCAG contrast primitives, a genre→palette table
  (`GENRE_PALETTES`), and a deterministic HSL synthesizer (`derive_palette`).
- The web gate `check_contrast` (`packages/web/validation.py`) enforces AA on built sites.

> **Palette precedence for demos:** derive from the business's own visual cues first
> (storefront, signage, logo, photos). The reference is fallback/enrichment, never an override.

## Code index

- **`packages/agency/`** — lane business logic. The **authoritative, per-module
  list** lives in [packages/agency/README.md](../../packages/agency/README.md)
  (kept in sync with the source); start there rather than duplicating it here.
- **`packages/web/`** — site machinery: `scaffold`, `validation`, `build`, `deploy`
  (incl. custom-domain attach + SSL), `ux_audit`, `palette`, `stripe_monetization`
  + `design_reference/` + `scaffold/`. See [packages/web/README.md](../../packages/web/README.md).
- **`scripts/agency/`** — runnable entrypoints, e.g. `gather_place`,
  `build_prospect_site`, `build_portfolio_demos`, `client_intake`, `launch_client`,
  `build_outreach`, `preview_site`, `screenshot_demo`, `retheme_sites`,
  `inject_booking`, plus domain onboarding (`domain_recon`, `verify_domain`,
  `attach_domain`). Full index: [scripts/agency/README.md](../../scripts/agency/README.md).
- **`scripts/web/`** — `shoot.mjs` (Playwright full-page screenshots),
  `pull-inbound.mjs` / `pull-orders.mjs` / `pull-leads.mjs` (Netlify Blobs drains:
  reviews, self-serve orders, and per-client contact-form leads) — see
  [scripts/web/README.md](../../scripts/web/README.md).

## Skills (canonical + claude adapters)

`landing-page-build`, `web-ux-audit`, `client-intake` (Phase 4), `launch-checklist`
(Phase 5), `local-seo-pages` (Phase 6). Trigger phrases in
[docs/skills-index.md](../skills-index.md).
