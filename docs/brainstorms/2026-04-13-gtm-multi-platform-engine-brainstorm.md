# Brainstorm: Multi-Platform Content Engine Evolution

**Date:** 2026-04-13
**Status:** Complete
**Product:** Catchbook (initial), extensible to all products
**Trigger:** Audit of existing GTM skillflow vs. Ronin's "Content Skill Graph" framework

---

## What We're Building

Evolving the existing 4-lane GTM pipeline to support **multi-platform content repurposing** across 5 platforms (TikTok, Instagram, Threads, X/Twitter, Facebook), with platform-aware authoring, per-platform tone adaptation, audience segmentation, and a performance feedback loop.

### Current State
- 4-lane pipeline: niche-research-brief -> gtm-artifact-refresh -> content-factory -> content-scheduler
- Targets 3 visual platforms: TikTok, Instagram, Threads
- 30 backlog items (all status=draft), each one post for one platform
- Strong research foundation, archetype-based taxonomy, deterministic image generation, Postiz publishing

### Target State
- Same 4-lane pipeline + 1 new skill (content-performance-review)
- Targets 5 platforms: TikTok, Instagram, Threads, **X/Twitter, Facebook**
- Topics repurposed into 5 platform-native posts (rethought, not reformatted)
- Shared platform playbooks with product-specific overrides
- Platform-tone adaptation layer
- Hooks tagged per platform
- Audience segment routing (expert vs casual)
- Weekly performance feedback loop updating hooks + archetype weights

### Platforms NOT in scope (for now)
- LinkedIn
- YouTube
- Newsletter/Email

---

## Why This Approach

The Ronin article's core insight is that **10 copies of the same text reformatted is not repurposing** — real repurposing means each platform version rethinks the angle, hook, tone, format, and structure. Our current system produces great content but only for visual platforms with the same approach. Adding X and Facebook requires fundamentally different content types (text-first vs visual-first), which forces us to build the adaptation layer properly.

We chose to extend existing skills rather than add new pipeline lanes because the authoring logic (understanding topic, selecting hooks, adapting voice) is the same cognitive task regardless of output platform. What changes is the platform knowledge the skill references.

---

## Key Decisions

### 1. Backlog Model: Flat with topic_id linking

**Decision:** Keep individual per-platform items in content-backlog.yaml but add a shared `topic_id` field that groups items from the same source topic.

**Why:** Simpler schema change. Each item can be scheduled, generated, and published independently. No nested data structures to manage. Easy to query "show me all items for topic_003" or "show me all X posts."

**Schema addition:**
```yaml
- item_number: 31
  topic_id: "topic_001"        # NEW — groups related items
  hook: "..."
  archetype: pain_point
  platform: x                   # NEW platform values: x, facebook
  format: short_take            # NEW — platform-specific format
  campaign: zero
  # ... rest unchanged
```

### 2. Text vs Visual Pipeline: Optional image attachment

**Decision:** Text-platform backlog items (X, Facebook) skip content-factory by default. They go straight from gtm-artifact-refresh -> content-scheduler. Items can optionally include a `visual_hint` field to generate an accompanying image.

**Why:** X and Facebook posts often perform better as pure text. But sometimes an image helps (proof posts with screenshots, carousel-style threads). The optional flag gives flexibility without forcing every post through image generation.

**How it works:**
- content-factory checks `platform` field — if `x` or `facebook` AND no `visual_hint`/`slides`, skip
- content-scheduler handles text-only items: just caption + hashtags, no media upload
- If `visual_hint` is present on a text-platform item, content-factory generates the image as usual

### 3. Platform Playbooks: Shared with product overrides

**Decision:** Platform playbook files live in a shared location with universal platform rules. Product-specific GTM artifacts (voice.md, content-taxonomy.md) handle product-specific tone and audience overrides.

**Why:** "X has a 280 char limit" and "Facebook algo penalizes external links" don't change per product. Avoids duplicating universal knowledge. Product voice and audience context already live in per-product GTM artifacts.

**File structure:**
```
skills/canonical/gtm-artifact-refresh/platforms/
  x.md              # Universal X/Twitter rules
  facebook.md       # Universal Facebook rules
  tiktok.md         # Universal TikTok rules
  instagram.md      # Universal Instagram rules
  threads.md        # Universal Threads rules
  platform-tone.md  # Voice adaptation rules per platform
```

**Product overrides come from:**
- `docs/products/<id>/gtm/voice.md` — brand personality, tone markers, vocabulary
- `docs/products/<id>/gtm/content-taxonomy.md` — archetypes, mix weights
- `docs/products/<id>/gtm/audience/` — segment definitions (expert.md, casual.md)

### 4. Skill Boundary: Extend gtm-artifact-refresh

**Decision:** Multi-platform repurposing becomes part of gtm-artifact-refresh, not a new skill.

**Why:** It already authors content and writes the backlog. Adding multi-platform expansion is a natural extension — it's the same cognitive task (understand topic, select angle, adapt voice) applied to more output targets. Keeps the pipeline at 4 lanes. The platform playbook files do the heavy lifting for platform-specific adaptation.

