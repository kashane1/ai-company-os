# Launch Checklist

**Kind:** agentic · **Owner:** web · **Runtimes:** claude, codex

Run a repeatable, fail-closed pre-launch gate on a client site before it goes
live. The delivery checkpoint of the agency flow (Agency layer, Phase 5).

## When to use

- A client site has been built (`client-intake` → `landing-page-build`) and you
  need to confirm it is ready to launch.
- The operator says "run the launch checklist", "is this site ready to launch",
  "pre-launch check".

## Inputs

- The built `dist/` directory for the client site.
- The Google Business Profile URL and the analytics tag/domain.
- Whether the deploy and DNS approvals have been granted.

## Procedure

1. **Compose the UX audit** — call
   `packages.web.ux_audit.audit_dist(dist)` and require `report.passed`
   (responsive / a11y / performance / SEO). This is the site-quality gate; do not
   load the agentic `web-ux-audit` skill autonomously.
2. **Run the checklist** —
   `packages.agency.launch.run_launch_checklist(dist, gbp_url=..., analytics_id=...,
   deploy_approved=..., dns_approved=...)`. It checks the contact form, `<title>`,
   GBP link, analytics tag, and composes the deploy-readiness gates
   (`assert_deploy_ready`, `assert_custom_domain_allowed`).
3. **Fail closed.** The site may be marked live only when `report.ready` is true —
   every item passes and the deploy/DNS approvals are granted.

## Outputs

- A `LaunchChecklistReport` (`.ready`, per-item pass/fail with detail).

## Forbidden areas

- Does not deploy. Publishing is the separate, approval-gated `webdeploy` lane.
