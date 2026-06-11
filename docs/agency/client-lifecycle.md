# Client lifecycle (Phases 3–5)

Operator guide for turning a **human-verified prospect** into a **live client site**.
Code lives under `packages/agency/`; skills: `client-intake`, `launch-checklist`.

> This doc zooms into Phases 3–5 (promotion → intake → launch). For the **full
> funnel** — collect → verify → contact → demo → outreach → sell → onboard → recurring
> — see [prospect-to-client-pipeline.md](prospect-to-client-pipeline.md).

## Overview

```text
Phase 3  promote_prospect     →  registry + docs stubs + engagement onboarded
Phase 4  client_intake        →  CLIENT_BRIEF + products/<slug>-site/ scaffold
         npm run build        →  dist/  (operator / Codex)
Phase 5  launch_client        →  checklist + phase: live
         webdeploy (gated)      →  production URL + custom domain
```

Prospect **preview mockups** (playbook `dist-v2/`) are separate — see
`docs/demo-site-build-playbook.md` and `scripts/agency/build_prospect_site.py`.

## Phase 3 — Promote to client

**Gate:** prospect `human_verified=true` and explicit operator approval.

```bash
python scripts/promote_prospect.py list-verified
python scripts/promote_prospect.py promote \
  --place-id <PLACE_ID> \
  --bundle package_a \
  --approved-by kashane
```

**Creates:**

- `infra/products.json` record (`type: client-site`, `phase: discovery`)
- `docs/products/<slug>-site/` workspace (`OFFER.md`, stubs, `reports/`,
  `COMPLIANCE.md`, `compliance/review-sms-consent-addendum.md`)
- Sets prospect `engagement_status` → `onboarded`

**Bundles:** `package_a` | `package_b` | `package_c` (see `packages/agency/catalog.yaml`).

## Phase 4 — Intake + site scaffold

Fill business details and materialize the paid Astro project.

```bash
# Seed intake from the warehouse record:
python scripts/agency/client_intake.py \
  --product-id joes-plumbing-site \
  --from-prospect <PLACE_ID>

# Or explicit fields:
python scripts/agency/client_intake.py \
  --product-id joes-plumbing-site \
  --business "Joe's Plumbing" \
  --category plumbing \
  --city "Seattle, WA" \
  --phone 206-555-0100 \
  --service "Drain cleaning"
```

Then build (requires Node):

```bash
cd products/<slug>-site
npm install && npm run build
```

**Outputs:**

- `docs/products/<slug>-site/CLIENT_BRIEF.md` (from intake)
- `products/<slug>-site/` — Astro scaffold from `packages/web/scaffold.py`

## Phase 5 — Launch checklist

Fail-closed gate before marking the engagement **live**. Inject the client's GBP
link and analytics tag into the built HTML before running the checklist.

```bash
python scripts/agency/launch_client.py check \
  --product-id joes-plumbing-site \
  --dist products/joes-plumbing-site/dist \
  --gbp-url 'https://maps.google.com/?cid=...' \
  --analytics-id plausible-joes-plumbing \
  --deploy-approved \
  --dns-approved

python scripts/agency/launch_client.py mark-live \
  ...same flags...
```

**Checks:** UX audit (responsive/a11y/perf/SEO), contact form, title, GBP link,
analytics, deploy + DNS approvals.

**Production deploy** remains the separate, gated `webdeploy` lane — this step
does not publish the site.

## Engagement status (operator-set)

| Status | Meaning |
|--------|---------|
| `none` | Default |
| `contacted` | Outreach sent |
| `replied` | Owner responded |
| `proposal_sent` | Offer sent |
| `won` | Accepted |
| `onboarded` | Set automatically on promotion |
| `lost` | Dead lead |

No automated transitions — update manually on the warehouse record until Phase 8.

## API surface (for skills/scripts)

| Callable | Module |
|----------|--------|
| `promote_prospect_to_client` | `packages.agency.promotion` |
| `intake_from_prospect` / `apply_client_intake` / `scaffold_client_product` | `packages.agency.client_lifecycle` |
| `run_launch_checklist` / `mark_client_live` | `packages.agency.launch` / `client_lifecycle` |
| `load_product_configs` | `packages.config.products` |

## After launch (Phases 6–8)

Recurring retainer work — local SEO, monthly reports, GBP, booking, reviews, promo
pages, Stripe billing, Package C ads (draft + approve) — is specified in
[`docs/plans/2026-06-03-feat-agency-retainer-ops-phases-6-8-plan.md`](../plans/2026-06-03-feat-agency-retainer-ops-phases-6-8-plan.md).
Compliance templates: [`docs/agency/compliance/`](compliance/).

## Tests

```bash
python -m pytest tests/python/unit/test_agency_promotion.py \
  tests/python/unit/test_client_intake_scaffold.py \
  tests/python/unit/test_client_lifecycle.py \
  tests/python/unit/test_agency_launch_checklist.py \
  tests/python/unit/test_product_registry_client.py -q
```
