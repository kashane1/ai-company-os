# Design Engine plan v2 — a five-figure web design studio

> **TL;DR.** v1 of this plan was scoped to "semi-automate cheaply." The founder
> overruled that: the goal is **capability, not thrift** — build a studio whose
> output justifies $15k–$65k, however few builds run through it. If a capability
> is missing from the repo, we build it here. This v2 keeps **all** phases and
> *hardens* them with the surviving review findings (role-based tokens,
> builder≠judge, enforced imagery provenance, per-phase definition-of-done).
>
> Four founder decisions are locked (2026-06-08): **(1) a new premium build
> stack** (Astro + interactive islands + motion), **(2) full motion + WebGL/3D**,
> **(3) a top-tier generated-imagery pipeline** used on production (with
> provenance + clearance), **(4) an independent-judge quality gate with founder
> sign-off**. Committing to one premium surface dissolves v1's worst problem (the
> dual-surface token fork). Sequence: Phase 0 stack → 1 tokens → 2 motion → 3
> blocks → 4 imagery → 5 reference analyzer → 6 quality loop.

This supersedes the v1 body below the line. It is the sequel to the Design Studio
integration ([2026-06-08-feat-design-studio-integration-plan.md](2026-06-08-feat-design-studio-integration-plan.md)),
which already built the measurement half (packet → shoot → score → review →
deploy guard). This plan builds the **generation** half and the **convergence
loop**.

## Locked decisions (founder, 2026-06-08)

| # | Decision | Consequence |
|---|---|---|
| 1 | **New premium build stack** | One surface to author craft in; bespoke demos migrate up. Kills the dual-surface token fork. |
| 2 | **Full motion + WebGL/3D** | A real motion layer (GSAP + Lenis + scroll choreography) + a Three.js/WebGL hero kit. The biggest "Awwwards gap" closer. |
| 3 | **Top-tier generated imagery, used on production** | Reference-anchored + seeded Gemini pipeline. Provenance tracked + founder-cleared per asset (legal posture is logged, not silent). |
| 4 | **Independent judge + founder sign-off** | Claude builds; a *different* model family (Gemini vision) scores screenshots; founder approves before any client ship. |

## Build status (2026-06-08, branch `feat/design-engine-v2`) — ALL PHASES SHIPPED

- [x] **Phase 0 — premium stack** — `scaffold/astro-premium/`; builds, web gate
  passes, renders a synthesized dark+copper premium page.
- [x] **Phase 1 — token synthesizer** — `design_system.py`; role-based DTCG tokens,
  AA-gated, zoom-safe scale, archetype↔genre bridge; `concept_statement` is a real field.
- [x] **Phase 2 — motion + WebGL** — GSAP/Lenis choreography + Three.js shader
  aurora tinted by `--accent`; lazy-split, reduced-motion safe; verified live.
- [x] **Phase 3 — block library + composer** — 5 art-directed Astro blocks +
  `blocks_composer.py`; varied per-archetype layout, verified end-to-end.
- [x] **Phase 4 — imagery pipeline** — `imagery.py` + `generate_imagery.py`; cohesive
  briefs, provenance + founder clearance gate wired into `premium_ready`.
- [x] **Phase 5 — reference analyzer** — `reference_params.py` + `analyze_reference.py`;
  structured vision read folded into a build spec.
- [x] **Phase 6 — quality loop + Gemini judge** — `design_loop.py` (builder≠judge,
  gate-not-gradient, calibration, sign-off) + `gemini_judge.py` + CLI.

74 unit tests green; the full stack verified with a real `npm` build, web-gate
pass, and live WebGL screenshot. Remaining before a real client build: live Gemini
runs (imagery generation + the judge) need `GEMINI_API_KEY`; per-build copy is still
the build agent's job (the composer provides serviceable placeholders).

## What already exists to build on