**What changes in gtm-artifact-refresh:**
- Reads platform playbooks + platform-tone.md for each target platform
- For each topic: generates one item per platform (5 items total)
- Follows default chain order: X -> TikTok -> Instagram -> Threads -> Facebook (see Decision 7)
- Tags hooks with platform suitability
- Routes audience segments to appropriate angles

### 5. Performance Feedback Loop: New content-performance-review skill

**Decision:** A dedicated skill that reads performance-log.md, scores hooks and archetypes by platform, and produces structured recommendations. Triggered weekly by the founder.

**Why:** The feedback analysis is a distinct cognitive task from content authoring or research. It needs its own validation logic (statistical significance thresholds, per-platform normalization). Making it a skill gives it explicit inputs/outputs and keeps it testable.

**Skill inputs:**
- performance-log.md (engagement data)
- hook-library.md (current hooks)
- content-taxonomy.md (current archetype mix)
- content-backlog.yaml (which items were published)

**Skill outputs:**
- Performance report (winners/losers by hook type, archetype, platform)
- Proposed updates to hook-library.md (retire underperformers, promote winners)
- Proposed archetype mix weight adjustments
- Proposed platform-tone refinements

**Founder approves** changes before they're applied. Skill does not auto-modify artifacts.

### 6. Audience Segments: Expert vs Casual

**Decision:** Two segments for Catchbook — Expert (tournament/intense/daily anglers) and Casual (weekend/infrequent anglers).

**File structure:**
```
docs/products/catchbook/gtm/audience/
  expert.md     # Who they are, what they want, how to talk to them
  casual.md     # Who they are, what they want, how to talk to them
```

**How it affects content:**
- Each backlog item gets an `audience` field (expert | casual | both)
- Platform playbooks note which segments skew where (X = more expert, Facebook = more casual)
- Hook selection adapts: expert gets "here's 5 advanced patterns" energy, casual gets "you can do this too" energy
- The archetype mix can weight differently per segment

### 7. Chain Order: Single default, refined by data

**Decision:** Launch with one default chain order for all archetypes: **X -> TikTok -> Instagram -> Threads -> Facebook**. The content-performance-review skill will recommend per-archetype ordering adjustments once engagement data exists.

**Why:** X-first forces brevity and the sharpest hook, which makes expanding to other platforms easier. Per-archetype ordering is a reasonable future optimization, but we have zero performance data to validate 8 different orderings. Starting with one chain keeps the skill simpler and avoids baking in guesses.

**Future state:** Once content-performance-review has enough data (target: 4-6 weeks of publishing), it can propose archetype-specific chain orders based on which platform produced the highest engagement per archetype. Those recommendations get added to the platform playbooks after founder approval.

### 8. Litmus Test Integration

**Decision:** Add a validation step to gtm-artifact-refresh: after generating all 5 platform variants for a topic, run a "cross-platform distinctiveness check" that verifies each post has a different hook, different angle, and different format.

**Implementation:** Instruction in the skill, not a separate validator. The skill checks:
- No two posts in the same topic_id share the same opening line
- Each post uses a different format (short take vs thread vs carousel vs video script vs discussion)
- Tone markers match the platform-tone.md specification

---

## Scope of Changes

### Existing Skills Modified
1. **gtm-artifact-refresh** — Major extension: multi-platform authoring, topic_id grouping, platform playbook consumption, audience routing, default chain order, litmus test
2. **content-factory** — Minor: skip text-only items, handle optional visual_hint on text platforms
3. **content-scheduler** — Minor: handle text-only posts (no media upload), support X and Facebook platform settings in Postiz
4. **niche-research-brief** — Minor: add per-platform topic suitability scoring to topic registry
5. **content-voice-guardrail** — Minor: validate against platform-tone.md (not just voice.md)

### New Skills
1. **content-performance-review** — Weekly feedback loop skill (Lane 5)

### New Shared Files
1. Platform playbooks: x.md, facebook.md, tiktok.md, instagram.md, threads.md (in skills/canonical/)
2. platform-tone.md (voice adaptation layer)

### New Per-Product Files
1. audience/expert.md, audience/casual.md (per product)

### Schema Changes
1. content-backlog.yaml: add `topic_id`, `format`, `audience` fields
2. hook-library.md: add `platforms:` tag per hook

---

## Resolved Questions

1. **Which platforms?** — X/Twitter and Facebook only. LinkedIn, YouTube, Newsletter deferred.
2. **Backlog model?** — Flat with topic_id, not nested topics.
3. **Text vs visual?** — Optional image attachment; text platforms skip content-factory by default.
4. **Playbook scope?** — Shared platform rules, product-specific voice/audience overrides.
5. **Skill boundary?** — Extend gtm-artifact-refresh, don't add a repurpose lane.
6. **Feedback loop?** — New content-performance-review skill, founder-approved changes.
7. **Audience segments?** — Expert (intense/daily) vs Casual (infrequent/weekend).
8. **Chain order?** — Single default (X -> TikTok -> Instagram -> Threads -> Facebook), refined per-archetype by performance data later.

## Open Questions

None — all key decisions resolved through dialogue.
