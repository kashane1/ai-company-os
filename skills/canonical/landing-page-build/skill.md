# Landing Page Build

**Kind:** agentic · **Owner:** web · **Runtimes:** claude, codex

Build (or revise) a professional, responsive landing/marketing site for a
discovered opportunity, using the platform's Astro static-first scaffold, so it
can be validated by the web gate and shipped by the deploy lane.

## When to use

- A goal routes to the `web` lane (see `apps/worker-supervisor` routing): a
  landing page, waitlist, or marketing site for a wedge.
- You need a customer-facing page to run a **web-first validation experiment**
  (demand test) before committing to a full build.

> **Premium track (optional, select builds only):** this skill ships a solid,
> validated page — the right floor for cold-outreach demos. For a build you intend
> to *elevate* to five-figure quality (art direction, concept-led imagery,
> screenshot-scored visual review), run the `design-studio` skill instead/around
> this one. Don't put every cold demo through it — it adds real iteration cost on
> purpose.

## Inputs

- Product/opportunity context: name, audience, the problem, the promise, proof
  points, primary call-to-action (waitlist / pre-order / book a call).
- Target product directory: `products/<product-id>-web/`.

## Procedure

1. **Scaffold, don't start from scratch.** Materialize the Astro template with
   `packages.web.scaffold.scaffold_site(target, context)`. Fill the context with
   real product copy (`default_context` shows every token and a presentable
   default). One source of truth: the same markup renders the offline preview.
2. **Write conversion-oriented copy.** A clear single `<h1>` promise, a concrete
   subhead, three benefit-led features, a 3-step "how it works", one proof point,
   and a single primary CTA repeated at top and bottom. No filler.
3. **Keep it accessible and responsive by construction.** One `<h1>` per page,
   `lang` on `<html>`, a `<title>`, `alt` on every meaningful image, an
   accessible name on every link/button, and the `width=device-width` viewport.
   The design system (`global.css`) is already fluid (clamp type, `auto-fit`
   grids, dark-mode, reduced-motion) — re-skin via the `--brand` token rather
   than hand-rolling breakpoints.
4. **Build and self-check.** Run the web gate
   (`packages.web.validation.validate_web_dist`) over the built `dist/`. Every
   check must pass before handing off — broken links, missing assets, a missing
   viewport, or an a11y gap is a hard fail.
5. **Hand off.** A green build is `safe_for_review`. Deployment is a **separate,
   gated lane** (`webdeploy`) — do not deploy from this skill.

## Boundaries

- Do **not** deploy, buy domains, change DNS, or wire live payments here — those
  are gated actions owned by the deploy lane and `deploy_readiness` policy.
- Static-first: prefer plain HTML/CSS + Astro islands; reach for a full app
  framework only when a wedge graduates beyond a marketing page.
- Never invent proof/testimonials as if real; placeholder copy must read as
  placeholder until the founder supplies real claims.

## Definition of done

- `products/<product-id>-web/` builds cleanly to `dist/`.
- The full web gate passes (build, links, assets, responsive, accessibility).
- Copy is specific to the product and free of leftover scaffold tokens.