- `packages/web/design_studio.py` — packet + `review_visual_quality`.
- `scripts/agency/design_studio.py` — `packet`/`shoot`/`review`/`status`/`guard`.
- `packages/web/design_reference/visual_rubric.md` — the 0–5 fitness function.
- `packages/web/palette.py` — WCAG contrast + genre table + HSL synth (the color engine).
- `scripts/web/shoot.mjs` — desktop+mobile full-page capture.
- `docs/products/better-business-web/concept-led-imagery-playbook.md` — the manual imagery pipeline.

---

## Phase 0 — Premium build stack *(the foundation everything plugs into)*

**New:** `packages/web/scaffold/astro-premium/` (a second, premium scaffold template).

Stand up a dedicated premium surface — **Astro (static-first shell) + interactive
islands + a motion layer**:

- **Astro** for structure, routing, SSG, and clean Netlify deploys (reuses the
  existing validation + deploy lanes).
- **Islands** (framework-agnostic; vanilla/Solid for weight, React only if a block
  needs it) for the interactive/WebGL pieces — heavy JS ships only where used.
- **Motion deps** wired but tree-shakeable: GSAP + ScrollTrigger, Lenis (smooth
  scroll), Three.js (lazy-loaded, hero-only).
- The **role-based design-token contract** (Phase 1) is the theme layer; the stack
  reads it, never hard-codes color/type.

**Why a new surface and not path B/C:** path B (hand-built single HTML) maxes
art-direction freedom but can't carry choreographed motion/WebGL or an automated
loop; path C (current scaffold) is a generic static page. The premium stack is the
home for the block library, motion system, and loop. Cold-outreach demos keep
using path B/C untouched; **good bespoke demos migrate up** to the premium stack
over time.

**Definition of done:** `astro-premium` builds to `dist/`, passes the existing web
gate, ships zero JS on a no-island page, lazy-loads Three.js, and renders a
reduced-motion-safe baseline.

## Phase 1 — Design System Synthesizer *(deterministic, hardened)*

**New:** `packages/web/design_system.py` (+ tests). **Consumes** a real
`concept_statement` (see below). **Calls** `palette.py` (does not reimplement it).

- **Concept as structured input** *(review fix)*: add `concept_statement` +
  optional `concept_palette`/`concept_type` cues to the packet spec
  (`request_from_spec`) and `WebsiteDesignRequest`. Founder *or* agent supplies the
  one-liner ("precision you can see; the calm craftsman"); falls back to the
  derived string when absent. This is the field that drives tokens, imagery, and
  motion — it must be suppliable, not fabricated.
- **Role-based tokens, two tiers** *(review fix)*: emit **primitive → semantic**
  tokens in **W3C DTCG format** (`$value`/`$type`), built to CSS via Style
  Dictionary. Semantic roles: `canvas`, `ink`, `accent`, `accent-strong`,
  `display-font`, `body-font`, `type-ratio`, `space-unit`, `radius`, `elevation`.
  The contract is the **role set**, so the premium stack and any migrated bespoke
  build read the same vocabulary.
- **Color** delegates to `palette.py` (`derive_palette`, `passes_aa`); add an
  **archetype↔genre bridge** so the studio's archetypes can use `GENRE_PALETTES`.
  Gate on WCAG 2.x AA; **APCA Lc advisory** for the dark/metal premium palettes.
- **Type**: premium pairing that escapes the genre default + a modular scale;
  **zoom-safe fluid `clamp()`** (rem+vw preferred term, rem min/max, body ≥1rem) —
  a hard **WCAG 1.4.4 / 1.4.12 test**, not taste *(review fix)*.
- **Signature treatments** (grain, gradient mesh, glow, hairlines) as opt-in,
  archetype-selected token layers.

**Definition of done:** same packet → byte-identical `tokens.json`; palette AA-valid
via `palette.py`; type scale monotonic + zoom-safe (tested at 200%); DTCG schema
validates; emits the `astro-premium` theme.

## Phase 2 — Motion & Interaction System *(the Awwwards gap closer)*

**New:** `packages/web/scaffold/astro-premium/src/motion/` (island components +
presets) + motion tokens in the synthesizer.

