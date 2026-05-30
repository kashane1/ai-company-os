# Adapter (claude): Web UX Audit

Implements `skills/canonical/web-ux-audit/skill.md` for the Claude runtime.

1. Build the site to `dist/` (or use the existing build).
2. `from packages.web.ux_audit import audit_dist` → `report = audit_dist(dist_dir)`.
3. Inspect `report.scores` and `report.categories[*].findings`. Fix every
   `error` finding, then `warn`, editing the site source (re-skin via `--brand`
   and the design system's fluid units rather than fixed widths).
4. Re-run `audit_dist` until `report.passed` is true (every category ≥ threshold).
5. Stop at the gate — deployment is the separate, approval-gated `webdeploy` lane.
