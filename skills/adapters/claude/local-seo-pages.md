# Adapter (claude): Local SEO Pages

Implements `skills/canonical/local-seo-pages/skill.md` for the Claude runtime.

1. **Generate:** `packages.agency.local_seo.generate_matrix(business_name,
   services, cities, differentiators=[...])`. Each page carries unique metadata
   and a non-thin body.
2. **Guard:** the generator raises `ThinContentError` on thin or duplicate pages —
   fix the inputs, never bypass it.
3. **Render + audit:** materialize pages into the site, then
   `packages.web.ux_audit.audit_dist(dist)` before publish.
4. **Never deploy from here** — publishing is the gated `webdeploy` lane.
