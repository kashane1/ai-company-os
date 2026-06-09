---
status: open
change_id: design-engine-external-authoring
owner: kashane
last_reviewed: 2026-06-09
related_plan: docs/plans/2026-06-08-feat-design-engine-v3-premium-loop-plan.md
---

# Design Engine — external authoring pipeline (widen the design space with Stitch & Figma)

> **TL;DR.** v3 closed the autonomous loop (build→judge→revise) but its builder is
> **template-parametric**: a fixed block set in `blocks_composer.py` plus revision
> by archetype/hue rotation (`premium_build.py:84`). No matter how good the Gemini
> judge is, the loop can only converge to the best point *inside a bounded design
> space*. **To raise the ceiling you widen the generator, not the judge.**
>
> This plan adds an **authoring-time** pipeline that uses external design tools to
> grow a **curated block library** the autonomous loop then searches. The safe
> shape is three roles: **external tool = novelty** (break out of the template
> set), **Claude = normalization** (rewrite harvested markup into tokenized Astro
> blocks that consume our design system), **the existing judge = admission gate**
> (a *block tournament* — render each candidate, score it against
> `visual_rubric.md`, admit only blocks that already clear the bar). The thing we'd
> normally fear — generic AI output — becomes the filter, because the rubric's
> `ai_house_style` penalty rejects it.
>
> **Verified surfaces (2026-06-09):** **Claude (GA)** is the in-pipeline spine — it
> normalizes every harvested design into tokenized Astro and seeds a baseline of
> candidates. **Stitch** is the external idea-generator: it has a real SDK
> (`@google/stitch-sdk`) but it's **v0.1.x experimental** ("not an officially
> supported Google product") → keep it *behind an adapter, assume it can vanish*.
> **Figma** is the *curated-library + token source-of-truth*: Dev Mode MCP (beta) +
> REST `/variables/local` (**Enterprise-gated** — a real constraint) + Builder.io
> Visual Copilot CLI for Figma→code.
>
> **Two tiers** (decided): **fleet** = autonomous, searches the curated library, no
> per-build external calls; **premium** = opt-in, human-assisted Figma curation OK,
> plus an optional runtime Claude seed. Sequel to
> [the v3 premium-loop plan](2026-06-08-feat-design-engine-v3-premium-loop-plan.md).

---

## 0. Why this plan exists — the decision already made

Brainstorm outcome (2026-06-09): **widen the design space at authoring time**, run
**both tiers**. This plan is the execution spec for that branch. It does **not**
re-litigate runtime-per-prospect generation (deferred to premium tier, §6) and does
**not** fork the `astro-premium` substrate — it feeds it.

The core principle, restated so every phase honors it:

> **External tools widen. Claude normalizes. The judge admits. Nothing un-judged,
> un-tokenized, or un-cleared enters the library.**

---

## 1. Ground truth — the ceiling is the bounded template space

| # | Finding | Evidence |
|---|---------|----------|
| 1 | The builder is template-parametric. Composition draws from a fixed per-archetype `_VARIANTS` set selected by concept-hash. | `packages/web/blocks_composer.py:113` (`plan_composition`), `_VARIANTS` |
| 2 | "Revision" is parametric, not generative — rotate archetype, rotate hue 47°, sharpen the concept line. It re-skins; it cannot invent a new layout. | `packages/web/premium_build.py:84` (`apply_brief`) |
| 3 | The block vocabulary is finite and hand-authored. | `CinematicHero, EditorialSplit, BentoGallery, StickyProcess, FullBleedMedia, ClosingCta` in `packages/web/scaffold/astro-premium/` |
| 4 | The judge + gate are strong and reusable as a fitness function. | `gemini_judge.py:156`, `design_studio.py:232` (`review_visual_quality`), `design_reference/visual_rubric.md` |
| 5 | Provenance/clearance is already a solved pattern we can mirror for blocks. | `packages/web/imagery.py` (`ImageryManifest`, `production_clearance`), `_stage_images` at `premium_build.py:207` |

**Conclusion:** the loop is a good *search*. It needs a *bigger, pre-vetted space*
to search. That space is a curated block library.

---

## 2. Verified tool surfaces (what is actually shippable)

Full report + sources in §11. Load-bearing facts:

