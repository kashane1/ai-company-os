---
description: Consume a niche-research-brief and refresh the GTM artifact chain — content-taxonomy.md, voice.md, hook-library.md, hashtag-strategy.md, content-backlog.yaml, and campaign-calendar.md. Enforces content archetype mix balance. Run this after niche-research-brief to propagate research into actionable content artifacts.
canonical_source: skills/canonical/gtm-artifact-refresh/skill.md
---

# GTM Artifact Refresh

You are running the gtm-artifact-refresh skill from `skills/canonical/gtm-artifact-refresh/skill.md`. Follow the canonical definition.

## Quick reference

This skill takes the niche research brief and propagates its intelligence into the GTM artifacts that drive content creation. It creates or updates 6 artifacts and enforces archetype mix balance in the content backlog.

**Prerequisite:** `niche-research-brief.md` must exist. Run the `niche-research-brief` skill first.

**Critical:** Read structured data from `niche-research-memory.yaml` (the machine-readable state), NOT by parsing section headings in the brief markdown. The brief is for humans; the memory YAML is the contract surface.

## Steps

### 1. Load inputs

- Read `skills/canonical/niche-research-brief/memory-schema.yaml` to understand the memory file structure
- Read `skills/canonical/gtm-artifact-refresh/platforms.md` — the platform playbook for multi-platform authoring (tone, format, character limits per platform)
- Read `niche-research-brief.md` (required — abort if missing)
- Read `niche-research-memory.yaml` — locate the niche entry at `niches.<niche>`. Abort if the niche key is not found.
- Read `product_context` from the memory file for cross-niche vocabulary and product-level competitors
- Read all existing GTM artifacts (content-taxonomy.md, voice.md, hook-library.md, hashtag-strategy.md, content-backlog.yaml, campaign-calendar.md)
- If `content-taxonomy.md` does not exist, force `mode: full`
- Accept `platforms` input (default: `[x, tiktok, instagram, threads, facebook]`) — which platforms to generate backlog items for

### 2. Create or update content-taxonomy.md

Read archetype data from `niches.<niche>.archetype_performance` and topic examples from `niches.<niche>.topics`.

Define all 8 content archetypes with:
- Trigger (psychological response)
- Primary engagement type
- Voice note (how to write in brand voice)
- Product proximity (high/medium/low/none)
- Target mix percentage (from `archetype_performance[].recommended_mix_pct`)
- 2-3 example hooks (highest composite score topics for that archetype)

Include composite scoring weights and mix rules:
- Never 3+ of same archetype in a row
- Weekly minimum: 1 Debate + 1 Identity post
- Seasonal content overrides calendar when real-world events are active
- Product mentions only in Pain Point and Value posts, only when natural

### 3. Update voice.md (additive only)

Read from `niches.<niche>.lexicon` (all 6 categories) and `product_context.cross_niche_vocabulary`.
- Add high-confidence species names, technique terms, locations, seasons/conditions terms, insider slang, gear brand names
- **Multi-niche rule:** Prefix niche-specific terms with context (e.g. "pre-spawn — bass fishing"). Cross-niche and product terms need no prefix.
- **Never remove** existing vocabulary or banned phrases (append-only for safety)
- **Never modify** voice pillars or "Who we are" section (founder-authored)

### 4. Update hook-library.md

Read from `niches.<niche>.topics` (sorted by composite score) and `niches.<niche>.sources.tiktok.top_creators`.
- Tag each hook with archetype and niche: `"Hook text" — [Archetype] — Niche: <niche> — Source: topic-id`
- **Multi-niche rule:** Hooks that apply across niches omit the niche tag.
- Incremental: append new hooks, preserve existing ones still in use
- Full: rewrite from memory, but keep hooks with above-median engagement

### 5. Update hashtag-strategy.md

Read from `niches.<niche>.sources.tiktok.hashtags_tracked` (and other platforms).
- **Multi-niche rule:** Group hashtags by niche under labeled sections. Platform limits apply per-post, not per-section.
- Respect platform limits (Instagram 8, TikTok 5, Threads 3, X 3, Facebook 2)
- Ensure sections exist for all 5 platforms (add Facebook and X sections if missing)
- Replace low-volume hashtags with higher-volume alternatives
- Keep hashtags that performed well in published content

### 6. Update content-backlog.yaml (multi-platform authoring)

Read from `niches.<niche>.topics` where `used_in_content: false`, sorted by composite score descending.

- Lock items already scheduled or published (do not modify or remove)
- Tag all existing items with archetype and composite score if not already tagged

**Multi-platform authoring loop** (cap at 3-5 topics per invocation):

For each unused topic, for each platform in the `platforms` input:
1. Check platform suitability using `platforms.md`. Skip unsuitable platforms (min 3 per topic).
2. RETHINK the angle per platform — different opening line, adapted tone.
3. **Visual platforms (tiktok, instagram, threads):** author full slides array + caption + hashtags.
4. **Text platforms (x, facebook):** author caption + hashtags ONLY. No `slides` field in the YAML.
5. **Enforce character limits at authoring time:** X 280, Threads 500, Instagram 2200, TikTok 4000, Facebook 300-800 sweet spot.
6. Assign shared `topic_id` (format: `topic_NNN`) across all platform variants of the same topic.
7. Write all items for a topic as a single append. Item numbers start at max(existing) + 1.
8. **Idempotent:** check existing backlog for this `topic_id` — only generate missing platforms.

- New Campaign Zero items = pure engagement (no product mentions)
- New Campaign One items = product-relevant content

**Check archetype mix balance** against taxonomy targets:
```
Value/Educational: N items (N%) — target N% — OK/NEED N MORE/OVER-INDEXED
Identity/Tribal:   N items (N%) — target N% — OK/NEED N MORE/OVER-INDEXED
...
```
Generate additional items for under-represented archetypes if needed.

### 7. Update campaign-calendar.md

- Only adjust timing, not structure
- Apply seasonal intelligence from `niches.<niche>.seasonal_calendar`
- Move seasonally-relevant items earlier, out-of-season items later
- Stagger same-topic posts (`topic_id`) 24-48 hours apart across platforms. Include `topic_id` in calendar entries.
- Never reschedule published items

### 8. Update memory

In `niche-research-memory.yaml` at `niches.<niche>`:
- Set `used_in_content: true` AND `backlog_item_number` for each topic added to backlog
- Append a `refresh_runs` entry with: date, mode, artifacts_updated, backlog_items_added, mix_balanced, mix_report

### 9. Run validators

- Run `content-voice-guardrail` on the updated voice.md — run once per platform (passing `platform` param) to verify tone adaptation
- Run `social-post-safety` on the updated hashtag-strategy.md (all 5 platforms: Instagram 8, TikTok 5, Threads 3, X 3, Facebook 2)
- Character limits are enforced during authoring (Phase 6), not just at validation
- If either fails, fix the changes before completing

### 10. Validate and output

- All files exist and non-empty
- Backlog >= 14 items
- All new items have archetype tag and score
- Voice.md changes are additive only
- Both validators passed
- Output the mix report

## Boundaries

- **May edit**: `content-taxonomy.md`, `voice.md`, `hook-library.md`, `hashtag-strategy.md`, `content-backlog.yaml`, `campaign-calendar.md`, `niche-research-memory.yaml`
- **Must not touch**: `apps/`, `packages/`, `infra/`, `state/`, `products/`
- **Read-only**: `niche-research-brief.md`, `performance-log.md`, `memory-schema.yaml`, `platforms.md`
- **Do not remove** existing voice constraints, published content items, or scheduled calendar entries
