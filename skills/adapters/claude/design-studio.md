# Adapter (claude): Design Studio

Implements `skills/canonical/design-studio/skill.md` for the Claude runtime.
Follow the canonical procedure; this adapter only notes the concrete tool calls.

The orchestration entrypoint is `scripts/agency/design_studio.py`
(`packet` / `shoot` / `review` / `status`). The pure contract it wraps is
`packages.web.design_studio` (`build_design_studio_packet`,
`review_visual_quality`). The scorer's anchors live in
`packages/web/design_reference/visual_rubric.md`.

1. **Packet:** compose the spec JSON, then
   `Bash: python scripts/agency/design_studio.py packet --target <dir> --spec <spec.json>`
   (or pipe via `--spec -`). Read `<dir>/design-studio/packet.md`.
2. **Build:** path B → bespoke playbook; path C →
   `packages.web.scaffold.scaffold_site`. For weak imagery, generate a cohesive
   concept-led set (Gemini "Nano Banana Pro" via the imagery playbook), curate,
   optimize to webp, build the page on the concept.
3. **Shoot:** `Bash: python scripts/agency/design_studio.py shoot --target <dir> --dist <distDir>`.
4. **Score:** view `design-studio/screenshots/{desktop,mobile}.png` (Read the
   PNGs directly), grade all six rubric categories, write
   `design-studio/scores.json`, then
   `Bash: python scripts/agency/design_studio.py review --target <dir> --scores design-studio/scores.json`.
   Exit code 1 = fail; the printed codes + `review.md` notes are the revision brief.
5. **Iterate** until `Bash: python scripts/agency/design_studio.py status --target <dir>`
   shows `"passed": true`.
6. **Then** run `packages.web.validation.validate_web_dist(dist)` and the UX
   audit. Do not route to `webdeploy` until both the visual review and the web
   gate pass.