| Tool | Real API? | Output | Maturity | Use it for | Biggest risk |
|---|---|---|---|---|---|
| **Claude** (Messages API) | Yes — GA, TS + Python | code (React/Tailwind/Astro) | GA | **in-pipeline spine** — normalize + baseline generate | none major; curation quality is on us |
| **Google Stitch** (`@google/stitch-sdk` + MCP) | Yes — **v0.1.x experimental** | HTML + screenshots (SDK); Figma + Tailwind (UI) | experimental | **idea generator behind an adapter** | Labs product can be killed/rewritten; free-tier data-use clause |
| **Figma Dev Mode MCP** | Yes — **beta** | `get_design_context` (React+Tailwind), `get_variable_defs` (tokens), `get_screenshot` | beta | premium curation + token read | MCP beta→paid |
| **Figma REST** `/variables/local`, `/images` | Yes — GA | tokens JSON; node PNG/SVG | GA | **token source-of-truth** | **Variables read is Enterprise-gated** |
| **Builder.io Visual Copilot CLI** | Yes — CLI | Figma→code (many frameworks + Tailwind) | live | batch Figma→code path | per-vendor longevity |
| **shadcn registry** (`npx shadcn add <url>`) | CLI (deterministic) | curated components into repo | GA | **distribution/curation layer** | not generative |

**Design implications:**
1. Build the spine on **Claude** (GA, clean, in-pipeline) for normalization and a
   baseline of candidates. Treat **Stitch** as the experimental external idea-
   generator — isolate behind a generator adapter, never load-bearing.
2. **Figma tokens require Enterprise.** Do **not** block the pipeline on it: ship a
   manual `tokens.json` fallback; light up the REST path only if/when Enterprise is
   confirmed (Phase 0 question).
3. **shadcn registry** is the cleanest deterministic *distribution* primitive — the
   final hand-off layer for admitted blocks, regardless of which generator fed them.

---

## 3. Architecture — block library + tournament

### 3.1 Block Library registry (mirror the imagery manifest)

New module `packages/web/block_library.py`, manifest at
`state/design-studio/block-library/manifest.json`:

```
blocks: [
  { id, component_path, archetype_affinity: [...],
    source: claude|stitch|figma|hand,
    license,                       # provenance for ToS/commercial clearance
    judge_score,                   # admission score (from the tournament)
    admitted_at,
    tier: fleet|premium,
    cleared: bool }                # mirrors imagery production_clearance
]
```

