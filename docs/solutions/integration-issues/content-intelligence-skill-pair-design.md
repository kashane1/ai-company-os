---
title: "Content Intelligence Skill Pair — Design & Review-Driven Fixes"
category: integration-issues
date: 2026-04-15
tags:
  - phase-3
  - skill-design
  - gtm-pipeline
  - content-intelligence
  - niche-research-brief
  - gtm-artifact-refresh
  - cross-skill-contract
  - memory-schema
  - multi-niche
  - architecture-review
related:
  - docs/solutions/integration-issues/content-pipeline-multi-tool-orchestration.md
  - docs/solutions/integration-issues/multi-platform-social-expansion-architecture.md
  - docs/solutions/integration-issues/social-media-publishing-nuances.md
  - skills/canonical/niche-research-brief/skill.md
  - skills/canonical/niche-research-brief/memory-schema.yaml
  - skills/canonical/gtm-artifact-refresh/skill.md
  - skills/canonical/content-voice-guardrail/skill.md
  - skills/canonical/social-post-safety/skill.md
  - skills/WIRING.md
  - packages/tools/product_artifacts/gtm_chain.py
  - packages/tools/social_tools/postiz_client.py
commits:
  - 807b270 Add niche-research-brief and gtm-artifact-refresh skills
  - 71f447c Add extended chain validation for content intelligence artifacts
  - bd13727 Make postiz hashtag limits platform-aware
---

# Content Intelligence Skill Pair — Design & Review-Driven Fixes

This document captures the design of two new skills (`niche-research-brief` and `gtm-artifact-refresh`), the cross-skill contract between them, and the 3 critical + 6 warning gaps caught by architectural review before commit. Use it when designing any new multi-skill, multi-artifact workflow in this repo.

## Problem

The content factory was producing slides, but the upstream GTM artifacts (taxonomy, voice, hook library, hashtag strategy, backlog, calendar) were authored once and then drifted. Nothing connected real audience signal to those artifacts, and nothing carried learning forward between research passes.

The non-obvious part was the cross-skill design. A single mega-skill that "researches and refreshes everything" would have been easier to write but impossible to iterate on — research cadence (weekly) and artifact refresh cadence (per campaign) are different, and a product can have multiple niches sharing one voice. We needed two skills with a durable contract between them, and that contract could not be "parse markdown section headings from the other skill's output" — every prior attempt at that pattern in this repo has been fragile.

We also needed the system to get smarter over time. A research pass that ignores what the last pass found, or what the last campaign's posts actually performed, is just expensive re-discovery.

## Root insights

- **Memory schema is the contract.** Instead of skills reading each other's markdown, both skills read and write a structured YAML memory file per product governed by an explicit `memory-schema.yaml`. The schema is the interface; the markdown brief is for humans.
- **Two-layer memory: `product_context` + `niches.<niche-id>`.** Voice, brand guardrails, and cross-niche learnings live at the product level. Topic pools, archetype mixes, scored topics, sources, lexicon, and refresh history live per-niche. One product, many niches, one voice.
- **Learning loop closes through `performance-log.md`.** Each gtm-artifact-refresh run appends to `refresh_runs`, and the next research pass reads performance log entries keyed to prior `backlog_item_number`s to down-weight stale archetypes and up-weight proven hooks. The performance log is read-only to both skills; it is written by the nightly observability rollup.
- **8-archetype taxonomy with enforced mix balance.** Pain Point, Value/Educational, Identity/Tribal, Debate/Hot Take, Aspirational/Aesthetic, Humor/Relatable, Seasonal/Timely, Behind-the-scenes. `gtm-artifact-refresh` refuses to emit a backlog that violates the target mix — no more accidental all-educational weeks.
- **Engagement-first scoring weights.** Virality 30%, Niche fit 25%, Content gap 20%, Timeliness 15%, Product alignment 10%. Product alignment is last on purpose: a topic that builds audience but doesn't mention the product is still worth posting.

## Review-driven fixes

