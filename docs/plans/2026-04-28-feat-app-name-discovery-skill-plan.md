---
title: App Name Discovery Skill
type: feat
status: completed
date: 2026-04-28
origin: docs/brainstorms/2026-04-28-app-name-discovery-skill-brainstorm.md
---

# App Name Discovery Skill

## Enhancement Summary

**Deepened on:** 2026-04-28
**Sections enhanced:** Technical Approach (rubric, archetypes, fixtures), Acceptance Criteria, Future Considerations
**Research agents used:** Explore (skill-estate prior art), best-practices-researcher (Igor / Lexicon / Altman naming frameworks), pattern-recognition-specialist (estate consistency)

### Key Improvements
1. **Canonical skill.md must use the established 5-section shape** — Purpose / Contract / Allowed edit boundaries / Forbidden areas / Instructions — not improvised headings.
2. **`contract.yaml` uses the canonical inputs/outputs schema** (mirrors `niche-research-brief`, `gtm-artifact-refresh`), not a bespoke rubric block. Rubric definitions live inside `skill.md`.
3. **Ship `fixtures/happy_path.yaml`** so the skill registers as `fixture_status: passing` from day one — matching every recently-added agentic skill in the registry. Fixture freezes the contract, not test outcomes.
4. **Registry entry adds `self_evolvable: false`** per the 2026-Q2 convention all post-ECC-batch skills follow.
5. **Distinctiveness weight raised 1.5 → 2.0** (Lexicon/Igor research: distinctive names become memorable; the inverse is not true).
6. **"Visual / icon potential" reframed as "App Store fitness"** — same slot, expanded to include 30-char display limit, ASO discoverability, voice-search uniqueness, icon coherence at 60pt.
7. **Sixth archetype: Lexical / Real-word** (Slack, Square, Block) — dominant in modern app names; matrix becomes 4 × 6 = 24 cells × 8 candidates ≈ 192.
8. **Secondary hard gate: App Store exact-match collision** — Apple won't approve, so it's auto-reject regardless of other scores.

### New Considerations Discovered
- Trademark hard-fail should be threshold-aware: 1/5 only for same-class conflicts; 2/5 triggers mandatory legal review rather than auto-rejection. Captured as a refinement to the gate description.
- The brainstorm explicitly locked "Full 8" rubric. Three dimensions surfaced by industry frameworks (Depth/Meaning capacity, Extensibility/Future-proofing, Strategic-story fit) are deferred to Future Considerations rather than added unilaterally.

## Overview