This is deliberately the same shape as `ImageryManifest` so the clearance/provenance
discipline (and the operator's mental model) carry over unchanged.

### 3.2 The composer reads the registry

`plan_composition` (`blocks_composer.py:113`) selects variants from the registry
filtered by `archetype_affinity ∩ requested archetype` and `tier`, **falling back to
today's hardcoded `_VARIANTS`** when the registry is empty. → zero behavior change
on day one; the registry becomes the new, growable source of variants.

### 3.3 The block tournament (judge-as-admission)

```
generate (N candidates, multi-generator)
   → normalize (Claude → tokenized Astro BlockSpec)
   → render (harness page → shoot.mjs screenshot)
   → judge (gemini_vision_judge vs visual_rubric.md)
   → admit top-K (critical categories ≥4, no ai_house_style fail)
```

The admission test **is** the production fitness function. The library can only grow
with blocks that already pass — self-compounding, and structurally resistant to AI
house style.

### 3.4 Tiers (the `tier` tag does the work)

- **fleet** — broadly-validated, judge-admitted, cheap to compose; every cold build
  searches this set. **No external calls at build time.**
- **premium** — higher-craft blocks (more motion, bespoke sequences), some hand-
  finished in Figma; gated to the opt-in premium track
  (`scripts/agency/design_studio.py`); same loop, same judge, richer library +
  higher `min_overall`. Optional runtime Claude seed (§6).

---

## 4. File-level changes (injection points)

| Area | Change | Anchor |
|---|---|---|
| Registry | new `packages/web/block_library.py` (manifest, load/filter, admit) modeled on `imagery.py` | `packages/web/imagery.py` |
| Composer | `plan_composition` reads registry, falls back to `_VARIANTS` | `blocks_composer.py:113` |
| Harness | new `scaffold/astro-block-harness/` — render one `BlockSpec` on neutral tokens | `scaffold/astro-premium/` |
| Tournament CLI | `design_loop.py block-gen` / `block-tournament` / `block-admit` | `scripts/agency/design_loop.py` (`run`/`judge`/`calibrate`) |
| Generators | new `packages/web/generators/` — common `generate(prompt, archetype)`; adapters: `claude` (baseline), `stitch` (flagged) | new |
| Normalizer | Claude sub-agent: raw HTML/TSX → tokenized Astro block consuming `--color-*/--space-*/--type-*` | reuses build sub-agent pattern from v3 §4 |
| Judge reuse | tournament calls `gemini_vision_judge` unchanged | `gemini_judge.py:156` |
| Tokens (premium) | Figma REST `/variables/local` → `tokens.json` → feed palette/type | `design_system.py:203-216` |
| Clearance | block `cleared` gate before a block ships, mirroring imagery | `imagery_cleared()`, `deploy.py` |

**Edit-boundary note (CLAUDE.md):** anything touching `packages/schemas/`,
`skills/canonical/`, or `skills/registry.yaml` needs **founder approval**. The block
manifest schema and any new skill wiring fall here — call it out in the PR, don't
self-merge.

---

## 5. Phases & definition-of-done

**Phase 0 — Decisions & access (gate before code).** Answer the §8 questions; put
keys in env (`STITCH_API_KEY`, `FIGMA_API_KEY`) via the repo's secret handling.
**DoD:** written decisions on Figma ingestion path, Figma tier, budget; keys present
or explicitly deferred.

**Phase 1 — Registry + contract (no external calls).** Build
`block_library.py`; composer reads it with `_VARIANTS` fallback; seed the registry
from today's blocks. **DoD:** premium loop is byte-for-byte unchanged with the
seeded registry; tests cover load/filter/fallback.

**Phase 2 — Tournament + admission (candidates from Claude only).** Harness page +
`block-tournament`/`block-admit`; admission uses the live rubric thresholds.
**DoD:** N Claude-generated candidates → scored → top-K admitted with provenance;
admission honors critical-category floor + `ai_house_style`.

**Phase 3 — Normalization adapter.** Claude rewrites raw markup → tokenized Astro
block. **Golden test:** judge candidate *before* and *after* normalization; fail if
score drops > tolerance (adapter flattened the idea). **DoD:** a raw generated
component becomes a tokenized block that builds and scores within tolerance.

**Phase 4 — External generators behind adapters.** `generators/` with `claude`
(baseline) and `stitch` (feature-flagged, isolated). **DoD:** one command generates
~20 candidates across both generators for the **two weakest archetypes**, tournaments
them, admits ~6; loop pass-rate measured before/after.

**Phase 5 — Figma tokens + premium curation.** REST `/variables/local` →
`tokens.json` → `design_system.py` (premium, brand-locked); premium-tier blocks
hand-finished in Figma via Builder.io CLI / Dev Mode MCP → normalizer → registry
`tier=premium`. **DoD:** a premium build sources brand tokens from a Figma file and
composes ≥1 premium-tier block. *Gated on Enterprise; manual `tokens.json` fallback
ships regardless.*

**Phase 6 — Measurement & compounding.** Instrument first-iteration pass-rate, score
variance, block-usage distribution; diversity guard flags single-block dominance.
**DoD:** a before/after metrics report on a fixed prospect set.

---

## 6. Premium runtime lane (forward pointer, not in scope here)

Because the seams are identical, the per-prospect path — **Claude (or Stitch)
generates a bespoke layout → Claude normalizes → seeds the loop at iteration 0** — is
a *small addition* later, not a rebuild. Deferred deliberately: it adds per-build
cost, latency, and nondeterminism that conflict with the fleet's checkpoint/resume
design. Premium-only, budget-guarded, opt-in.

---

## 7. Provenance, licensing & ToS (do not skip)

- **Per-block `source` + `license`** recorded at admission; **`cleared` gate** before
  any block ships, mirroring `imagery_cleared()`. No un-cleared block deploys.
- **Free-tier data-use:** Stitch (governed by Gemini Labs terms) **may train on
  prompts/outputs** on its free tier. For a commercial library, prefer the **paid
  tier**, or lean on Claude (clean terms); confirm which tier the Stitch key lands on
  (Phase 0).
- **No IP indemnity** at the standard Stitch tier; generated output may overlap with
  third-party IP. The tournament + human curation + `ai_house_style` penalty are the
  practical guardrails; a legal pass precedes first commercial ship.

---

## 8. Decisions needed (Phase 0)

1. **Figma ingestion path:** Dev Mode MCP (`get_design_context` / `get_variable_defs`)
   or Builder.io Visual Copilot CLI for batch Figma→code? *Recommend: Dev Mode MCP
   first (we already run MCP clients here), add the Builder.io CLI if batch volume grows.*
2. **Figma tier:** do we have / want **Enterprise** (required for Variables REST)?
   *If no: ship the manual `tokens.json` fallback; defer the REST path.*
3. **Budget per authoring run** (caps generator calls). *Recommend a per-run token/credit ceiling mirroring the loop's `BudgetGuard`.*
4. **Stitch in or out of v1?** *Recommend behind a feature flag, off by default, given v0.1.x risk.*

---

## 9. Risks & mitigations

| Risk | Mitigation |
|---|---|
| Stitch (v0.1.x) vanishes / breaks | Isolate behind a generator adapter; never load-bearing; feature-flag off by default |
| Figma Variables Enterprise-gated | Manual `tokens.json` fallback; REST path optional |
| AI house-style homogenization | Tournament admission + multi-generator sourcing + prompt diversity + rubric `ai_house_style` penalty + Phase-6 diversity guard |
| Normalizer flattens the idea | Golden before/after judge test (Phase 3) |
| Cost / nondeterminism in the fleet | Authoring-time only for fleet; pin SDK versions; budget guard |
| ToS / IP exposure | Per-block license/source, `cleared` gate, prefer paid tiers, legal pass before commercial ship |
| Edit-boundary violations | Founder approval for schema/skills/registry changes |

---

## 10. Definition of done (overall)

The autonomous fleet loop composes from a **judge-admitted, provenance-tracked block
library** that is **measurably wider** than today's `_VARIANTS` (first-iteration
pass-rate ↑, block-usage diversity ↑), with a **repeatable authoring command** that
generates → normalizes → tournaments → admits new blocks, **no external calls at
fleet build time**, and a **premium tier** that can source Figma brand tokens and
premium-only blocks — all without forking `astro-premium` and without shipping any
un-cleared block.

