# Build the agency's own funnel/landing page on Netlify

**Status:** pending · **Priority:** p3 (future, operator-requested)

## Context

The WaaS agency now has a working **prospect → preview-site → Netlify draft
deploy** path (`packages/agency/prospect_site.py` +
`scripts/agency/build_prospect_site.py`, see `docs/waas-prospecting-lane.md`
Stage 5). Those are the *client demo* sites.

Separately, the operator wants the agency's **own** funnel/landing page — the
public page that explains the "no-website rescue" offer and captures inbound
leads — also hosted on Netlify (the operator's account). This is the
"validation asset" the wedge brief calls for ("one landing page explaining the
no-website rescue offer").

## Scope (when picked up)

- Reuse the existing Astro scaffold (`packages/web/scaffold/astro-landing`) and
  the `default_context` / agency copy — this is a *product* landing page, not a
  per-client site, so it likely warrants its own client-workspace under
  `docs/products/<agency-funnel>-site/` per the template convention.
- Wire the CTA form to a real handler (Netlify Forms or Stripe Checkout — the
  scaffold already stubs `netlify/functions/`).
- Deploy to **production** on the operator's Netlify account — this crosses the
  `deploy_readiness` production gate (validated build + reviewed preview +
  granted approval) and, if a custom domain is used, the DNS approval gate.
- Pull offer copy/pricing from `packages/agency/catalog.yaml` so terms don't
  drift.

## Not now

Deferred by the operator ("a task for another day"). Logged so it isn't lost.
No work should start until explicitly picked up.