- **Scroll choreography:** Lenis smooth scroll + GSAP ScrollTrigger timelines;
  staggered hero reveals, pinned sections, parallax — all behind
  `prefers-reduced-motion` with a fully-visible fallback (the shoot pipeline
  already runs reduced-motion).
- **WebGL/3D hero kit:** Three.js scenes + shader backdrops as a lazy-loaded
  island, used for hero moments only; static poster fallback for reduced-motion
  and capture.
- **Motion presets** keyed by archetype/concept (`cinematic`, `editorial-calm`,
  `product-precise`…) so the synthesizer picks a motion direction, and blocks
  consume it as a token — motion is *designed*, not ad-hoc.

**Definition of done:** each preset has a reduced-motion fallback; WebGL lazy-loads
and never blocks first paint; Lighthouse perf stays within an agreed budget; the
shoot pipeline captures a clean static frame.

## Phase 3 — Premium Block Library *(authored once, in the premium stack)*

**New:** `packages/web/scaffold/astro-premium/src/blocks/` + a composer.

Because we committed to **one** premium surface, blocks are authored **once** as
Astro/island components over Phase-1 tokens + Phase-2 motion — no dual-surface
fork. Initial set: `cinematic-hero` (WebGL option), `bento-gallery`,
`editorial-split`, `device-frame-proof`, `service-area-map`, `sticky-process`,
`marquee-proof`, `editorial-cta`. A **composer** assembles a page from blocks by
archetype, fills them with evidence + imagery + tokens.

- Blocks read **only** role tokens (no hard-coded color — grep-testable).
- Each block is responsive at both capture viewports and recomposed (not just
  reflowed) on mobile.

**Definition of done:** every block renders valid HTML, passes the web gate +
a11y, consumes only tokens, and round-trips through the composer; the composer
produces a buildable `astro-premium` site from a packet + manifest.

## Phase 4 — Concept-Led Imagery *(top-tier generated pipeline)*

**New:** `packages/web/imagery.py` + `scripts/agency/generate_imagery.py`
(subcommands `brief` / `generate` / `select` / `optimize`).

Promote the imagery playbook into a production pipeline (Gemini "Nano Banana Pro"):

1. **brief**: concept → hero + supporting-set briefs with a shared style spec.
2. **generate**: **reference-anchored (up to 14 ref images) + fixed seed + shared
   style suffix** *(best-practice fix — cohesion comes from refs+seed, not suffix
   alone)*.
3. **select** *(agent-native fix)*: a real subcommand — agent/operator reads the
   PNGs against the concept and records survivors:
   `generate_imagery.py select --target <dir> --keep <ids.json|->`. The loop
   (Phase 6) supplies an agent-chosen keep-set with a `--auto-curate` top-N
   default so unattended runs converge.
4. **optimize**: webp + write `design-studio/imagery-manifest.json`.