---

## 11. References (verified 2026-06-09)

- Stitch SDK — https://github.com/google-labs-code/stitch-sdk · https://www.npmjs.com/package/@google/stitch-sdk · MCP: https://stitch.withgoogle.com/docs/mcp/setup/
- Gemini API terms (govern Stitch output) — https://ai.google.dev/gemini-api/terms
- Figma MCP — https://developers.figma.com/docs/figma-mcp-server/tools-and-prompts/ · Variables REST — https://developers.figma.com/docs/plugins/working-with-variables/ · Make — https://www.figma.com/make/
- Builder.io Visual Copilot CLI — https://www.builder.io/blog/visual-copilot-cli
- shadcn registry (deterministic distribution layer) — `npx shadcn add <url>`

---

## 12. Execution status (2026-06-09)

All six phases implemented test-first behind injected adapters (external keys touched
only at authoring time), 46 unit tests, committed phase by phase on
`feat/design-engine-external-authoring`. v0 dropped per founder decision; generators
are Claude (baseline) + Stitch.

| Phase | Module(s) | Status |
|---|---|---|
| 1 Registry | `block_library.py`, composer wiring | ✅ done — builtin-seeded compose is byte-identical |
| 2 Tournament | `block_tournament.py`, `block_harness.py`, `block_studio.py` | ✅ done (pure core tested; live render needs npm+Chromium) |
| 3 Normalizer | `block_normalizer.py` | ✅ done + **proven live** (Claude: 261-line hero, 49 token refs, 0 hex, 0 Tailwind) |
| 4 Generators | `block_generators.py`, `block_studio.py gen` | ✅ Claude path proven live end to end; Stitch **auth + generation proven live**, but the live get-screen/HTML response shape differs from the SDK source — mapping that is the one open item (Stitch stays behind a flag, off by default) |
| 5 Figma tokens | `figma_tokens.py`, `block_studio.py figma-tokens` | ✅ done — free key authorizes `/v1/me`; Variables REST is Enterprise-gated as predicted; manual `tokens.json` fallback proven live |
| 6 Metrics | `library_metrics.py`, `block_studio.py metrics` | ✅ done |

**Proven against the real free accounts (used sparingly):** the Stitch free key
authorizes the MCP API (initialize + create_project + generate all succeed); the
Figma free key authorizes the REST API. **Not yet usable on free tiers:** Figma
Variables REST (Enterprise — fallback covers it); full Stitch HTML extraction (one
response-shape mapping pass remains).

**Open follow-ups:** (a) map Stitch's live `get_screen` HTML/screenshot fields;
(b) wire premium_build to *stage* cleared library blocks into the scaffold + layer
`tokens.css` (mirrors imagery staging); (c) skill/registry wiring for an operator
trigger (founder-approval boundary).
