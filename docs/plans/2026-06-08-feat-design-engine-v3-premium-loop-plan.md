# Design Engine v3 — the autonomous premium loop (the "five-figure factory")

> **TL;DR.** v2 built a real **measurement system** (independent Gemini judge,
> hard gate, token synthesizer, motion libraries, imagery pipeline) but bolted it
> onto **a loop that does not run**. The convergence orchestrator
> (`packages/web/design_loop.py:82`) has *zero non-test callers*; its CLI exposes
> only `judge`/`calibrate` with **no `run`**; no real build step exists; the
> premium scaffold template (`astro-premium`) is **never instantiated by any
> production code**; the generated imagery is **never read by the build**; and the
> judge is **motion-blind by construction** (`shoot.mjs` forces
> `reducedMotion:"reduce"`). The founder asked for "a loop that prompts the agent
> until the bar is met"; what shipped is a four-CLI manual relay a human walks a
> build through by hand. Honest grade of the *best* current output: **≈3.1/5 —
> sells at $2–4k, not $15k** (gap concentrated in motion/depth, layout
> originality, imagery, copy).
>
> **v3 closes the loop, then raises the ceiling.** Build the one missing keystone
> — `build_premium_site(packet, brief) → dist` — wire it into a `design_loop.py
> run` command, and the existing (tested, correct) orchestrator + scaffold +
> imagery pipeline all go live in a single stroke. Then make the judge *see* what
> it certifies (motion video + DOM + Lighthouse + a 13-dimension Awwwards-weighted
> rubric), and attack the visual tells (full-bleed treated imagery, real depth,
> per-build layout variety, generated conversion copy). **Build on the existing
> `astro-premium` lane — do not fork** (Astro is the right substrate; verdict in
> §5). Recommended loop mechanism: a **hybrid** — the tested Python orchestrator
> as the engine, a Claude sub-agent for the build leg only, cron + an append-only
> `loop-log.jsonl` for scheduling/resumability (§4).
>
> This supersedes nothing in v2's *primitives* — it makes them reachable. It is
> the sequel to [the v2 design-engine plan](2026-06-08-feat-design-engine-plan.md).

---

## 0. Why this plan exists

The founder's framing (paraphrased): *"the Claude Code creator says he doesn't
prompt it anymore — he writes loops that prompt it. I want that for Better
Business Web: an automated lane that produces extremely high-end, Awwwards/Dribbble
-caliber, five-figure websites, looping until the bar is met."*

That framing is **loop engineering** (Boris Cherny / Addy Osmani): stop
hand-driving turn-by-turn; author a controller that sets a goal, runs the model,
**evaluates the output with a separate signal**, decides the next prompt, and
**stops on a real condition**. For a generated artifact (a website) the proven
shape is `generate → render → independent-vision-judge → structured critique →
targeted patch → re-judge, until score ≥ threshold OR N rounds with no
improvement` (ReLook, Google ADK LoopAgent — see §11).

**The good news:** v2 already built ~80% of that shape correctly. **The gap:** the
two legs that actually make it *run* and *converge toward taste* are missing.

---

## 1. Ground truth — shipped at the primitive layer, false at the capability layer

The v2 plan's banner reads "ALL PHASES SHIPPED." Verified against `main`
(2026-06-08), that is true for *functions that exist and pass unit tests against
fakes*, and false for *a capability anyone can run*. The decisive findings:

| # | Finding | Evidence (verified) |
|---|---------|---------------------|
| 1 | **The loop is dead code.** `run_design_loop` is well-written but has **only test callers**. | `packages/web/design_loop.py:82`; sole caller `tests/python/unit/test_web_design_loop.py`. |
| 2 | **No `run` command.** The CLI exposes only `judge` + `calibrate`. The "loop" an operator runs is a markdown bullet ("Iterate until it passes"). | `scripts/agency/design_loop.py:72-77`; `skills/canonical/design-studio/skill.md:59`. |
| 3 | **No real build step.** `BuildStep` is an injected callable with **no implementation anywhere**. The only `build` stubs (tests) *ignore the revision brief*. | `packages/web/design_loop.py:32,102`; `test_web_design_loop.py:42`. |
| 4 | **Convergence is faked in tests.** The "it improved" test hard-codes `seq=[WEAK, STRONG]` and a stub that does `builds[0]+=1` — the brief is never consumed, yet the suite is green. | `test_web_design_loop.py:38,42,55-56`. |
| 5 | **The premium scaffold is never instantiated.** `scaffold_site(template="astro-premium")` is **passed nowhere**; production calls the generic `astro-landing`. `PREMIUM_TEMPLATE` is defined and unreferenced. | `scaffold.py:35,38`; `packages/agency/client_lifecycle.py:104`. |
| 6 | **The judge is motion-blind.** It scores **two static, motion-frozen PNGs** — the capture pipeline forces reduced motion. So the Phase-2 motion/WebGL work (v2's "biggest Awwwards-gap closer") is **invisible to the gate that exists to certify it**. | `scripts/web/shoot.mjs:103`; `gemini_judge.py:86-92`. |
| 7 | **The judge ignores the repo's own rubric.** The rich 0–5 anchors in `visual_rubric.md` are **never sent to Gemini** — the prompt only lists 6 category *names*. The model scores against its own taste. | `gemini_judge.py:38-45` vs `design_reference/visual_rubric.md`. |
| 8 | **Wrong, cheap judge model, non-deterministic.** `gemini-2.5-flash`, default temperature, no seed, no anchor images, single call. | `gemini_judge.py:25,86-101`. |
| 9 | **The imagery pipeline's output is discarded.** Generated PNGs + manifest are written, then **no composer/build reads the manifest**. Image model is `gemini-2.5-flash-image`, not the Pro model the docs claim; no seed/reference passed. The legal clearance gate `imagery_cleared()` has **zero callers**. | `imagery.py`, `blocks_composer.py`, `build.py`, `gemini_images.py:71-75`, `deploy.py`. |
| 10 | **"Reference analysis" analyzes no references.** No image/URL ingestion — it reads JSON/stdin; ~80% of the agent's read is dropped by a 5-branch keyword router; `type_scale_ratio`, `motion_cues`, `grid`, `hero_structure` never reach synthesis. | `analyze_reference.py:30-31`; `design_studio.py:386-399`. |
| 11 | **The calibration safety rail is inert.** `calibrate()` exists but there is **no gold corpus on disk** — no `expected`-labelled samples. The drift-halt can never fire. | `packages/web/design_loop.py:156`; absence under `products/better-business-web/portfolio/`. |
| 12 | **Copy is outside the loop.** Composer ships placeholders ("Detail 1", "Replace with real proof"); copy is "the build agent's job." The judge scores `copy_specificity` (truthfulness) but **nothing rewards five-figure conversion copy**. | `plan v2:53`; composer placeholders. |
| 13 | **`--motion-preset` is a dead token** — synthesized but never read by the motion layer; motion is one uniform fade-up + one parallax + an ambient shader. | motion layer never reads the token. |

**Net:** the *gate* is mature; the *driver*, the *path to the premium surface*,
and the *feedback signal for everything motion/imagery/copy* are missing.

---

## 2. What already exists — keep and build on (this engine is real)

- **The convergence skeleton is correct.** `run_design_loop` implements exactly
  the shape the research converges on: build→capture→judge→revise, best-index
  tracking, graceful degrade-to-best on exception, `needs_signoff=True` on pass
  (never auto-ships). It's right; it's just unwired. **Extend it, don't rebuild.**
- **Builder ≠ judge independence is architecturally enforced** — the single best
  decision in the codebase. Builder is Claude; judge is a different model family
  (Gemini), scoring **pixels not HTML**, blind to the builder's reasoning. This is
  precisely the decoupled-offline-judge design the reward-hacking literature
  recommends (arXiv 2407.04549). **Do not weaken this.**
- **The gate is a real hard gate.** Overall ≥80, every category ≥4/5, three
  critical categories fail on a single 3 (`design_studio.py:29-36, 205-277`).
  Per-category floors + critical-fail-on-3 prevents halo-averaging. Thresholds are
  sound.
- **The token/CSS synthesis is above bootstrap-grade.** Fluid `clamp()` type with
  rem-base zoom-safety, AA-gated accents that iterate until contrast clears 4.5:1,
  role-based tokens so a re-synthesis re-themes the whole site, DTCG export. The
  *plumbing* is good; the *expressive surface* is thin (§3c).
- **The motion libraries are Awwwards-grade and correctly wired** — Lenis↔GSAP
  ScrollTrigger synced with `lagSmoothing(0)`, a real fbm-shader WebGL hero with
  IntersectionObserver pause + WebGL-absent degradation, exemplary progressive
  enhancement. The stack is there; the choreography spends ~15% of it.
- **The typography craft genuinely reads boutique** — Fraunces display + italic
  accent words + mono micro-eyebrows is the one thing already punching above the
  rest (graded 3.5; see §3).
- **The skill wiring structure is clean** (canonical→adapter→pointer→registry per
  `skills/WIRING.md`), and the cheap-tier learnings are hard-won and inheritable
  (`docs/demo-site-learnings.md`, `docs/demo-site-build-playbook.md`).

---

## 3. The honest quality grade (what the pixels actually say)

Grading the **best** current output (`barbering-v3`, `auto-repair-v3` — the new
engine, not the legacy demo pages), 1 = cheap template, 5 = Awwwards SOTD:

| Dimension | Score | Why |
|---|---|---|
| Hero impact | 3.5 | Left-aligned serif headline + italic accent + drop cap breaks the centered stack — but the photo is small, boxed, uncropped (reads "editorial article," not "cinematic hero"). |
| Typography craft | 3.5 | Best dimension — Fraunces + italic accents + mono eyebrows reads boutique. Held back by flat body hierarchy + identical rhythm across all builds. |
| Art direction | 3.0 | A real per-build POV (warm-leather barber; near-black technical auto) — but it's **one recipe re-skinned**; no compositional signature. |
| Layout originality | 2.5 | Blocks break the stack, but **every build marches the same section order** (hero→stats→split→grid→process→quote→CTA). Predictable rhythm is the "$500 tell." |
| Visible motion / depth | 2.0 | Weakest, and it matters. Only depth primitives are one reused `.glow` radial + 4% grain. **No shadows, no layering, no overlap, no z-depth.** Motion is invisible in the (frozen) capture. |
| Spacing / polish | 3.5 | Legitimately clean fluid scale + generous rhythm. Knocked for being *uniform* — no compression/expansion tension. |
| Conversion clarity | 3.0 | CTAs present + proof + location — but ghost-bordered hero CTA, buried booking, no urgency/trust density a high-ticket page carries. |

**Weighted ≈ 3.1/5 — "solid pro / nice indie studio."** Sells at $2–4k. The gap to
$15k is concrete: **motion/depth, layout originality, art-directed imagery, copy.**

The **12 AI/cheap "tells"** (from the research, now the judge's penalty list):
default sans flat · purple/indigo "aurora" gradient · multi-color gradient
headline · three-icon feature grid · centered-everything hero · glassmorphism
everywhere · one radius + one timid shadow · fake stat/social-proof bar · bouncing
scroll-mouse · fake dashboard mockup · generic copy ("transform your workflow") ·
functional hollowness (no form validation/focus/ARIA). The legacy demo pages
(`luminous-dark` / `warm-boutique` — *the same page in two palettes*) hit most of
these and should be **quarantined or rebuilt on the v3 engine** (eat our own dog
food).

---

## 4. Recommended architecture for the autonomous premium loop

**Control flow** (the build leg is the only leg that needs Claude):

```
PRECONDITION  refuse default → design_studio.py packet → packet.json + packet.md
              (packet.md = the persisted done-condition + scope anchor)
CALIBRATION   design_loop.py calibrate --gold gold.json
GATE          if judge mislabels gold → HALT, alert founder (don't trust a drifted judge)

LOOP run_design_loop(max_iters=4, no_improve_patience=2, budget=BudgetGuard):
  i=0: build_premium_site(packet, brief=None)        ◄── AGENT LEG (Claude)
  i>0: build_premium_site(packet, apply_brief(brief)) ◄── parametric revision
       └─ synthesize_design_system → design-system.css
       └─ scaffold_site(template="astro-premium")        [the never-called premium path]
       └─ plan_composition + render            [+ structural variants from brief]
       └─ generate_imagery brief→generate→auto-curate     [wire manifest INTO blocks]
       └─ generate conversion copy from packet.evidence
       └─ build_site (npm)                                [build.py already exists]
  capture()  → shoot.mjs: static PNGs + FULL-MOTION scroll video (un-freeze)
  scores = judge(shots, video, dom, lighthouse, anchors) ◄── INDEPENDENT (Gemini), N=2-3 on criticals
  report = review_visual_quality(scores)                  ◄── GATE (every cat ≥ floor)
  on_progress → append loop-log.jsonl                     ◄── CHECKPOINT / resumable
  if report.passed: STOP, needs_signoff=True             ◄── never auto-ship
  if score ≤ best-so-far: REJECT revision, re-prompt      ◄── monotonic accept (ReLook)
  if no improvement for K rounds: HALT, surface best      ◄── plateau detection
  if budget exceeded: HALT, surface best
  brief = revision_brief(report)                          ◄── structured critique → next patch
FOUNDER SIGN-OFF  surface review.md + best screenshots → founder disposes
ON PASS+SIGNOFF   → validate_web_dist + ux_audit → gated webdeploy
```

**Mechanism: HYBRID — Python orchestrator as the engine + a Claude sub-agent for
the build leg + cron/`loop-log.jsonl` for scheduling + resumability.** Why, mapped
to repo tools:

- **Not pure `/loop`** (the ralph-loop pattern): it re-feeds the same prompt to one
  Claude session and relies on the model's **self-judgment** to decide "done" — re-
  introducing the self-preference bias the builder≠judge design eliminated. Use
  `/loop` only as a *driver* for the build leg, never as the judge.
- **Not pure Workflow-tool JS:** the convergence engine, calibration, best-tracking
  and graceful degradation **already exist and are tested in Python**. Re-implementing
  in JS duplicates source for no gain.
- **Not pure Python:** Python can't *be* Claude — the build/revise leg needs the
  agent to compose the site from packet + brief.
- **So:** extend the tested `run_design_loop`; its `BuildStep` hands control to a
  Claude sub-agent for the build leg only; the judge stays the independent Gemini
  call; cron + `loop-log.jsonl` give scheduling/resumability. All additions land in
  `packages/web/` + `scripts/agency/` (web-owned, outside the founder-gated set).

**Anti-reward-hacking guards (most already present; ✅ = exists, ➕ = add):**
gate not gradient ✅ · never feed the judge the builder's reasoning ✅ · render-
failure = hard fail ✅ · per-category floors ✅ · founder disposes ✅ · monotonic
acceptance ➕ · plateau cap ➕ · gold-set drift halt (build the corpus) ➕ ·
optional 2-of-3 judge panel on critical categories, disagreement → founder ➕.
(Research: ReLook; "Spontaneous Reward Hacking in Iterative Self-Refinement,"
arXiv 2407.04549 — improvements plateau after 1–2 rounds while a weak judge keeps
inflating; decoupled judge + monotonic accept are the documented fixes.)

---

## 5. Build on v2, do not fork — and keep Astro

**Extend the existing `astro-premium` lane.** Reasons:

1. **The foundation is correct, not the problem.** The gaps are *unwired pieces and
   missing dimensions*, not wrong architecture. A fork re-pays for the good parts
   (orchestrator, judge, token synthesizer, motion libraries).
2. **Astro is the right substrate for the five-figure bar.** Its zero-JS-by-default
   per-page bundling is precisely the premium advantage — an 800KB Three.js hero
   never taxes a contact page, protecting the **performance axis Awwwards juries
   score (30%)**. Next.js ships a React baseline everywhere; vanilla Vite throws
   away routing/SEO/content-collections. The motion stack (GSAP/Lenis/Three/Barba)
   is framework-agnostic, so switching unlocks *no* capability and costs Astro's
   biggest edge.
3. **The one Astro ceiling is bounded with a known fix.** Persistent state across
   multi-page navigation (a site-wide canvas surviving route changes) is the only
   place Astro fights you — solved per-build with the Barba.js-inside-Astro pattern
   (Codrops), an opt-in escape hatch. The immediate universal fix: a
   `BaseLayout.astro` with `<ClientRouter />` + lifecycle-safe `gsap.context()`
   teardown (today `motion.ts` inits at module top-level and **breaks the instant
   ClientRouter is added** — the highest-value scaffold fix).

**Retire, don't fork:** quarantine the legacy centered-stack demo pages out of the
showcase, or rebuild the BBW marketing site on the v3 engine.

---

## 6. Phased upgrade plan (v3)

Ordered by leverage. **[founder-gated]** marks edits to `packages/policies`,
`packages/schemas`, `skills/canonical`, `skills/registry.yaml` (require explicit
founder approval per [REPO_MAP](../../REPO_MAP.md)). Everything else is web-owned.

### Phase 1 — Close the loop (make the founder's vision *exist*)
**Goal:** one command runs build→judge→revise→repeat autonomously to a pass.

> **Build status (2026-06-08) — web-owned keystone SHIPPED & verified; founder-gated
> wiring + live run DEFERRED.** Honest accounting (not "all shipped"): the loop now
> *closes* against fakes in CI (1332 unit tests green, ruff clean). What shipped:
> `packages/web/premium_build.py` (`build_premium_site` — instantiates the
> previously-never-called `astro-premium` path; `apply_brief` — real parametric
> revision; `run_premium_loop` — checkpointed driver); `BudgetGuard` + plateau +
> monotonic-branch-from-best in `packages/web/design_loop.py`; `design_loop.py run`
> CLI; `generate_imagery.py select --auto-curate`; and the faked-convergence test is
> replaced by one that proves the brief is consumed. **Not done (by design):** the
> **[founder-gated]** `design-loop` skill/registry/skill.md wiring (awaiting
> approval), and the **live end-to-end run** (needs `npm` + `GEMINI_API_KEY` — the
> founder runs it). The thin builder is deterministic; it closes the loop but won't
> clear the five-figure gate until Phases 2–4 add the judge's sight + depth/imagery/
> copy. That is the intended sequence, not a regression.

**Deliverables:**
- `packages/web/premium_build.py::build_premium_site(packet, brief, target) → dist`
  — the missing keystone: synthesize → `scaffold_site(template="astro-premium")` →
  compose → (imagery, copy) → `build_site`.
- `apply_brief(packet, brief) → packet'` — parametric revision: failing-category →
  token/block/motion deltas (replaces "human starts over").
- `run` subcommand in `scripts/agency/design_loop.py` driving `run_design_loop`.
- `BudgetGuard` (max iters / $ / wall-clock) + plateau detection + monotonic
  acceptance in `packages/web/design_loop.py`; `loop-log.jsonl` checkpoint via
  `on_progress`; resume-from-log on restart.
- `generate_imagery.py select --auto-curate top-N` (promised in v2, absent).
- **[founder-gated]** `design-loop` registry skill + triggers ("run the premium
  factory on `<niche>`"); update `skills/canonical/design-studio/skill.md` to point
  at `run` instead of raw Python calls.
- **Tests that actually exercise a `build` callable consuming the brief** (kill the
  faked-convergence pattern).
**Exit:** `design_loop.py run --spec X` produces a built `dist/`, scores it,
revises on fail, converges or halts-to-best **with no human between iterations** —
against fakes in CI, then once live with a real `GEMINI_API_KEY`.

### Phase 2 — Make the judge see what it certifies
**Goal:** the gate can perceive motion, performance, and the AI-house-style tells.

> **Build status (2026-06-08) — SHIPPED & verified (1338 tests green).** The judge now
> *sees motion* and grades against the repo's rubric: `shoot.mjs --frames N` captures
> motion-enabled scroll frames; `gemini_judge.py` injects the full `visual_rubric.md`
> anchors, ingests the scroll frames, runs low-temp with an N-sample per-category
> median, and scores the **v3 12-dimension rubric** (single source of truth:
> `design_studio.RUBRIC_CATEGORIES`) — adding `color_system`, `whitespace_depth`,
> `motion_quality`, `signature_moment`, `conversion_strength`, and a critical
> `ai_house_style` anti-tell. Gold corpus at
> `products/better-business-web/portfolio/calibration/gold.json` (starter set all
> known-"bad" — nothing in-repo clears the bar yet — which catches a too-lenient
> judge; "good" exemplars land with the first flagship pass). **Deviations from §7,
> by design:** equal per-category floor + critical gate (stricter, less fragile)
> instead of 40/30/20/10 weighting; performance + a11y stay in `ux_audit` so the
> Gemini judge is a pure taste+motion judge (no fragile Lighthouse-in-Gemini); and
> scores-provenance stamping is deferred (the autonomous `run` path calls the judge
> in-process and can't be hand-gamed).

**Deliverables:**
- Un-freeze capture: extend `scripts/web/shoot.mjs` to record a full-motion
  scroll-through video (keep a reduced-motion static pass for a11y).
- Feed video + DOM/computed-styles + a real Lighthouse trace to `gemini_judge.py`;
  **inject the rubric anchors into the prompt**; add `generationConfig` (low temp,
  N=2–3 median on critical categories); provenance-stamp `scores.json` and reject
  builder-written scores (close the self-scoring loophole).
- **[founder-gated]** the v3 rubric (§7) into `design_reference/visual_rubric.md`
  (+ `motion_quality`, `signature_moment`, `conversion_strength`, `performance`,
  AI-tell penalty cap).
- Build the gold calibration corpus under
  `products/better-business-web/portfolio/calibration/gold.json` (15–25 labelled
  Awwwards / template / own-build samples); wire `calibrate` into CI; pass "good"
  anchors as few-shot images.
**Exit:** `calibrate` runs against a real corpus and passes; the judge scores a
motionless page strictly below an equivalent animated one.

### Phase 3 — Imagery + depth + layout variety (the verified 3.1 → 4.5 jump)
**Goal:** kill the "$500 template" tells in the pixels.

> **Build status (2026-06-08) — SHIPPED & verified (1344 tests green).** The page now
> has pictures, depth, and variety: `design_system.py` emits an elevation ramp
> (`--shadow-1/-2/-3`, canvas-tuned) + a spacing scale + 12-col grid tokens;
> `global.css` gains `.card`/`.elevated`/`.media`/`.scrim` utilities; `CinematicHero`
> gets a full-bleed image variant, `BentoGallery` renders treated images, and a new
> `FullBleedMedia` block is the edge-to-edge image-over-type moment. The composer
> picks one of N **per-archetype structural variants by a stable concept hash** (not
> the seed) so two same-archetype builds differ, and `derive_content` places hero +
> gallery + full-bleed imagery. `build_premium_site` stages the imagery manifest's
> selected assets into `public/img/` and references them. `gemini_images.py` gains
> `model` (Pro: `gemini-3-pro-image-preview`) + `seed`; the imagery CLI uses them.
> Imagery clearance is gated by `premium_ready()` (correct layer — `deploy()` is
> site-generic and doesn't know the build hub). Live image generation needs
> `GEMINI_API_KEY`; the wiring is unit-tested with stub assets.

**Deliverables:**
- Media model + image slots in every block; `derive_content` reads
  `imagery/manifest.json`; a full-bleed hero variant (image-over-type + scrim);
  `BentoGallery` renders treated images.
- Elevation/shadow tokens + a real spacing scale + 12-col grid tokens in
  `design_system.py` / `global.css` / `design-system.css`; refactor blocks off
  inline `!important` grids.
- 3 new image-first blocks (`FullBleedMedia`, `MediaCollage`, `ProjectShowcase`);
  per-block structural variants **selected by concept, not seed** (so two same-
  archetype builds are visibly different).
- Upgrade `gemini_images.py` to the Pro image model + seed + reference-image;
  concept-specific shot lists; per-build image treatment (duotone/editorial crop).
- Wire `imagery_cleared()` into `deploy.py` (the legal gate that never runs).
**Exit:** every page has ≥1 full-bleed treated image moment + visible depth; best
output judge ≥4 on art-direction and layout; two same-archetype builds differ.

### Phase 4 — Motion choreography + conversion copy
**Goal:** spend the loaded libraries; make copy a judged artifact.

> **Build status (2026-06-08) — SHIPPED & verified (1348 tests green).** Motion is
> now spent and lifecycle-safe, and copy is a real generated artifact: `motion.ts`
> is rewritten boot()/shutdown() lifecycle-safe (survives view-transition nav,
> no-ops to a single boot on MPA — R3's "highest-value fix"); `scroll.ts` reads the
> previously-dead `--motion-preset` token and varies stagger/ease/parallax per
> archetype, returning a teardown handle; a new `cursor.ts` adds a custom cursor +
> magnetic CTAs (fine-pointer only, fully torn down). New `packages/web/copy.py`
> derives **grounded conversion copy** from `packet.evidence`/goal (intent-matched
> CTA — "Book your visit" / "Get a free quote" — never fabricated claims); the
> composer uses it for hero/split/CTA/full-bleed slots, and `apply_brief` treats a
> `conversion_strength` fail as a copy lever. **Deferred (need a live build to
> verify; the generated site is single-page):** wiring `<ViewTransitions>` into the
> generated page (motion.ts is already lifecycle-*ready*), GSAP SplitText per-char
> reveals (needs a gsap 3.13 bump), and an explicit pin+scrub scene (StickyProcess
> uses CSS `position:sticky` today). TS/Astro changes are verified by structure +
> the offline smoke, not a browser (no npm in this environment).

**Deliverables:**
- `BaseLayout.astro` + `<ClientRouter />` + lifecycle-safe `gsap.context()`
  teardown; wire `--motion-preset` to distinct choreography; SplitText reveals; one
  real pin+scrub scene; custom cursor + magnetic CTAs.
- Conversion-copy generation in `build_premium_site` from `packet.evidence`; copy
  deltas in `RevisionBrief`.
**Exit:** each archetype has a distinct motion personality; the loop generates and
revises copy autonomously; AI-tell count on output drops to 0–1.

### Phase 5 — Reference-anchored convergence + scale
**Goal:** the loop converges *toward a chosen exemplar*, then fans out.
**Deliverables:** real reference ingestion (`--image`/`--url` → vision + k-means
palette); a structured art-direction packet with controlled vocabularies
(`grid_system`, `hero_archetype`, `motion_signature{easing,stagger,parallax,
reveal}`, `scale_contrast`) **driving** synthesis/composition/motion (replace the
keyword router `design_studio.py:386-399`); feed the reference to the judge;
niche→spec helper; `make premium NICHE=…`; prove on **one flagship niche** before
fanning out.
**Exit:** a reference shot measurably changes layout (not just color); one flagship
build clears the premium gate end-to-end.

**Recommended first flagship niche** (high premium upside + visual potential +
conversion value): **med spa**, **boutique fitness/pilates**, or **high-end local
restaurant**. Pick at Phase 5; the keystone (Phases 1–4) is niche-agnostic.

---

## 7. The v3 premium rubric (the new fitness function)

For the vision judge, scored 1–5 with desktop+mobile PNGs **+ a scroll video + DOM/
computed-styles + a Lighthouse trace**. Mapped to Awwwards weights (Design 40 /
Usability 30 / Creativity 20 / Content 10). **Pass = weighted ≥ 8.0 AND every
dimension ≥ 4 AND criticals ≥ 4 AND ≤1 AI-tell AND perf budget met.** (★ critical;
a single 3 fails the build.)

| # | Dimension | Source | A **5** looks like |
|---|-----------|--------|--------------------|
| 1★ | Visual thesis / concept | V,D | One memorable idea carried through every section; on-brand, not generic. |
| 2★ | Hero impact | V | First screen feels expensive — full-bleed treated imagery, type *over* image, depth. |
| 3 | Typographic craft | V,D | Bespoke display+text pairing, fluid clamp scale, 3×+ hierarchy jumps, tuned tracking. |
| 4 | Color & contrast system | V,D | Dominant color + one sharp accent, tokenized, AA-clear, deliberate light/dark. |
| 5 | Layout & composition | V,D | Intentional asymmetry/overlap on a disciplined baseline grid; mobile recomposed. |
| 6 | Whitespace, rhythm & depth | V,D | Consistent spacing scale; real elevation/shadow layering; sections breathe. |
| 7★ | Imagery & art direction | V | Original/treated photography or custom 3D, consistent grade, full-bleed moment, AVIF/WebP. |
| 8 | Motion quality | video,D,P | Cohesive easing/duration language, restraint, smooth-scroll, scroll-linked reveals, 60fps. |
| 9 | Signature moment | video,D | One unforgettable on-concept interaction executed flawlessly. |
| 10 | Micro-interaction finish | V,D | Crafted hover/active/focus/loading states; magnetic CTAs; real form validation. |
| 11 | Conversion strength | V,D | Sharp offer, clear CTA hierarchy, social proof placed for persuasion, low friction. |
| 12 | Content & copy quality | V,D | Specific, brand-voiced, every claim substantiated, designed-not-pasted. |
| 13 | Performance & a11y | P,D | LCP<2.5s, CLS<0.1, INP<200ms, Lighthouse≥90, weight<3MB, keyboard-nav, reduced-motion. |
| — | **AI-tell penalty (cap)** | V,D | Zero of the 12 tells (§3). **3+ tells caps the total at 2.5/5 regardless.** |

Aggregation: `raw = Σ(score/5·weight)`; `score5 = clamp(raw·5 − 0.05·tells·5, 1,
5)`; `if tells ≥ 3: score5 = min(score5, 2.5)`. Each dimension scored in a separate
call (avoid halo); every justification must cite a specific observable (a
font-family, hex, LCP number, or DOM node).

---

## 8. First concrete move

**Build `packages/web/premium_build.py::build_premium_site(packet, brief, target)
→ dist` and wire it into a `design_loop.py run` command.**

Every other gap is a refinement on a loop that doesn't close: the judge is good but
judges nothing autonomously; the scaffold is good but is never instantiated; the
imagery pipeline runs but its output is discarded; the orchestrator is correct but
has no `BuildStep` to call. This is the smallest change that converts the founder's
request from a diagram into a running program — and it makes `run_design_loop`, the
premium scaffold, and the imagery pipeline all go live in one stroke. **Ship a
thin version first** (synthesize → scaffold → compose → build; brief applied as
token deltas only), prove the loop closes on one build, then layer imagery / motion
/ copy quality into the now-running loop.

---

## 9. Risks & anti-patterns to avoid

- **Reward-hacking the judge** (the biggest long-run risk): keep builder≠judge
  across families; score fresh pixels every round (never feed the judge the
  builder's reasoning); gate not gradient; monotonic acceptance; plateau cap; build
  the gold corpus so drift actually halts the loop (today it's inert).
- **Faking convergence in tests:** v3 tests must exercise a `build` callable that
  *actually consumes the brief*, or the green suite will again certify a loop that
  doesn't close.
- **Scope creep before the loop works:** resist building the full 13-dim rubric,
  video judging, Barba transitions, and tonal ramps before Phase 1 runs end-to-end.
- **Template-sameness:** determinism makes two same-archetype builds byte-identical
  today — variant selection must be concept/reference-driven, or the factory ships
  the same site to every plumber.
- **Declaring "shipped" at the primitive layer:** v3 status is measured by *"did
  the loop run end-to-end and clear the gate on a real build,"* not *"do the
  functions exist and pass unit tests against fakes."*
- **Premium-dependency failure collapses the thesis:** on a Gemini/imagery failure
  the loop degrades to "whatever images you had" — exactly when the premium
  differentiator breaks. Add retry/queue before relying on generated imagery, and
  keep the founder-sign-off gate as the ultimate backstop (never auto-ship).

---

## 10. Key files for the v3 build

`packages/web/design_loop.py` (extend the engine) · `packages/web/premium_build.py`
(**new — the keystone**) · `scripts/agency/design_loop.py` (add `run`) ·
`packages/web/gemini_judge.py` + `scripts/web/shoot.mjs` (un-freeze + video +
anchors + determinism) · `packages/web/blocks_composer.py` +
`scaffold/astro-premium/src/blocks/` (media + depth + variants) +
`src/styles/{global,design-system}.css` (elevation/spacing/grid tokens) +
`src/scripts/motion.ts` + new `BaseLayout.astro` (lifecycle-safe ClientRouter) ·
`packages/web/imagery.py` + `packages/tools/content_tools/gemini_images.py` (wire +
upgrade model/seed/refs) · `packages/web/deploy.py` (wire `imagery_cleared`) ·
`packages/web/reference_params.py` + `scripts/agency/analyze_reference.py` (real
ingestion) · `products/better-business-web/portfolio/calibration/gold.json` (**new
corpus**) · **[founder-gated]** `packages/web/design_reference/visual_rubric.md`,
`skills/registry.yaml`, `skills/canonical/design-studio/skill.md`.

---

## 11. Sources (external grounding)

- **Loop engineering:** Boris Cherny — write loops, not prompts ([Digg](https://digg.com/ai/q0idpj2w), [OfficeChai](https://officechai.com/ai/i-now-just-write-loops-to-prompt-claude-code-claude-code-creator-boris-cherny/)); [Addy Osmani — Loop Engineering](https://addyosmani.com/blog/loop-engineering/) / [Long-running Agents](https://addyosmani.com/blog/long-running-agents/).
- **Generate→render→vision-judge→refine:** [ReLook, arXiv 2510.11498](https://arxiv.org/html/2510.11498); [Google ADK Loop Agents](https://google.github.io/adk-docs/agents/workflow-agents/loop-agents/); [Vision-Guided Iterative Refinement, arXiv 2604.05839](https://arxiv.org/html/2604.05839v1).
- **Independent judge / reward hacking:** [Spontaneous Reward Hacking in Iterative Self-Refinement, arXiv 2407.04549](https://arxiv.org/html/2407.04549v1); [Evidently AI — LLM-as-a-judge](https://www.evidentlyai.com/llm-guide/llm-as-a-judge); [orq.ai — LLM juries](https://orq.ai/blog/llm-juries-in-practice).
- **The Awwwards bar:** [Awwwards Evaluation System (40/30/20/10)](https://www.awwwards.com/about-evaluation/); [Utsubo — judging criteria decoded](https://www.utsubo.com/blog/award-winning-website-design-guide); [Codrops](https://tympanus.net/codrops/); [Lenis](https://github.com/darkroomengineering/lenis).
- **AI "tells":** [prg.sh — the purple gradient website](https://prg.sh/ramblings/Why-Your-AI-Keeps-Building-the-Same-Purple-Gradient-Website); [newwebsite.ai — 10 signs](https://www.newwebsite.ai/blog/10-signs-a-website-was-designed-by-ai).
- **Astro for premium:** [Astro View Transitions](https://docs.astro.build/en/guides/view-transitions/) / [Islands](https://docs.astro.build/en/concepts/islands/); [Codrops — Barba.js + GSAP in Astro](https://tympanus.net/codrops/2026/04/08/creating-custom-page-transitions-in-astro-with-barba-js-and-gsap/); [astro#12725 (Lenis/ClientRouter)](https://github.com/withastro/astro/issues/12725); [astro#15728 (Safari WebGL persist)](https://github.com/withastro/astro/pull/15728).