**Provenance + clearance** *(review fix, honoring the founder's prod decision)*:
every manifest asset carries `provenance` (`generated`|`owner`|`licensed`) and
`production_clearance` (`bool` + who/when). Generated assets are allowed on
production, but the deploy guard (`premium_ready`) is extended to **require a
founder clearance waiver** for each `generated` asset on a real client go-live —
logged, not silent. The legal posture (generated imagery is non-copyrightable per
USCO 2025 and SynthID-watermarked) is recorded in the playbook so the choice is
always informed.

**Definition of done:** manifest schema validates; all assets webp under a size
budget; provenance present on every asset; the clearance gate blocks an uncleared
generated asset from a client go-live.

## Phase 5 — Reference Analyzer *(vision → structured params)*

**New:** `scripts/agency/analyze_reference.py`.

`analyze_reference.py --image <path|url> --out reference-params.json` — an agent
vision-reads a chosen Dribbble/Awwwards shot and the subcommand persists structured
params (palette hexes, type-scale ratio, density, grid, hero structure, **motion
cues**) that feed the Phase-1 synthesizer, Phase-2 motion presets, and the packet's
`references[].takeaways`. Built as a primitive the loop can call, not a manual step.

**Definition of done:** emits a validating `reference-params.json` the synthesizer
consumes; degrades gracefully (writes partial params, never crashes the loop) when
vision is low-confidence.

## Phase 6 — Quality Loop with Independent Judge *(the guarantee)*

**New:** `scripts/agency/design_loop.py`. **Orchestrates**, never duplicates —
calls the existing `shoot`/`review` subcommands.

```
packet(+concept) → tokens(P1) → motion preset(P2) → compose blocks(P3)
→ generate+select imagery(P4) → build astro-premium → shoot(done)
→ JUDGE → if fail: revision brief → revise → repeat → on pass: FOUNDER SIGN-OFF
```

- **Builder ≠ judge** *(P1 review fix)*: Claude builds; the visual judge is a
  **different model family (Gemini vision)** scoring screenshots against
  `visual_rubric.md`. Kills self-preference contamination.
- **Gate, not gradient** *(P1 review fix)*: keep the hard floors (every category
  ≥4, criticals fail on a single 3) + an explicit **iteration cap**. The loop
  *proposes*; on pass it **stops and requests founder sign-off** before any client
  ship. Never auto-hill-climbs the number.
- **Calibration harness** *(gives the taste-memory set a real job)*: a
  **gold-standard set** (our best shipped builds + reference records, scored) is
  re-scored each run; if the judge rates known-good lower / known-bad higher, it
  has drifted → halt + recalibrate. Stored anonymized under
  `products/better-business-web/portfolio/` + `docs/` (**never** runtime `state/`).
- **Revision-brief contract** *(spec-flow fix)*: on fail, `design_loop.py` hands
  the revise agent `{failing categories + notes + packet + build path +
  screenshots}`; the agent returns token deltas / block swaps / motion changes (for
  the premium stack these are *parametric* — the loop can re-synthesize and
  recompose, so revision is real, not hand-rebuild).
- **Termination & failure contract** *(spec-flow fix)*: on non-convergence, ship
  the **best-scoring iteration** for founder decision; on Gemini API failure
  (judge or imagery), degrade to existing/owner imagery + flag for human review
  rather than hard-fail; honor a token/cost budget on direct runs (not only under
  Workflow).

**Definition of done:** loop runs packet→pass on the premium stack; judge is a
non-Claude model; calibration halts on judge drift; non-convergence surfaces the
best build; founder sign-off is required before client deploy.

---

## Sequencing & dependencies

0 (stack) → 1 (tokens) → 2 (motion) → 3 (blocks) → 4 (imagery) → 5 (reference) → 6 (loop).

Each phase is independently demoable: after P1 you can theme the stack; after P2 a
hero moves; after P3 you can compose a full premium page by hand; P6 automates the
convergence. P5 (reference analyzer) can land any time after P1. P6's *automation*
only has teeth once P1+P3 make revision parametric — until then the loop runs as
the **agent-guided** loop already written into the `design-studio` skill.

## Cross-cutting: taste memory

The gold-standard set is no longer an orphan — Phase 6's calibration harness reads
it. Build it alongside P6: anonymized scored records of our best builds + the
Dribbble/Awwwards references, under the BBW portfolio + `docs/`.

## Non-goals

- Not touching the cold-outreach demo path (B/C) — the premium stack is the opt-in
  track; routine demos stay cheap.
- Not auto-shipping a client site on judge score alone — founder signs off.
- Not claiming generated imagery is copyrightable — it's used by informed choice
  with provenance + clearance logged.

---
---

# (v1 — superseded, kept for history)

The original "semi-automate cheaply" framing and its 5-phase outline lived here.
It was replaced by v2 above after the multi-agent review and the founder's
capability-over-thrift decision (2026-06-08). v1's core ideas survive in v2; what
changed: a dedicated premium stack instead of dual-surface retrofitting, motion +
WebGL elevated to a first-class phase, imagery hardened to a production pipeline
with provenance, and the loop given an independent judge + calibration harness.
