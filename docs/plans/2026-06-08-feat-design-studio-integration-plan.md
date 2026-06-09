# Design Studio Integration Plan — make the premium lane usable

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to
> implement this plan task-by-task.

**Status:** proposed (awaiting founder approval — Task 4 touches `skills/canonical/`
and `skills/registry.yaml`, which are edit-gated).

## Context

`packages/web/design_studio.py` exists, is tested (6/6), and defines a sound
contract: `build_design_studio_packet()` and `review_visual_quality()`. But it is
an **island** — nothing in the repo imports it outside its own test and docs. The
prior plan ([2026-06-08-feat-web-design-studio-lane-plan.md](2026-06-08-feat-web-design-studio-lane-plan.md))
delivered the module (~30%). This plan delivers the remaining ~70%: the
integration that makes the module actually shape a build.

**Key product constraint (founder, 2026-06-08):** the Design Studio pass is a
**premium, opt-in track reserved for select builds** — a demo the founder feels
strongly about, or a paid client site. It is **NOT** run on every cold-outreach
demo. Therefore the design must be explicitly invoked, never a global gate that
taxes the high-volume prospect pipeline.

## Goal

After this plan, an operator can take one chosen build through:

```
mark premium → packet (persisted) → guided build → desktop+mobile screenshots
→ rubric scoring → visual review report (persisted) → gated deploy
```

…end-to-end, with the existing technical gates (`validate_web_dist`, `ux_audit`)
still running underneath, and the cold-demo path completely untouched.

## Architecture decisions

1. **Opt-in is signalled by artifact presence, not a flag everywhere.** A build
   joins the premium track when its packet is written to the site hub. No
   `packet.json` → the design-studio review simply does not apply. This keeps
   cold demos zero-cost.
2. **Per-build persistence under the existing hub.** For prospect demos (path B):
   `state/prospects/sites/<place_id>/design-studio/`. For client sites (path C):
   `products/<slug>-site/design-studio/`. The entrypoint takes the target
   directory, so both work.
   Contents: `packet.json` + `packet.md` (readable brief), `screenshots/{desktop,mobile}.png`,
   `scores.json` (rubric output), `visual-review.json` + `review.md`.
3. **The scorer is an agent following a written rubric.** `review_visual_quality()`
   consumes `VisualScore` objects; today nothing produces them. We add a rubric
   doc with anchored 0–5 descriptions, and the `design-studio` skill instructs the
   agent (or computer-use vision) to view the two screenshots and emit `scores.json`.
   No new ML infra — the judgment lives in the agent, the *discipline* lives in the
   rubric + the module's thresholds.
4. **One orchestration entrypoint** (`scripts/agency/design_studio.py`) ties
   packet → shoot → review → persist. The skill is the human/agent-facing wrapper;
   the entrypoint is the deterministic plumbing tests can cover.

---

### Task 1 — Orchestration entrypoint + persistence (TDD)

**Files:**
- Create: `scripts/agency/design_studio.py`
- Create: `tests/python/unit/test_design_studio_entrypoint.py`

**Subcommands:**
- `packet --target <dir> --spec <json|->` — build `WebsiteDesignRequest` from a
  spec, call `build_design_studio_packet`, write `design-studio/packet.json` +
  render `packet.md`.
- `shoot --target <dir> --dist <distDir>` — capture desktop + mobile full-page
  PNGs into `design-studio/screenshots/` (delegates to Task 5).
- `review --target <dir> --scores <json|->` — load `scores.json`, call
  `review_visual_quality` with the screenshot paths, write `visual-review.json` +
  `review.md`; exit non-zero if `passed` is false.
- `status --target <dir>` — print which premium-track artifacts exist and whether
  the build currently passes.

**Step 1 (RED):** tests assert — packet round-trips to JSON and back; `review`
writes a report and returns exit 1 when below threshold, exit 0 when passing;
`status` reports missing screenshots before `shoot` runs; path resolution works
for both a `state/prospects/sites/<id>/` target and a `products/<slug>-site/`
target.

**Step 2 (GREEN):** implement using `packages.web.design_studio` only — no
business logic duplicated in the script.

### Task 2 — Visual rubric (turns screenshots into scores)

**Files:**
- Create: `packages/web/design_reference/visual_rubric.md`

Define the scored categories the module expects, each with anchored 0–5
descriptions (0 = generic/template, 5 = Dribbble/Awwwards-grade). Must include the
three the module marks **critical** (floor 4/5): `visual_thesis`, `hero_impact`,
`imagery_art_direction`. Add: `typography`, `composition_variety`, `polish_detail`,
`responsive_composition`, `copy_specificity`. Pull the anchors from the craft
language already in `state/prospects/sites/_scaffold/05-craft-pass.md` and
`docs/demo-site-learnings.md` so the rubric matches existing taste vocabulary.
Document the output shape (`scores.json` = list of `{category, score, note}`) so it
deserializes straight into `VisualScore`.