Add a new canonical skill — `app-name-discovery` — that consumes an existing founder pack at `docs/products/<product-id>/` and produces a scored matrix of candidate app names organized by emotional register × naming archetype, plus a defensible shortlist. The skill is product-agnostic; the "life clock" iOS app is the first test case (executed in a follow-up step, not in this plan's scope).

The skill ships with full estate wiring per `skills/WIRING.md`: canonical source-of-truth + Claude adapter + project-skill pointer + registry entry + `CLAUDE.md` trigger phrases.

## Problem Statement / Motivation

Naming an app is the most-reused early-product decision and the most often done by gut. Every product after life-clock will need it. Without a written rubric and a forced spread across registers/archetypes, founders converge on one feel before they've felt the alternatives. This skill turns naming into a repeatable, version-controlled artifact: the founder still picks, but the picking is honest and the rejected branches are visible.

The skill joins the founder-pack-consuming family alongside `app-store-positioning-pack` and `gtm-artifact-refresh` — pre-positioning, post-product-brief.

## Proposed Solution

A canonical skill that, given a `product-id`:

1. Loads the founder pack (`founder-brief.md`, `product-brief.md`, `brand-guidelines.md`, `competitive-analysis.md`, plus optional positioning doc) and aborts if any required file is missing.
2. Captures git SHA of the product directory + path for reproducibility.
3. Generates candidate names across a 4×6 matrix: **registers** (Stark, Calm, Sharp, Playful) × **archetypes** (Descriptive, Evocative, Invented, Metaphor, Compound, Lexical), 8 candidates per cell (~192 total).
4. Applies a **cross-language safety hard gate** — any candidate scoring 1/5 on cross-language safety is rejected before entering the matrix.
5. Scores every surviving candidate on the **Full 8 rubric** (1–5 with weights).
6. Produces a **shortlist of 5** that satisfies an **archetype-spread rule** (≥3 archetypes represented). Pure ranking is overridden if needed by swapping in the highest-scoring candidate from a missing archetype.
7. Writes output to `docs/products/<product-id>/naming/<YYYY-MM-DD>-candidates.md` with the matrix, shortlist (each marked `needs_verification: true`), and a discarded section explaining cultural-safety / generic rejections.

Availability checks (App Store, USPTO, domain) are **score-only, flag-for-manual** — the founder runs live verification on the shortlist.

(See brainstorm: [docs/brainstorms/2026-04-28-app-name-discovery-skill-brainstorm.md](docs/brainstorms/2026-04-28-app-name-discovery-skill-brainstorm.md))

## Technical Approach

### Files to create

- `skills/canonical/app-name-discovery/skill.md` — canonical definition. **Must use the established 5-heading shape**: `## Purpose` / `## Contract` (with Inputs + Outputs subsections) / `## Allowed edit boundaries` / `## Forbidden areas` / `## Instructions` (numbered phases). Rubric, weights, gates, and the spread rule live inside Instructions. Optional sections (Failure modes, Worked example, References) may be added but are not required by the fixture.
- `skills/canonical/app-name-discovery/contract.yaml` — uses the canonical inputs/outputs schema (mirrors `niche-research-brief/contract.yaml`). Fields: `inputs` (product_id, optional weight overrides) and `outputs` (path to candidates doc, shortlist size). **Rubric definitions do NOT live here** — they live inline in `skill.md`.
- `skills/canonical/app-name-discovery/output-template.md` — markdown template with YAML front-matter, matrix scaffold, shortlist scaffold, discarded-notes scaffold.
- `skills/canonical/app-name-discovery/fixtures/happy_path.yaml` — contract-freeze fixture asserting `required_input_fields`, `required_output_fields`, `required_section_headings` (the 5 canonical headings), and `required_forbidden_areas` (`apps/`, `packages/`, `infra/`, `state/`, `products/`).
- `skills/adapters/claude/app-name-discovery.md` — Claude runtime adapter. Frontmatter description + step-by-step adapter narrative (mirrors `gtm-artifact-refresh` adapter style).
- `.claude/skills/app-name-discovery.md` — thin discovery pointer per WIRING.md template. Frontmatter only references; body is the boilerplate "Read and follow the adapter" line.

### Files to modify

- `skills/registry.yaml` — append a new `app-name-discovery` entry. Fields: `id`, `name`, `path: canonical/app-name-discovery/skill.md`, `owner_agent: supervisor`, `target_runtimes: [claude]`, `stage: active`, `kind: agentic`, `fixture_status: passing` (fixture ships in v1 — see Files to create), `source: internal`, `self_evolvable: false`, `adapters.claude`, `project_skill`.
- `CLAUDE.md` — add the new skill to the bullet list under "Available Claude project skills" and add four trigger phrases under "Trigger phrases → skills":
  - `"find a name for this app"` / `"name this product"` / `"run name discovery"` / `"explore app names"` → `skills/adapters/claude/app-name-discovery.md`

### Rubric specification (lives in `skill.md` Instructions, not in `contract.yaml`)

```yaml
rubric:
  dimensions:
    - id: memorability
      weight: 1.5
    - id: pronounceability
      weight: 1.0
    - id: distinctiveness
      weight: 2.0          # raised from 1.5 per Lexicon/Igor research
    - id: positioning_fit
      weight: 2.0          # heaviest — must match the founder pack
    - id: availability_estimate
      weight: 1.0
    - id: trademark_risk
      weight: 1.0
    - id: cross_language_safety
      weight: 1.0           # also a hard gate at score == 1
    - id: app_store_fitness   # was visual_icon_potential — expanded scope
      weight: 1.5
      covers:
        - 30-character display limit (~12 chars before home-screen truncation)
        - ASO discoverability vs. keyword-stuffing rejection risk
        - Phonetic uniqueness for Siri / voice search
        - Icon coherence at 60pt wordmark
  scale: [1, 2, 3, 4, 5]
  hard_gates:
    - dimension: cross_language_safety
      reject_at: 1
      reason: "Chevy-Nova-class disasters auto-reject."
    - dimension: app_store_collision
      reject_on: "exact-match existing iOS app name"
      reason: "Apple won't approve duplicates."
    - dimension: trademark_risk
      reject_at: 1
      condition: "same-class conflict only"
      reason: "Adjacent-class friction (score 2) triggers mandatory legal review, not auto-reject."
  shortlist:
    size: 5
    spread_rule:
      min_archetypes: 3
```

Weights are defaults; per-product override lives in YAML front-matter on the output doc.

### Archetypes (6, expanded from brainstorm's 5)

1. **Descriptive** — Salesforce, JetBlue
2. **Evocative** — Patagonia, Amazon
3. **Invented / Coined** — Spotify, Kodak
4. **Metaphor** — Apple, Oracle
5. **Compound / Portmanteau** — Pinterest, Instagram
6. **Lexical / Real-word** — Slack, Square, Block (added per industry-naming research; dominant in modern apps)

### Output document shape

```markdown
---
product_id: <product-id>
generated_at: 2026-04-28
founder_pack_git_sha: <sha>
founder_pack_path: docs/products/<product-id>
rubric_weights: { ... }   # optional override
---

# App Name Candidates — <product-id>

## Shortlist (5)

| Name | Archetype | Register | Total | needs_verification |
| ... |

## Matrix

### Stark × Descriptive
1. <name> — M:5 P:4 D:3 PF:5 A:3 TM:3 CL:5 V:4 — total
...

## Discarded
- <name> — Reason: cross-language collision (German "..." means ...)
```

### Boundaries (canonical)

- **May edit:** `docs/products/<product-id>/naming/*.md` only.
- **Must not touch:** `apps/`, `packages/`, `infra/`, `state/`, `products/`, any other `docs/products/<product-id>/*` artifacts.
- **Read-only:** founder pack files.

## System-Wide Impact

- **Interaction graph:** Skill invocation is one-shot. No callbacks/middleware. Output is a single new markdown file. Downstream: `app-store-positioning-pack` is unaffected (it consumes positioning, not the candidates doc); a future founder workflow may pick the chosen name and write it back into `product-brief.md` — out of scope here.
- **Error propagation:** Missing founder pack file → fail fast with explicit list of missing paths. Empty matrix (all candidates gated out) → fail with the rejection log so the founder sees why.
- **State lifecycle risks:** None. Output is content-addressable by date; reruns produce a new dated file rather than mutating prior runs. No partial-write risk that matters.
- **API surface parity:** Trigger phrases must be added in `CLAUDE.md` AND the disambiguation rule must be respected — none of the 4 phrases collide with existing trigger phrases (verified against current `CLAUDE.md`).
- **Integration test scenarios** (covered manually in this plan; no automated fixtures in v1):
  1. Founder pack fully present → matrix + shortlist produced.
  2. Founder pack missing `competitive-analysis.md` → skill aborts with clear error.
  3. All Stark candidates fail cross-language gate → matrix shows empty Stark row, shortlist still satisfies spread rule from remaining 3 registers.
  4. Pure ranking would yield 5 Invented shortlist → spread rule swaps in #1 from two other archetypes.
  5. Per-product override in front-matter → skill respects custom weights.

## Acceptance Criteria

- [x] `skills/canonical/app-name-discovery/skill.md` exists with the canonical 5-heading shape: Purpose / Contract (Inputs+Outputs) / Allowed edit boundaries / Forbidden areas / Instructions.
- [x] Canonical `skill.md` Boundaries sections list both "Allowed edit boundaries" (`docs/products/<product-id>/naming/*.md`) and "Forbidden areas" (`apps/`, `packages/`, `infra/`, `state/`, `products/`, plus other `docs/products/<product-id>/*` artifacts).
- [x] `skills/canonical/app-name-discovery/contract.yaml` exists using the canonical inputs/outputs schema (no bespoke rubric block — rubric is inline in `skill.md`).
- [x] `skills/canonical/app-name-discovery/output-template.md` exists.
- [x] `skills/canonical/app-name-discovery/fixtures/happy_path.yaml` exists and asserts `required_input_fields`, `required_output_fields`, `required_section_headings` (the 5 canonical headings), and `required_forbidden_areas`.
- [x] `skills/adapters/claude/app-name-discovery.md` exists, mirrors the structure of `skills/adapters/claude/gtm-artifact-refresh.md`, and includes a Quick reference, Steps 1–N, and Boundaries section.
- [x] `.claude/skills/app-name-discovery.md` exists, contains only frontmatter + the standard 2-line WIRING boilerplate body, with no skill logic.
- [x] `skills/registry.yaml` has a new `app-name-discovery` entry with `target_runtimes: [claude]`, `kind: agentic`, `fixture_status: passing`, `self_evolvable: false`, `project_skill`, and `adapters.claude` set.
- [x] `CLAUDE.md` lists the skill under "Available Claude project skills" and registers all 4 trigger phrases.
- [x] No collisions: the 4 trigger phrases do not match any pre-existing trigger phrase in `CLAUDE.md` (manual grep confirms).
- [x] Cross-language safety is implemented as a **hard gate** (reject at 1/5), not just a low-weight dimension.
- [x] App Store exact-match collision is a secondary hard gate (auto-reject).
- [x] Trademark risk hard-fail is threshold-conditional: 1/5 only on same-class conflicts; 2/5 emits `legal_review_required: true` rather than rejecting.
- [x] Shortlist spread rule (≥3 archetypes out of 6) is described in the canonical skill with explicit override behavior.
- [x] All availability/trademark dimensions on the shortlist are flagged `needs_verification: true` in the output template.
- [x] Output path follows `docs/products/<product-id>/naming/<YYYY-MM-DD>-candidates.md` exactly.
- [x] Founder-pack git SHA + path are captured in the output doc front-matter; if the product dir has uncommitted changes, also set `dirty: true`.
- [x] Skill is product-agnostic — no string `life clock` or `life-clock` appears anywhere in the skill files.

## Success Metrics

- Skill can be invoked end-to-end on the next product without code edits — only a `product-id` argument.
- A founder reviewing the output can identify in <5 minutes which 1–2 candidates they want to verify externally.
- Every shortlist row has clear rationale tied back to founder-pack content (positioning fit ≥ 4/5 is enforceable on review).

## Dependencies & Risks

- **Dependency:** `docs/products/<product-id>/` founder pack must exist with the four required files. No new code dependencies.
- **Risk: Generation drift.** LLM-driven generation might over-index on one archetype (typically Invented) before the spread rule kicks in. Mitigation: the canonical skill explicitly instructs generation per-cell in a fixed order, then scores, then applies gate + spread rule.
- **Risk: Founder-pack hash without commit.** Git SHA capture assumes the product dir is committed. If uncommitted, capture `HEAD` SHA + a `dirty: true` flag in the output front-matter.
- **Risk: Trigger-phrase collision.** Verified clean as of 2026-04-28; revisit if `CLAUDE.md` is edited concurrently.
- **Out-of-scope (deferred):** automated availability lookups, tagline generation, fixture-backed validation. Tracked as `fixture_status: missing` in the registry; promotion to `passing` is a separate plan.

## Implementation Phases

### Phase 1: Canonical skill files
- Create `skills/canonical/app-name-discovery/{skill.md,contract.yaml,output-template.md}`.
- Define rubric, weights, gates, spread rule, output schema.

### Phase 2: Adapter + project pointer
- Create `skills/adapters/claude/app-name-discovery.md` modeled on `gtm-artifact-refresh` adapter.
- Create `.claude/skills/app-name-discovery.md` per WIRING.md template (boilerplate only).

### Phase 3: Registry + trigger phrases
- Append entry to `skills/registry.yaml`.
- Add bullet under "Available Claude project skills" in `CLAUDE.md`.
- Add 4 trigger phrases under "Trigger phrases → skills" in `CLAUDE.md`.

### Phase 4: Self-verification
- Run `verification-loop` (or at minimum `skill-stocktake`) to confirm no estate drift.
- Manually trace each acceptance criterion and tick.

## Future Considerations

Surfaced by industry-naming-framework research (Igor, Lexicon, Altman, Placek) but **deferred** because the brainstorm explicitly locked the 8-dimension rubric. Promote in a v2 plan if signal warrants:

- **Depth / Meaning capacity** (Lexicon's sound-symbolism work) — does the name reward repeated exposure with layered meaning? Distinct from distinctiveness; about whether the name *grows* with the brand.
- **Extensibility / Future-proofing** (Igor's "Bond" criterion) — can the name stretch beyond the v1 product? Burbn → Instagram cautionary tale.
- **Strategic story / Brand-narrative fit** — does the name *do work* for the brand narrative beyond positioning fit?
- **Additional archetypes to consider in v2:** Founder/Eponymous, Acronym/Initialism, Geographic. Acronym and Founder should generally be *penalized* for new consumer apps, not promoted.
- **Automated availability lookups** (App Store, USPTO, domain) — currently flag-for-manual.
- **Tagline candidate generation** — currently owned by `app-store-positioning-pack`.

## Sources & References

- **Origin brainstorm:** [docs/brainstorms/2026-04-28-app-name-discovery-skill-brainstorm.md](docs/brainstorms/2026-04-28-app-name-discovery-skill-brainstorm.md). Key decisions carried forward: register×archetype matrix shape; Full 8 rubric with 1–5 + weights; cross-language safety as hard gate; archetype spread rule on shortlist; score-only availability handling; canonical + adapter + project-pointer wiring.
- **Wiring contract:** [skills/WIRING.md](skills/WIRING.md).
- **Reference skill (structure):** [skills/canonical/gtm-artifact-refresh/skill.md](skills/canonical/gtm-artifact-refresh/skill.md), [skills/adapters/claude/gtm-artifact-refresh.md](skills/adapters/claude/gtm-artifact-refresh.md), [.claude/skills/gtm-artifact-refresh.md](.claude/skills/gtm-artifact-refresh.md).
- **Sibling skill (founder-pack consumer):** [skills/adapters/claude/app-store-positioning-pack.md](skills/adapters/claude/app-store-positioning-pack.md).
- **Project conventions:** [CLAUDE.md](CLAUDE.md) — disambiguation rule for trigger phrases.