The architecture-strategist review pass caught gaps that fell into recognizable categories. Each is fixed with a concrete commit.

### Critical (would have broken execution)

- **Schema/instructions drift.** `skills/canonical/gtm-artifact-refresh/skill.md` told the agent to write a `refresh_runs` field that didn't exist in `skills/canonical/niche-research-brief/memory-schema.yaml`. Fix: added `refresh_runs` array per niche to the schema.
- **Under-specified contract.** `gtm-artifact-refresh` took only `product_id` + `mode` but the memory file supported multiple niches per product. Fix: added required `niche` input to the contract, skill, and adapter.
- **Declared-but-not-invoked dependencies.** The skill listed `content-voice-guardrail` and `social-post-safety` as dependencies but no instruction step invoked them. Fix: added Phase 9 that explicitly runs both validators on the updated voice.md and hashtag-strategy.md.

### Warnings

- `packages/tools/product_artifacts/gtm_chain.py` — added `EXTENDED_FILES` tuple and `extended_missing` / `extended_empty` fields so the validator knows about `niche-research-brief.md`, `niche-research-memory.yaml`, and `content-taxonomy.md`.
- `skills/canonical/gtm-artifact-refresh/skill.md` Phase 8 — write `backlog_item_number` back to memory after each topic enters the backlog, so the performance loop can key on it.
- `skills/canonical/gtm-artifact-refresh/skill.md` + adapter — rewrote every data-source reference to read from memory YAML paths (`niches.<niche>.archetype_performance`, `niches.<niche>.topics`, `niches.<niche>.lexicon`, `niches.<niche>.sources.tiktok.hashtags_tracked`, `niches.<niche>.seasonal_calendar`) instead of parsing markdown section headings.
- `skills/canonical/gtm-artifact-refresh/skill.md` — added explicit multi-niche merge rules for single-file artifacts: voice.md prefixes niche-specific terms with context, hook-library.md tags hooks with niche name, hashtag-strategy.md groups hashtags under labeled niche sections.
- `packages/tools/social_tools/postiz_client.py` — added `PLATFORM_HASHTAG_LIMITS` dict (Instagram 8, TikTok 5, Threads 3, X 3) and a `platform` parameter on `create_draft_post()`; the hardcoded 5-cap was silently truncating Instagram drafts.

## Code examples

**Memory hierarchy** (one file per product, multiple niches inside):

```yaml
product_id: catchbook
product_context:
  identity:
    name: "Catchbook"
    tagline: "A fishing logbook for anglers who take the craft seriously"
  cross_niche_vocabulary:
    product_terms: [{ term: "catch log", context: "..." }]
    industry_terms: [{ term: "PB", confidence: high, context: "personal best" }]
  competitors: [{ name: "Fishbrain", ... }]

niches:
  freshwater-bass-fishing:
    last_researched: 2026-04-12
    runs: [...]
    refresh_runs: [...]
    sources: { reddit: {...}, tiktok: {...}, appstore: {...} }
    topics: [...]
    lexicon:
      species: [{ term: "largemouth bass", confidence: high, source_count: 12 }]
      techniques: [{ term: "Texas rig", confidence: high, source_count: 8 }]
    seasonal_calendar: [...]  # all 12 months
    archetype_performance: [...]  # all 8 archetypes, pct sums to 100
```

**Scored topic entry** (engagement-first weighted composite):

```yaml
- id: spot-finding-without-local-knowledge
  title: "Finding new spots without local knowledge"
  archetype: pain_point
  discovered: 2026-04-12
  source: r/bassfishing
  source_evidence: "47 upvotes, recurring across 3 threads"
  scores:
    virality: 85
    niche_fit: 90
    product_alignment: 95   # Catchbook directly solves this
    content_gap: 70
    timeliness: 60
    composite: 82          # V*.30 + NF*.25 + CG*.20 + T*.15 + PA*.10
  signal_strength: high
  lifecycle: new
  used_in_content: false
  backlog_item_number: null
  content_performance: null
```