### Task 3 — Mobile-capable screenshots

**Files:**
- Modify: `scripts/web/shoot.mjs` (add `--width <px>` / viewport arg)
- Modify: `scripts/agency/screenshot_demo.py` (expose desktop + mobile presets)

`shoot.mjs` currently captures full-page at one width. The module **hard-requires**
desktop *and* mobile. Add a width argument (default desktop 1440; mobile preset
390) and emit deterministic filenames. Verify the existing review-gallery callers
are unaffected (width defaults to current behavior). Task 1's `shoot` subcommand
calls this twice (desktop, mobile).

**Step (verify):** run on one existing built demo and confirm two correctly-sized
full-page PNGs land in `design-studio/screenshots/`.

### Task 4 — `design-studio` skill (the opt-in wrapper) — **founder-gated**

**Files:**
- Create: `skills/canonical/design-studio/skill.md`
- Create: `skills/adapters/claude/design-studio.md`
- Modify: `skills/registry.yaml` (new entry; `kind: agentic`)
- Modify: `docs/skills-index.md` (trigger phrases)

The skill orchestrates the premium track and is invoked **only** when the operator
chooses to elevate a build (trigger phrases like "run the design studio on this",
"make this a premium build"). Procedure:
1. Confirm this is a select/premium build (the skill refuses to be the default).
2. Gather evidence + references → write the spec → `design_studio.py packet`.
3. Guide the bespoke (path B) or Astro (path C) build using the packet's concept,
   archetype, palette, type, imagery, and motion plans.
4. `design_studio.py shoot` → desktop + mobile.
5. Score against `visual_rubric.md` → write `scores.json` → `design_studio.py review`.
6. Iterate until the review passes; only then hand to the existing technical gates.

> Per `CLAUDE.md` edit boundaries, `skills/canonical/` and `skills/registry.yaml`
> require explicit founder approval — approving this plan covers it, but call it
> out at implementation time.

### Task 5 — Light opt-in pointers (don't tax the cold path)

**Files:**
- Modify: `skills/canonical/landing-page-build/skill.md` (one "Premium track" note)
- Modify: `docs/demo-site-build-playbook.md` (pointer at the craft-pass stage)
- Create: `state/prospects/sites/_scaffold/06-design-studio-pass.md` (optional stage)

Each addition is a *pointer*, clearly marked **optional / select builds only**, so
the default flows (cold-outreach demos) stay exactly as they are. The bespoke
playbook gains an optional stage 06 that says: "for a build you intend to elevate,
run the `design-studio` skill instead of stopping at 05-craft-pass."

### Task 6 — Optional deploy enforcement for premium builds

**Files:**
- Modify: `packages/web/deploy.py` (or the readiness policy it calls)
- Modify: relevant deploy test

Add a `require_design_studio` opt-in: when a build's hub contains a `packet.json`,
deploy refuses unless `visual-review.json` exists and `passed: true`. This means
**once you elect the premium track, you can't accidentally ship the un-reviewed
version** — but builds with no packet (every cold demo) are unaffected.

### Task 7 — End-to-end verification on a real demo

**Steps:**
1. `pytest tests/python/unit/test_web_design_studio.py test_design_studio_entrypoint.py -q`
2. `ruff check scripts/agency/design_studio.py tests/python/unit/test_design_studio_entrypoint.py`
3. Dry-run the full track against one existing built demo (e.g. the TrueLine
   plumbing or Lumière nails `dist-v2/`): packet → shoot → score → review, and
   confirm artifacts land under that business's `design-studio/`.
4. Confirm a deliberately-weak fixture **fails** the review (the whole point: a
   valid-but-generic page is rejected).
5. `git diff --check`.

## Definition of done

- One command sequence (or the `design-studio` skill) takes a chosen build from
  packet → review, persisting every artifact under the build's hub.
- The visual review is producible by an agent from a written rubric — no manual
  guessing of score shape.
- Desktop **and** mobile screenshots are captured automatically.
- A premium-flagged build cannot deploy without a passing review (Task 6).
- The cold-outreach demo path is byte-for-byte unchanged.
- All tests + ruff green; verified on at least one real existing demo.

## Explicitly out of scope

- Automating *taste* (the agent still makes the design; the system enforces
  discipline and memory).
- Wiring into `apps/worker-web` autonomous runs — premium builds are
  operator-initiated by design.
- Rebuilding the bespoke or Astro build surfaces themselves.
