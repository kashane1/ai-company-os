# Adapter (claude): Design Studio

Implements `skills/canonical/design-studio/skill.md` for the Claude runtime.
Follow the canonical procedure; this adapter only notes the concrete tool calls.

Entrypoints: `scripts/agency/design_loop.py` (`run` — the autonomous loop;
`judge` / `calibrate`) and `scripts/agency/design_studio.py`
(`packet` / `shoot` / `review` / `status`). The pure contracts they wrap are
`packages.web.premium_build` (`build_premium_site`, `apply_brief`,
`run_premium_loop`), `packages.web.design_loop` (`run_design_loop`, `BudgetGuard`),
and `packages.web.design_studio` (`build_design_studio_packet`,
`review_visual_quality`). The scorer's anchors live in
`packages/web/design_reference/visual_rubric.md`.

**Path A — autonomous (preferred):**
1. **Packet:** compose the spec JSON, then
   `Bash: python scripts/agency/design_studio.py packet --target <dir> --spec <spec.json>`
   (or `--spec -`). Read `<dir>/design-studio/packet.md`.
2. **Run:** `Bash: python scripts/agency/design_loop.py run --target <dir> --spec <spec.json>`
   (`--max-iters`, `--max-seconds`, `--no-improve-patience` tune the stop conditions).
   It builds → shoots → Gemini-judges → parametric-revises → repeats until PASS or a
   halt-to-best. Exit 0 = passed (still needs founder sign-off). Read
   `<dir>/design-studio/loop-log.jsonl` + `visual-review.json`.

**Path B — manual / refinement:**
3. **Build:** `packages.web.premium_build.build_premium_site(packet, <dir>/site)`
   (path B bespoke → playbook). For weak imagery, generate a cohesive concept-led set
   (Gemini), curate (`generate_imagery.py select [--auto-curate N]`), build on the concept.
4. **Shoot:** `Bash: python scripts/agency/design_studio.py shoot --target <dir> --dist <distDir>`.
5. **Score:** view `design-studio/screenshots/{desktop,mobile}.png` (Read the PNGs),
   or `Bash: python scripts/agency/design_loop.py judge --target <dir>` (Gemini),
   then `Bash: python scripts/agency/design_studio.py review --target <dir> --scores design-studio/scores.json`.
   Exit 1 = fail; the codes + `review.md` notes are the revision brief.
6. **Iterate** until `Bash: python scripts/agency/design_studio.py status --target <dir>`
   shows `"passed": true`.

**Both:** then run `packages.web.validation.validate_web_dist(dist)` and the UX
audit. Do not route to `webdeploy` until both the visual review and the web gate pass.
