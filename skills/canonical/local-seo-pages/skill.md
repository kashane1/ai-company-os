# Local SEO Pages

**Kind:** agentic · **Owner:** web · **Runtimes:** claude, codex

Generate a differentiated set of locally-targeted pages from a service x geo
matrix for a client site (Agency layer, Phase 6). The highest-AI-leverage
recurring service — dozens of quality local pages in minutes.

## When to use

- A client on a local-SEO retainer needs city/service/location pages
  (e.g. "Roof Repair Dallas", "Emergency Roof Repair Dallas").
- The operator says "generate local SEO pages", "build the service area pages",
  "build the service x geo matrix".

## Inputs

- The client's services and target cities (from `LOCAL_SEO.md`).
- Optional differentiators (licensed, 24/7, family-owned, …).

## Procedure

1. **Generate the matrix** —
   `packages.agency.local_seo.generate_matrix(business_name, services, cities,
   differentiators=[...])`. Each page gets a unique title, slug, meta
   description, `<h1>`, and a non-thin body.
2. **Thin-content guard.** The generator rejects thin pages (below the minimum
   word count) and duplicate slugs/titles — do not bypass it.
3. **Render + audit.** Materialize each page into the site and run
   `packages.web.ux_audit.audit_dist(dist)` before publish.
4. **Stop before deploy.** Publishing remains the gated `webdeploy` lane.

## Outputs

- A list of `SeoPage` records (slug / title / meta / h1 / body).

## Forbidden areas

- Does not deploy. Does not produce thin or near-duplicate pages.
