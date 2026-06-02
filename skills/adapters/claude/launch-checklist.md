# Adapter (claude): Launch Checklist

Implements `skills/canonical/launch-checklist/skill.md` for the Claude runtime.

1. **Audit:** `packages.web.ux_audit.audit_dist(dist)` → require `.passed`.
2. **Checklist:** `packages.agency.launch.run_launch_checklist(dist, gbp_url=...,
   analytics_id=..., deploy_approved=..., dns_approved=...)`.
3. **Gate:** mark the site live only when `report.ready` is true. Inspect
   `report.failures()` for any blocking item.
4. **Never deploy from here** — routing to the `webdeploy` lane is separate and
   approval-gated.