## Prevention

### 1. Schema files are the contract
The YAML schema is the single source of truth for artifact shape. Any field named in `skill.md` instructions must be present in the schema, and vice versa.
**Check:** grep every field name mentioned in the skill's write/update steps against the schema file. Zero misses allowed.

### 2. Name the unit of work in the input contract
If a skill operates on a sub-entity (niche, segment, variant), the input payload must identify that sub-entity explicitly — never infer it from a parent ID.
**Check:** for each input, trace whether it uniquely resolves to exactly one processing target. If the underlying data is 1-to-many, add the discriminator.

### 3. Dependencies must be invoked, not just declared
A skill's `dependencies:` list is a lie unless the instruction body actually calls each one at a defined step with defined inputs.
**Check:** for every entry in `dependencies:`, find the instruction line that invokes it. Unreferenced dependencies get deleted or wired in.

### 4. Register every new artifact with the chain validator
New artifact types are invisible to the chain validator until registered. Silent omission is the default failure mode.
**Check:** when adding an artifact, update `packages/tools/product_artifacts/gtm_chain.py` in the same commit.

### 5. Structured data is the interface; markdown is the render
Skills consume and produce structured files (YAML/JSON). Markdown is a view layer for humans, never a parse target for downstream skills.
**Check:** if a downstream skill reads a `.md` file to extract data, reject the design — move the data to a sibling structured file and render the markdown from it.

### 6. Define merge semantics for every shared artifact
Any artifact touched by more than one upstream context (niche, product, campaign) needs written merge rules: append, replace-by-key, dedupe, or partition.
**Check:** list every shared-output file. For each, the skill must state the merge strategy and the conflict-resolution key.

### 7. Shared tools expose policy, not bake it in
Limits, caps, and formatting rules in shared clients must be parameters with platform-aware defaults, not hardcoded constants.
**Check:** scan shared tool modules for magic numbers and format rules. Each must be overridable by caller or driven by a policy lookup.

## Pre-commit review checklist

Before committing any new multi-file, multi-skill workflow:

- Does every field the skill writes exist in the schema?
- Does the input contract uniquely identify the unit of work?
- Is every declared dependency actually invoked in the steps?
- Are all new artifacts registered with the chain validator?
- Does any downstream skill parse markdown instead of structured data?
- For each shared output, is the merge rule written down?
- Are shared-tool limits parameterized and policy-driven?
- Can a fresh reader trace inputs to outputs without reading prose?
- What happens on partial failure mid-skill — is state recoverable?
- Is there a single command that validates the whole chain end-to-end?

## Cross-references

**Related solutions**
- [content-pipeline-multi-tool-orchestration.md](./content-pipeline-multi-tool-orchestration.md) — 3-tool gap in the same GTM pipeline
- [multi-platform-social-expansion-architecture.md](./multi-platform-social-expansion-architecture.md) — 5-platform expansion with platform-aware authoring
- [social-media-publishing-nuances.md](./social-media-publishing-nuances.md) — Postiz API payload structure and platform gotchas

**Canonical skills in the chain**
- `skills/canonical/niche-research-brief/` (produces brief + memory)
- `skills/canonical/gtm-artifact-refresh/` (consumes brief + memory, emits backlog)
- `skills/canonical/content-voice-guardrail/` (hard gate on voice)
- `skills/canonical/social-post-safety/` (hard gate on hashtags/platform limits)
- `skills/canonical/aso-keyword-refresh/` (similar weekly-refresh pattern)

**Pattern & wiring docs**
- `skills/WIRING.md` — canonical → adapter → project skill routing
- `skills/canonical/shared/product-artifact-chain.md` — artifact chain validation pattern

**Tools touched**
- `packages/tools/product_artifacts/gtm_chain.py` — extended chain validator
- `packages/tools/social_tools/postiz_client.py` — platform-aware hashtag limits
- `packages/tools/content_tools/gemini_images.py` — downstream consumer (unchanged this cycle)
