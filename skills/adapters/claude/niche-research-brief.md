---
description: Research a product niche and produce a structured brief with audience insights, scored topics, content archetypes, and competitor intelligence. Builds on previous runs via persistent memory. Run this to populate or refresh the research foundation for all GTM content.
canonical_source: skills/canonical/niche-research-brief/skill.md
---

# Niche Research Brief

You are running the niche-research-brief skill from `skills/canonical/niche-research-brief/skill.md`. Follow the canonical definition.

## Quick reference

This skill researches a niche (e.g. "freshwater bass fishing") and produces two files:

- **niche-research-brief.md** — readable brief with 9 sections covering audience, pain points, seasonality, lexicon, social landscape, content gaps, competitors, archetype analysis, and a scored topic registry
- **niche-research-memory.yaml** — persistent memory that accumulates intelligence across runs

**One memory file per product. Multiple niches inside it.** The memory file has two layers:
- Product-level context (identity, features, cross-niche vocabulary, competitors) — shared across all niches
- Niche-level context (topics, sources, lexicon, seasonal calendar, archetypes) — one section per niche

**Critical:** Read the schema at `skills/canonical/niche-research-brief/memory-schema.yaml` before writing any YAML. Follow it exactly.

## Steps

### 0. Read the memory schema

Read `skills/canonical/niche-research-brief/memory-schema.yaml` to understand the exact YAML structure you must produce. This is non-negotiable — the schema is the contract.

### 1. Load memory + close feedback loop

- Read `docs/products/<product_id>/gtm/niche-research-memory.yaml`
  - If missing: first run for this product. Initialize from schema. Populate `product_context` from founder-brief.md, product-brief.md, mvp-spec.md if they exist. Create empty niche entry.
  - If exists but niche is new: add a new niche entry. Do not overwrite existing niches.
- Read `docs/products/<product_id>/gtm/performance-log.md` (read-only)
- Match published content to topics in memory, update `content_performance` ratings
- Read `docs/products/<product_id>/gtm/content-backlog.yaml` to mark topics as `used_in_content`

### 2. Plan the research pass

- Identify which sources need re-checking (stale >30 days or high-signal)
- Identify which archetypes have topic gaps
- If `focus_areas` provided, prioritize those areas
- Run 1: hit all Tier 1 sources (Reddit, App Store, TikTok, Google Trends)

### 3. Execute research (deep pass, single run)

Use web search and web fetch for all research. Sources in priority order:

**Reddit** — Discover subreddits via `site:reddit.com "<niche>"`. For each, extract pain points, debates, FAQs, gear mentions, species, techniques, seasonal patterns. Note upvote counts as signal strength.

**App Store reviews** — Discover competitors via `"<niche>" app site:apps.apple.com`. Focus on 2-4 star reviews for actionable insight. Extract praise, complaints, feature requests, exact user language.

**TikTok / target platforms** — Search for niche content. Extract performing formats, top creators, hook patterns, hashtag clusters, and which content archetypes dominate.

**Google Trends** — Check seasonal patterns, rising queries, regional differences.

**Amazon / gear reviews** — Targeted only. Fill lexicon gaps for brand names, gear terms, technique vocabulary.

### 4. Classify and score every topic

Classify into one of 8 archetypes: Pain Point, Value/Educational, Identity/Tribal, Debate/Hot Take, Aspirational/Aesthetic, Humor/Relatable, Seasonal/Timely, Behind-the-scenes/Process.

Score each topic (0-100 per dimension):
- **Virality (x0.30)** — engagement potential
- **Niche fit (x0.25)** — audience specificity
- **Content gap (x0.20)** — underserved by existing creators
- **Timeliness (x0.15)** — relevant right now
- **Product alignment (x0.10)** — natural product connection (lowest weight intentionally)

### 5. Merge into memory (follow the schema exactly)

All writes target `niches.<niche-id>` unless the finding is product-level.

- Add new topics with ALL required fields from schema (id, title, description, archetype, scores, lifecycle, etc.)
- Update source quality ratings, `last_sampled` dates
- Grow credibility lexicon across all 6 categories (species, techniques, gear_brands, slang, locations, seasons_and_conditions)
- Update seasonal calendar (all 12 months)
- Update competitors (product-level → `product_context.competitors`, niche-level → `niches.<niche-id>.competitor_notes`)
- Update archetype performance (all 8 archetypes, mix pct sums to 100)
- If product-level intelligence found → write to `product_context`
- Add run entry, update `last_updated`

### 6. Generate the brief

Write `niche-research-brief.md` with ALL cumulative intelligence. Required sections:

1. Audience Profile
2. Pain Points & Desires
3. Seasonal Calendar
4. Credibility Lexicon
5. Social Media Landscape
6. Content Gaps
7. Competitor App Intelligence
8. Archetype Performance
9. Scored Topic Registry (sorted by composite score, each tagged NEW/CONFIRMED/PROMOTED/DEPRIORITIZED/USED)

### 7. Validate

- Brief has all 9 sections
- Memory file is valid YAML conforming to `memory-schema.yaml`
- Updated run entry present
- At least 3 sources sampled (Run 1) or 1 re-checked (subsequent)
- Lexicon has entries in all 6 categories
- Seasonal calendar has all 12 months
- All 8 archetypes in archetype_performance, mix pct sums to 100
- At least 10 scored topics (Run 1)

## Boundaries

- **May edit**: `docs/products/<product_id>/gtm/niche-research-brief.md`, `docs/products/<product_id>/gtm/niche-research-memory.yaml`
- **Must not touch**: `apps/`, `packages/`, `infra/`, `state/`, `products/`, any other GTM artifact
- **Read-only**: `performance-log.md`, `content-backlog.yaml`, product artifact chain (founder-brief, product-brief, mvp-spec)
- **Do not invent** product decisions or audience assumptions without research backing
