# Adapter (claude): Landing Page Build

Implements `skills/canonical/landing-page-build/skill.md` for the Claude runtime.
Follow the canonical procedure; this adapter only notes the concrete tool calls.

1. **Scaffold:** call `packages.web.scaffold.scaffold_site(target_dir, context,
   template="astro-landing")`. Build `context` from
   `packages.web.scaffold.default_context(site_name, tagline=..., audience=...)`
   and override the copy tokens with real product language.
2. **Preview offline:** `packages.web.scaffold.render_landing_html(context)`
   returns a self-contained HTML string — inspect it before building.
3. **Edit:** revise `src/pages/index.astro` and re-skin via `--brand` in
   `src/styles/global.css`. Keep one `<h1>`, alt text, named controls, and the
   responsive viewport.
4. **Validate:** build to `dist/` (`npm ci && npm run build`) and run
   `packages.web.validation.validate_web_dist(dist)`. All checks must pass.
5. **Stop at the gate:** a green build is `safe_for_review`. Routing to the
   `webdeploy` lane (publishing) is a separate, approval-gated step — never
   deploy from here.
