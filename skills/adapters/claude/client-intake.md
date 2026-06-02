# Adapter (claude): Client Intake

Implements `skills/canonical/client-intake/skill.md` for the Claude runtime.
Follow the canonical procedure; this adapter notes the concrete tool calls.

1. **Capture:** build `packages.agency.intake.ClientIntake(business_name=...,
   service_category=..., city=..., services=[...], phone=..., hours=...,
   ideal_customer=..., competitors=[...])` and call `.validate()`.
2. **Brief:** `packages.agency.intake.render_brief(intake)` → write to
   `docs/products/<slug>-site/CLIENT_BRIEF.md`.
3. **Site context:** `intake.to_site_context()` → pass to
   `packages.web.scaffold.scaffold_site(target_dir, context)` (or hand to
   `landing-page-build`). Preview offline with
   `packages.web.scaffold.render_landing_html(context)`.
4. **Stop at a buildable site.** Launch is the gated `launch-checklist` step.
