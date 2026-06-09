# Design Studio

**Kind:** agentic · **Owner:** web · **Runtimes:** claude, codex

Run the **premium design track** on a single chosen build: turn evidence and
references into a structured art-direction packet, build to that direction,
capture desktop/mobile screenshots, score them against the visual rubric, and
iterate until the work clears a five-figure quality bar.

## When to use

- **Opt-in, select builds only.** A demo you feel strongly about, or a paid
  client site. **Not** every cold-outreach demo — those keep using the normal
  `landing-page-build` / bespoke playbook flow untouched.
- The founder/operator explicitly elevates a build ("run the design studio on
  this", "make this a premium build").

If you're about to run this on a routine cold demo, stop — that's not what it's
for. The premium track adds real iteration cost on purpose.

## Inputs

- The build hub directory: `state/prospects/sites/<place_id>/` (bespoke demo,
  path B) or `products/<slug>-site/` (paid client, path C).
- Business evidence (reviews, services, real photos, visual cues) and 1–3
  inspiration references (Dribbble/Awwwards URLs + what's worth translating).

## Procedure

1. **Confirm this is a premium build.** Refuse to be the default. Note the build
   hub `<dir>`.
2. **Packet.** Write a spec (site name, category, audience, goal, evidence,
   visual assets, references with takeaways, `imagery_mode`) and run
   `python scripts/agency/design_studio.py packet --target <dir> --spec <spec.json|->`.
   Read the generated `<dir>/design-studio/packet.md` — that's your art-direction
   brief.
3. **Build to the packet — via the design engine** (the premium surface):
   - **Tokens:** `packages.web.design_system.synthesize_design_system(packet)` →
     write `design-system.css` (role-based, AA-gated, zoom-safe).
   - **Stack:** materialize `scaffold_site(target, ctx, template="astro-premium")`
     (Astro + GSAP/Lenis/Three motion).
   - **Layout:** `packages.web.blocks_composer.plan_composition(packet)` +
     `render_index_astro(...)` → a varied, archetype-driven page (not a stacked template).
   - **Imagery:** `scripts/agency/generate_imagery.py` (brief→generate→select); for a
     real client ship, founder-clear generated assets (`clear`) or swap for licensed.
   - **Reference:** optionally fold a Dribbble/Awwwards read in with
     `scripts/agency/analyze_reference.py`.
   - For the legacy hand-built path (B) or quick demos, the bespoke playbook still applies.
4. **Screenshot.**
   `python scripts/agency/design_studio.py shoot --target <dir> --dist <distDir>`
   captures desktop (1440) + mobile (390) full-page PNGs.
5. **Score against the rubric — with the independent judge.** Prefer
   `python scripts/agency/design_loop.py judge --target <dir>` (Gemini vision scores
   the screenshots — a different model family from the Claude builder, which
   neutralizes self-preference) → writes `scores.json`. Or grade by hand per
   [`visual_rubric.md`](../../../packages/web/design_reference/visual_rubric.md)
   (grade down on doubt). Then
   `python scripts/agency/design_studio.py review --target <dir> --scores <dir>/design-studio/scores.json`.
6. **Iterate until it passes.** A fail's notes are the revision brief — fix the
   build, re-shoot, re-score. Don't re-score the same pixels.
7. **Then the technical gates.** Only once the visual review passes, hand to the
   normal web gate (`validate_web_dist`) + UX audit, then the gated deploy lane.

## Boundaries

- **Premium-ready is a precondition for a premium deploy.** Do not route a
  packet-bearing build to the `webdeploy` lane until
  `python scripts/agency/design_studio.py status --target <dir>` shows
  `"passed": true`. (Hard enforcement in `deploy_readiness` policy is a separate
  founder-gated step — for now this is a procedural gate.)
- This skill does **not** deploy, buy domains, or wire payments — those stay in
  the deploy lane.
- Generated imagery is for the pitch/preview and our own fictional samples; a
  real client's published site must swap in owner-provided/licensed photos before
  go-live (honesty guardrail from the imagery playbook).

## Definition of done

- `<dir>/design-studio/` holds `packet.json` + `packet.md`, `screenshots/{desktop,mobile}.png`,
  `scores.json`, and `visual-review.json` + `review.md`.
- `status --target <dir>` reports `"passed": true` (overall ≥ 80/100, every
  category ≥ 4/5, both screenshots present).
- The normal web gate + UX audit also pass.
