# Web UX Audit

**Kind:** agentic · **Owner:** web · **Runtimes:** claude, codex

Audit a built web product for polish across four categories — responsive,
accessibility, performance, SEO — and act on the findings. The web build gate
(F2) is the fail-closed minimum; this is the quality bar that makes a site
genuinely professional and usable on every screen.

## When to use

- After the WEB lane builds a site and the F2 gate passes, before handing off to
  the deploy lane.
- Whenever asked to review or improve the responsiveness, accessibility, or
  performance of a generated site.

## Procedure

1. **Run the audit.** `packages.web.ux_audit.audit_dist(dist_dir)` returns a
   scored `UxAuditReport` (0-100 per category + findings).
2. **Fix `error` findings first**, then `warn`. Common fixes:
   - *Responsive:* ensure `width=device-width` and never disable zoom; use the
     design system's fluid units / `auto-fit` grids rather than fixed pixel
     widths.
   - *Accessibility:* `lang` on `<html>`, one `<h1>`, no skipped heading levels,
     `alt` on images, an accessible name on every control, a label for every
     input.
   - *Performance:* stay under the page-weight budget, defer/async non-critical
     scripts, compress images over the size budget.
   - *SEO:* a 10-70 char title, a meta description, Open Graph tags.
3. **Re-audit until every category clears the threshold** (default 70). Treat a
   sub-threshold category as a blocker, not a suggestion.

## Boundaries

- Audit and fix the built product; do not deploy (separate, gated lane).
- Don't game scores with hidden or off-screen content — fixes must be real.

## Definition of done

- Every category scores at or above the pass threshold.
- No `error`-severity findings remain.
