---
title: "feat: Multi-Platform Content Engine Evolution"
type: feat
status: active
date: 2026-04-13
origin: docs/brainstorms/2026-04-13-gtm-multi-platform-engine-brainstorm.md
---

# feat: Multi-Platform Content Engine Evolution

## Enhancement Summary

**Deepened on:** 2026-04-13
**Research agents used:** architecture-strategist, code-simplicity-reviewer, agent-native-reviewer, pattern-recognition-specialist, performance-oracle, security-sentinel, data-migration-expert, best-practices-researcher

### Key Improvements from Deepening

1. **Simplified schema** — dropped `format` field, `audience` field, and numeric platform suitability scoring per simplicity review. Platform playbooks provide all context the LLM needs without rigid enums.
2. **Deferred Phase 3** — content-performance-review skill moved to a follow-up plan (requires 30+ published posts). Reduces scope by ~100 lines and one entire skill.
3. **Consolidated platform playbooks** — 6 files merged into 1 (`platforms.md`) per simplicity review.
4. **Added security hardening** — content injection checks, filename sanitization, threat model update requirement.
5. **Added performance safeguards** — topics-per-invocation cap, Gemini retry logic, idempotent re-run support, atomic YAML writes.
6. **Fixed migration gaps** — null-guarded validator, explicit Postiz text-only payload fix, item_number sequencing rule.
7. **Added platform algorithm insights** — X reply-engagement weighting (27x), Facebook Shares-to-Stories priority, stagger timing 24-48h.

### Simplifications Applied (from YAGNI review)

| Removed | Reason |
|---------|--------|
| `format` enum (15 values) | No downstream consumer; platform playbooks guide authoring |
| `audience` field + persona files | Zero audience data; platform descriptions guide tone |
| Platform suitability scores (0-100) | No empirical basis; simple skip/author decision instead |
| Formal cross-platform litmus test | Redundant if authoring prompt is adequate; add one instruction line |
| Fixed chain order | Arbitrary sequence; LLM authors independently per platform |
| `visual_hint` on text platforms | Text platforms = text only in v1 |
| Hook platform tags | LLM already has platform context during selection |
| content-performance-review (entire Phase 3) | Zero performance data; cannot run for weeks; defer to follow-up plan |

---

## Overview

Evolve the 4-lane GTM content pipeline to support **5 platforms** (TikTok, Instagram, Threads, X/Twitter, Facebook) with multi-platform repurposing and platform-aware authoring. One topic produces up to 5 platform-native posts — each rethought for the platform, not reformatted.

(see brainstorm: docs/brainstorms/2026-04-13-gtm-multi-platform-engine-brainstorm.md)

## Problem Statement

The current pipeline produces content for 3 visual platforms (TikTok, Instagram, Threads) using the same slide-based approach. Adding X and Facebook requires:

1. **Text-first content paths** — X and Facebook are primarily text platforms; forcing them through the image generation pipeline is wasteful and produces suboptimal content
2. **Platform-native authoring** — each platform has different character limits, format rules, audience segments, and tone expectations that aren't currently encoded
3. **Cross-platform distinctiveness** — without a repurpose chain, expanding to more platforms risks producing near-identical content that annoys multi-platform followers

## Proposed Solution

### Architecture

Extend existing 4-lane pipeline:

```
Lane 1: niche-research-brief         (minor update: add facebook to platform enum)
Lane 2: gtm-artifact-refresh          (MAJOR: multi-platform authoring, topic grouping)
Lane 3: content-factory                (minor: skip text-only items)
Lane 4: content-scheduler             (moderate: text-only posts, X/Facebook support)
```

New shared knowledge layer:

```
skills/canonical/gtm-artifact-refresh/platforms.md   (all 5 platforms + tone rules)

# Future (deferred):
Lane 5: content-performance-review    (after 30+ posts published)
```

### Key Design Decisions (from brainstorm)

1. **Flat backlog with topic_id** — items stay individual, grouped by shared `topic_id`
2. **Optional image attachment** — text platforms skip content-factory; text-only posts go straight to scheduler
3. **Shared playbooks, product overrides** — universal platform rules in skills/canonical/; product voice/audience in docs/products/
4. **Extend gtm-artifact-refresh** — no new repurpose skill; authoring is the same cognitive task applied to more outputs

---

## Implementation Phases

### Phase 0: Security Prerequisites

Before any implementation, address these security requirements:

#### 0.1 Update MCP Threat Model

The existing threat model at `docs/security/mcp-threat-model.md` does not cover X and Facebook channels. Per the threat model's own section 5, any change requires acknowledgment via `acknowledge_threat_model.sh`, and the GTM lane is blocked (`blocked:threat-model-drift`) until that runs.

- Update threat model to cover X and Facebook channel scoping
- Run `acknowledge_threat_model.sh`
- Verify `packages/config/gtm_allowed_accounts.py` exists (referenced in threat model but may not exist as actual module)

#### 0.2 Harden Postiz Client Security

- Migrate `POSTIZ_API_KEY` to macOS Keychain as a P0 secret (blast radius now covers 5 platforms)
- Add `@mention` and `$cashtag` detection to `social-post-safety/validator.py` — flag any `@` or `$` followed by alphanumeric unless in an allowlist (e.g., `@catchbookapp`)
- Add Unicode NFKC normalization before running profanity and PII checks (defeats homoglyph evasion)
- Sanitize filenames in `upload_media()` — strip characters outside `[a-zA-Z0-9._-]` from Content-Disposition header
- Truncate API error response bodies to 500 chars in logging (prevents credential leakage)
- Add hard assertion in `create_draft_post` that refuses any `type` value other than `"draft"`

**Files to edit:**
- `packages/tools/social_tools/postiz_client.py`
- `packages/tools/social_tools/social_post_safety/validator.py`
- `packages/config/secrets.py` — add `POSTIZ_API_KEY` to `P0_SECRET_NAMES`
- `docs/security/mcp-threat-model.md`

---

### Phase 1: Foundation — Schema, Playbooks, and Tool Updates

#### 1.1 Expanded Backlog Schema

Update the content-backlog.yaml schema with one new field:

```yaml
- item_number: 31
  topic_id: "topic_001"           # NEW — groups cross-platform items (null for legacy)
  hook: "you don't need a tackle box app. you need a fishing journal."
  archetype: pain_point
  platform: x                     # EXPANDED — now includes: tiktok | instagram | threads | x | facebook
  campaign: zero
  composite_score: 85
  status: draft
  slides:                         # ABSENT for text platforms — present for visual platforms
    - slide: 1
      text:
        headline: "..."
        subhead: null
        bullets: null
        body: null
      visual_hint: "..."
  caption: "..."                  # REQUIRED for all platforms
  hashtags: ["catchbookapp"]      # REQUIRED for all (can be empty list for Facebook)
```

**Migration for existing items (1-25):** Leave as-is with `topic_id: null`. New validation rules only apply to items where `topic_id` is non-null. No retroactive migration needed.

**Item numbering rule:** New item_numbers always start at `max(existing_item_numbers) + 1`. The skill must read the current max before appending.

**Files to edit:**
- `skills/canonical/gtm-artifact-refresh/skill.md` — update schema definition in Phase 6
- `packages/tools/product_artifacts/gtm_chain.py` — update validator (see Phase 1.1b)

#### 1.1b GTM Chain Validator Updates

Extend `packages/tools/product_artifacts/gtm_chain.py` with null-guarded validation:

```python
# Platform enum validation (new):
VALID_PLATFORMS = {"tiktok", "instagram", "threads", "x", "facebook"}
if item.get("platform") not in VALID_PLATFORMS:
    errors.append(f"invalid platform '{item.get('platform')}'")

# Slides are optional for text platforms:
if item.get("platform") in ("x", "facebook"):
    pass  # slides not required
elif item.get("topic_id") is not None:
    # Only enforce slides requirement for new multi-platform items
    if not item.get("slides"):
        errors.append(f"item {item['item_number']} on {item['platform']} missing slides")

# topic_id format when present:
if item.get("topic_id") is not None:
    if not isinstance(item["topic_id"], str):
        errors.append("topic_id must be a string")
```

**Files to edit:**
- `packages/tools/product_artifacts/gtm_chain.py`

#### 1.2 Platform Playbook (Consolidated)

Create a single consolidated reference file with all platform rules and tone adaptations. The LLM reads this every authoring run.

**Location:** `skills/canonical/gtm-artifact-refresh/platforms.md`

**Structure:**

```markdown
# Platform Playbooks & Tone Adaptations

## X / Twitter

### Platform DNA
- Character limit: 280 (target this for max reach; Premium allows 25K)
- Vibe: fast, casual, opinion-driven. lowercase default. 0.5 seconds to stop the scroll
- Algorithm: replies worth 27x a like; conversations (reply + author reply back) worth 150x
- External links get near-zero distribution; drop links in first reply
- Posts lose ~50% visibility every 6 hours; first-hour engagement is critical

### Content Rules
- Line breaks between every thought. Never dense paragraphs
- No hashtags in body (0-3 at very end if any)
- No emojis except as signoff
- Links go in a reply, never the main post
- Contrarian and proof hooks perform best

### Tone (adapting from product voice.md)
- Most concise version. Every word earns its place
- Lowercase everything. Short sentences. No filler
- "lol", "imo", "btw" used freely. Sarcasm welcome
- Coaching "you" voice. Direct, not lecturing

### Formats
- Short Take: 2-4 lines. bold claim + context + punchline
- Thread: "Here's [N] steps to [outcome]:" with numbered steps
- Proof Post: "[Before] -> [After] in [timeframe]" with breakdown
- Resource Drop: "I just found [thing] — [why it matters]"

### Posting Strategy
- 5-7x/week minimum
- Best times: 8-9am, 12-1pm, 5-6pm
- Engage in replies for 30 min after posting

---

## Facebook

### Platform DNA
- Character limit: 63,206 (sweet spot 300-800)
- Vibe: community-driven, discussion-focused. less "personal brand", more "helpful community member"
- Algorithm: Shares-to-Stories and Saves worth more than 50 generic Likes. Reels get 3-5x reach of feed posts
- Build account "tag" from last 9-12 posts — stick to 2 core themes
- Groups deliver higher organic reach than Pages

### Content Rules
- Questions and discussion prompts drive engagement
- Longer captions with personal context work well
- Native video upload gets algorithm priority
- 0-2 hashtags max (minimal hashtag culture)
- Links OK in post body (unlike X)
- Reply to every comment in first 2 hours

### Tone (adapting from product voice.md)
- Warmest, most community-oriented version
- Ask questions. Invite discussion
- More personal stories, less tactical playbooks
- "Have you ever..." and "What do you think about..." energy

### Formats
- Discussion: personal observation + question at the end
- Community Story: "Has anyone else tried..." framing
- Question: pure discussion prompt, no CTA

### Posting Strategy
- 3x/week
- Best days: Tue, Thu, Sat
- Share to relevant groups, not just profile

---

## TikTok

### Platform DNA
- Character limit: 4,000 caption
- Vibe: raw, unpolished, authentic. Overproduced content performs WORSE
- Discovery-based algorithm — don't need followers to go viral
- Audience: youngest demographic, more casual, discovering topics

### Content Rules
- Hook in FIRST 2 SECONDS. If you don't grab them, they swipe
- Screen recordings with voiceover work incredibly well for tech content
- No long intros. Jump straight in
- Captions/text overlays mandatory (most watch muted)
- 5 hashtags max at end of caption

### Tone (adapting from product voice.md)
- Most energetic version. Written as spoken word
- Fast-paced, no filler, hook immediately
- "This is insane" energy allowed
- Show don't tell

### Formats
- Screen Recording: show yourself doing the thing. 45-60 seconds
- Quick Tip: one actionable tip in 30 seconds
- Transformation: "I replaced X with Y" — before vs after

### Posting Strategy
- 5-7x/week (daily if possible)
- Best times: 7-9am, 12-3pm, 7-10pm
- Post consistently for 30 days before judging results

---

## Instagram

### Platform DNA
- Caption limit: 2,200 characters
- Vibe: visual-first. Image/carousel stops the scroll, caption closes the deal
- Audience: wider and more casual. More aspirational, more visual learners
- Carousels are king for engagement

### Content Rules
- Slide 1 = the hook. Bold claim, large text, max 8 words
- Captions add context the slides don't cover (don't repeat slides as text)
- 5-8 hashtags at end of caption
- CTA in last slide AND caption: "Save this" / "Follow for more"
- Links only in bio/stories

### Tone (adapting from product voice.md)
- Simplest language. Visual-first, text supports visuals
- Aspirational "you can do this too" energy
- Bold, clean, designed

### Formats
- Carousel: 7-10 slides, one idea per slide. One bold hook on slide 1
- Reel Script: adapted from TikTok with more polish

### Posting Strategy
- 4-5x/week (3 carousels, 1-2 Reels)
- Best times: 11am-1pm, 7-9pm

---

## Threads

### Platform DNA
- Character limit: 500
- Vibe: relaxed, community-feel, more casual than X
- Text-first, conversational, opinion-driven

### Content Rules
- Opinions and hot takes perform best
- More conversational than X — "talking out loud" energy
- No hashtags in body (0-3 at very end)
- No links. Pure text engagement
- Cross-post adapted versions of X content with softer tone

### Tone (adapting from product voice.md)
- Most relaxed version. Opinion-driven, conversational
- "Shower thought" energy
- Hot takes welcome

### Formats
- Hot Take: bold opinion, 1-3 short posts
- Opinion: personal observation + "what do you think?"
- Conversational: stream of consciousness, casual

### Posting Strategy
- 3-5x/week
- Whenever posting to X, adapt for Threads too

---

## The Adaptation Rule

When adapting across platforms: change TONE first, then FORMAT, then HOOK.
The voice stays the same — only the delivery changes.

Each platform version must have a different opening line and angle.
If someone followed you on ALL 5 platforms, they should never feel like
they're seeing the same content everywhere.
```

**Files to create:**
- `skills/canonical/gtm-artifact-refresh/platforms.md`

#### 1.3 Postiz Client Updates

Extend `packages/tools/social_tools/postiz_client.py`:

**1. Add X and Facebook platform settings:**

```python
# In _platform_settings()
"x": {"__type": "x"},
"facebook": {"__type": "facebook"},
```

> **Note from learnings:** These may need additional fields once tested (TikTok needed 9 fields). Start minimal, test with manual curl first, then add. Update `docs/solutions/integration-issues/social-media-publishing-nuances.md` with findings.

> **Postiz confirmed:** Postiz supports X/Twitter and Facebook along with 30+ other platforms. OAuth setup for Facebook and X requires a public-facing callback URL.

**2. Add text-only post support — fix the image key issue:**

The current code always includes the `image` key (even as empty list). Must conditionally omit it:

```python
# BEFORE (broken for text-only):
"value": [{"content": caption, "image": [...]}]

# AFTER (correct):
value_entry = {"content": caption}
if media_ids and media_urls:
    value_entry["image"] = [
        {"id": mid, "path": murl}
        for mid, murl in zip(media_ids, media_urls)
    ]
# If no media, "image" key is absent entirely — don't send empty list
```

> **Gotcha from learnings:** Both `id` and `path` required for media. Omitting `path` = 400 error. For text-only posts, omit the entire `image` key.

**3. Add rate-limit delay between Postiz API calls:**

Add a configurable 1-2 second delay between calls. Log `X-RateLimit-Remaining` and `Retry-After` response headers if present.

**4. Add Facebook to PLATFORM_HASHTAG_LIMITS:**

```python
PLATFORM_HASHTAG_LIMITS = {
    "tiktok": 5,
    "instagram": 8,
    "threads": 3,
    "x": 3,
    "facebook": 2,
}
```

**Files to edit:**
- `packages/tools/social_tools/postiz_client.py`

#### 1.4 Update social-media-publishing-nuances.md

Per the learnings doc (marked as active/living document), add X and Facebook sections:

```markdown
## X (Twitter)
- Platform settings: `{"__type": "x"}`
- Hashtag limit: 3
- Character limit: 280 (standard) / 25,000 (Premium) — target 280
- Algorithm: replies 27x a like, conversations 150x
- Links: near-zero distribution in main tweet; use first reply
- Post-publish behavior: [TO BE DOCUMENTED after first live post]

## Facebook
- Platform settings: `{"__type": "facebook"}`
- Hashtag limit: 2 (minimal culture)
- Character limit: 63,206 (sweet spot 300-800)
- Algorithm: Shares/Saves > Likes. Reels get 3-5x reach. Stick to 2 themes
- Post-publish behavior: [TO BE DOCUMENTED after first live post]
```

**Files to edit:**
- `docs/solutions/integration-issues/social-media-publishing-nuances.md`

---

### Phase 2: Skill Updates — Multi-Platform Authoring

The core pipeline changes.

#### 2.1 gtm-artifact-refresh — Multi-Platform Authoring

**This is the biggest change.** The skill currently generates one backlog item per topic. It must now generate up to 5 items per topic (one per platform).

**Changes to the canonical skill definition (`skills/canonical/gtm-artifact-refresh/skill.md`):**

**Phase 1 (Load Inputs) — add new inputs:**
- Read `platforms.md` from `skills/canonical/gtm-artifact-refresh/`
- Accept new input: `platforms` (list of enum, default `[x, tiktok, instagram, threads, facebook]`)

**Phase 5 (Hashtag Strategy) — add Facebook section:**
- Add Facebook hashtag rules (0-2 tags, purely categorical)
- Confirm X section exists

**Phase 6 (Content Backlog) — multi-platform authoring loop:**

Replace the current "one item per topic" loop with:

```
For each unused topic in the registry (cap: 3-5 topics per invocation):
  1. For each platform in the input platforms list:
     - Read that platform's section in platforms.md
     - Decide: can this topic work on this platform? If clearly unsuitable,
       skip with a one-line reason logged. Minimum 3 platforms per topic.
  
  2. For each suitable platform:
     - RETHINK the angle for this platform (not reformat)
     - Write a caption that fits the platform's character limit
       (X: 280 chars hard max, Threads: 500, Instagram: 2200,
        TikTok: 4000, Facebook: 300-800 sweet spot)
     - For visual platforms (tiktok, instagram, threads):
       author full slides array + caption + hashtags
     - For text platforms (x, facebook):
       author caption + hashtags only (no slides)
     - Each platform version MUST have a different opening line
  
  3. Assign shared topic_id to all items in the group
  
  4. Write all items for a topic as a single append operation
     Only after ALL items for a topic are written, update memory
     to set used_in_content: true
  
  5. Use atomic write: write to .tmp file, then rename
```

**Idempotent re-run support:** On re-run, count existing items for each topic_id in the backlog. Only generate missing platforms. This makes the operation safe to retry after a crash.

**Context window management:** Load only the relevant platform section from platforms.md when authoring for that platform (not all 5 at once). Summarize locked backlog items (just item_numbers, archetypes, platforms) instead of loading full YAML.

**Phase 7 (Campaign Calendar) — multi-platform scheduling:**
- Stagger same-topic posts across the week (not all 5 on same day)
- Default spacing: 24-48 hours between posts in the same topic group (per best practices research: cross-platform stagger of 24-48h avoids duplicate content penalties)
- Add `topic_id` reference to calendar entries

**Phase 9 (Validators) — extend:**
- Run `content-voice-guardrail` per platform (pass platform param)
- Character limit is a hard constraint enforced during authoring (Phase 6 step 2), not just at validation. Catching violations earlier is cheaper than discovering them at validation.

**Edit boundaries — no changes needed:**
- platforms.md is read-only (in the skill's own directory, not an edit target)
- The skill already edits content-backlog.yaml, hook-library.md, hashtag-strategy.md

**Files to edit:**
- `skills/canonical/gtm-artifact-refresh/skill.md` — major rewrite of Phases 1, 5, 6, 7, 9
- `skills/adapters/claude/gtm-artifact-refresh.md` — update to reference new inputs and platforms.md

#### 2.2 content-factory — Skip Text-Only Items

**Changes to `skills/canonical/content-factory/skill.md`:**

**Phase 1 (Load and Validate):**
- Filter: skip any item where `slides` is null or empty (NOT hard-coded to platform names — more resilient to future platforms)
- Log skipped items: "Item 31 — no slides, skipping image generation"
- If ALL requested items lack slides, exit with `slides_generated: 0, items_processed: 0` (not an error)

### Research Insight (architecture review)

> Use `slides is null/empty` as the skip condition rather than hard-coding platform names. If a future platform is text-only, the factory skips it without a code change. The scheduler already handles this correctly by checking for slides presence.

**Phase 2 (Generate Slides):**
- No changes — only processes items that passed filter
- Add retry-with-backoff on Gemini 429 errors: 4s → 8s → 16s, max 3 retries
- Add progress checkpointing: write `progress.yaml` in output directory tracking which slides are complete. Re-runs skip completed slides.

**Phase 3 (Preview + Status Update):**
- Only update `status: generated` for processed items
- Items without slides retain `status: draft`

**Files to edit:**
- `skills/canonical/content-factory/skill.md` — update Phase 1 filter, add retry logic
- `skills/adapters/claude/content-factory.md` — note text-only skip behavior

#### 2.3 content-scheduler — Text-Only Posts and X/Facebook

**Changes to `skills/canonical/content-scheduler/skill.md`:**

**Pre-flight check — add:**
- Verify Postiz channels exist for X and Facebook (call `list_channels()`)
- If a target platform's channel is not connected, warn and skip that item (don't abort entire batch)

**Phase 1 (Load and Validate) — two paths:**

```
For each item_number in input:
  Read item from content-backlog.yaml
  
  IF item has slides AND status == "generated":
    → Visual path: read from state/artifacts/content-factory/<product_id>/item_<NNN>/
    → Upload media, create draft with media
  
  ELIF item has NO slides AND status == "draft":
    → Text path: read caption + hashtags directly from backlog YAML
    → Create draft WITHOUT media upload
    → Status transitions: draft → scheduled (skips "generated")
  
  ELSE:
    → Error: item has slides but status != "generated" — run content-factory first
```

**Contract update:** Add `content-backlog.yaml (read for text-only items + status write)` to dependency list. Currently only listed for status writes.

**Phase 2 (Upload + Create Posts):**
- Add X and Facebook platform settings to Postiz payload
- For text-only posts: omit `image` key from payload (don't send empty list)
- Run `social-post-safety` for all posts regardless of path

**Files to edit:**
- `skills/canonical/content-scheduler/skill.md` — add text-only path, X/Facebook settings, preflight check
- `skills/adapters/claude/content-scheduler.md` — document dual path

#### 2.4 Validator Updates

**content-voice-guardrail:**
- Add `facebook` to accepted platform enum values

**social-post-safety (validator.py):**
- Add X character limit check: warn if caption > 280 chars (soft warning, not hard fail — Premium exists)
- Add Facebook to platform awareness
- Expand `_check_platform_tos` with stub rules for X, Facebook, and Threads
- Add `@mention`/`$cashtag` detection (from Phase 0.2)
- Add cross-platform duplicate content flag: if scheduling a topic group, warn if any two items share >60% text overlap

**Files to edit:**
- `skills/canonical/content-voice-guardrail/skill.md` — expand platform enum
- `packages/tools/social_tools/social_post_safety/validator.py` — add X/Facebook checks, mention detection

#### 2.5 niche-research-brief — Platform Enum Update

**Minor update** — add `facebook` to the platform enum in the contract. The existing contract already includes `[tiktok, instagram, threads, x, youtube]`. Add `facebook` to this list.

**Files to edit:**
- `skills/canonical/niche-research-brief/skill.md` — add facebook to platform enum
- `skills/canonical/niche-research-brief/contract.yaml` — add facebook to platforms list

---

### Phase 3: Integration and Polish

#### 3.1 Update CLAUDE.md

Add to "Available Claude project skills":
```
- **content-performance-review** — (planned) analyze content performance and propose strategy improvements
```

No trigger phrase needed yet (skill deferred to follow-up plan).

**Files to edit:**
- `CLAUDE.md`

#### 3.2 Update Skills Registry

Add placeholder entry for future content-performance-review:

```yaml
# ----- Phase 6 content intelligence feedback -----
  - id: content-performance-review
    name: Content Performance Review
    kind: agentic
    canonical_source: skills/canonical/content-performance-review/skill.md
    owner_agent: gtm
    target_runtimes: [claude]
    fixture_status: planned
    source: internal
    notes: "Deferred until 30+ posts published. See follow-up plan."
```

**Files to edit:**
- `skills/registry.yaml`

#### 3.3 Verification Script

After implementation, run these checks:

```python
# 1. Backward compatibility — existing items pass updated validator:
from packages.tools.product_artifacts.gtm_chain import validate_gtm_chain
result = validate_gtm_chain("catchbook", Path("."))
assert result.ok, f"Existing backlog broke: {result.failures}"

# 2. Text-only Postiz dry run — verify payload without image key:
# Use test channel or mock API call
# Confirm no 400 error from omitted image key

# 3. Platform enum — all 5 values accepted:
for p in ["tiktok", "instagram", "threads", "x", "facebook"]:
    assert p in VALID_PLATFORMS
```

---

## System-Wide Impact

### Interaction Graph

```
Topic in niche-research-memory.yaml
  → gtm-artifact-refresh reads topic + platforms.md
    → Authors up to 5 backlog items (one per platform) with shared topic_id
      → content-voice-guardrail validates each item per platform
      → social-post-safety validates each item
        → Visual items (tiktok, instagram, threads): content-factory generates slides
        → Text items (x, facebook): skip factory
          → content-scheduler creates Postiz drafts
            → Visual: upload media + create draft with media
            → Text: create draft without media
              → Founder reviews + publishes in Postiz UI
```

### State Lifecycle

```
Topic: unused → used_in_content (only after ALL platform items written)
Item:  draft → generated (visual only, after factory) → scheduled (after scheduler)
Item:  draft → scheduled (text-only, skips generated state)
```

**Partial failure handling:** If authoring generates 3 of 5 platform items before crashing, `used_in_content` is NOT set. Partial topic groups are valid — each item is independently useful as a draft. On re-run, the skill detects existing items by topic_id and only generates missing platforms (idempotent).

### Error Propagation

| Error | Where | Impact | Recovery |
|-------|-------|--------|----------|
| Postiz missing X channel | content-scheduler preflight | X posts skipped, others proceed | Connect X in Postiz |
| X caption > 280 chars | gtm-artifact-refresh Phase 6 | Hard constraint, rewrite during authoring | Automatic — LLM rewrites to fit |
| Topic unsuitable for platform | gtm-artifact-refresh Phase 6 | Platform skipped (min 3) | Normal behavior |
| Gemini 429 rate limit | content-factory Phase 2 | Retry with backoff (4s→8s→16s) | Automatic — 3 retries |
| Gemini retry exhausted | content-factory Phase 2 | Item left as draft | Re-run factory |
| Text item sent to factory | content-factory Phase 1 | Skipped (not error) | Scheduler handles directly |
| Crash mid-topic authoring | gtm-artifact-refresh Phase 6 | Partial items written, used_in_content not set | Re-run generates missing platforms |

---

## Acceptance Criteria

### Functional Requirements

- [ ] gtm-artifact-refresh produces up to 5 backlog items per topic, one per platform
- [ ] Each platform version has a different opening line and angle
- [ ] X posts are authored within 280 characters
- [ ] Facebook posts include a discussion question or community angle
- [ ] Text-only items (X, Facebook) flow directly to scheduling without image generation
- [ ] Visual items (TikTok, Instagram, Threads) continue through existing factory pipeline
- [ ] content-scheduler creates text-only Postiz drafts (no media) for X and Facebook
- [ ] content-scheduler creates media-attached Postiz drafts for visual platforms
- [ ] Existing 25 backlog items continue to work unchanged (backward compatible)
- [ ] platforms.md exists with all 5 platform sections
- [ ] MCP threat model updated for X and Facebook
- [ ] Postiz API key migrated to Keychain

### Non-Functional Requirements

- [ ] No increase in Gemini API calls for existing visual platforms
- [ ] Postiz text-only posts don't trigger media upload errors (image key omitted, not empty)
- [ ] Backward compatible: items without `topic_id` still pass validation
- [ ] Topics-per-invocation capped at 3-5 to prevent context window degradation
- [ ] Gemini calls have retry-with-backoff (4s → 8s → 16s, max 3)
- [ ] YAML writes are atomic (tmp + rename)

### Quality Gates

- [ ] platforms.md reviewed for accuracy against current platform rules
- [ ] social-media-publishing-nuances.md updated with X and Facebook sections
- [ ] Verification script passes (backward compat, text-only dry run, platform enum)
- [ ] skills/registry.yaml updated

---

## Dependencies & Prerequisites

1. **Postiz X/Facebook channels** — must be connected in Postiz before content-scheduler can create drafts. Requires public-facing callback URL for OAuth setup.
2. **Postiz API support** — Confirmed: Postiz supports X and Facebook. Test with manual curl request before implementing scheduler changes.
3. **MCP threat model** — must be updated and acknowledged before GTM lane is unblocked.
4. **Gemini API key** — no change, only used for visual items.

## Risk Analysis & Mitigation

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|-----------|
| Postiz X/Facebook payload quirks | Medium | Delays Phase 2.3 | Test with curl first; document in nuances.md |
| gtm-artifact-refresh context saturation | Medium | Quality degrades on later items | Cap at 3-5 topics/invocation; load platform sections lazily |
| Content quality drops with 5x output | Medium | Weak posts dilute brand | Voice guardrail per platform; founder reviews all drafts |
| Existing items break with schema changes | Low | Lost progress | Null-guarded validation; no required field changes |
| Gemini rate limits with larger batches | Medium | Partial batch failure | Retry-with-backoff; progress checkpointing; idempotent re-runs |

---

## Deferred to Follow-Up Plan

These items are intentionally excluded from this plan and will be addressed once 30+ posts are published:

1. **content-performance-review skill** — Weekly feedback loop (hooks, archetype weights, platform-tone refinements). Requires performance data that doesn't exist yet.
2. **Audience segmentation** — expert.md / casual.md persona files with `audience` field on backlog items. Requires data on which segments engage where.
3. **Hook platform tagging** — `Platforms:` tag in hook-library.md. Deferred until hook selection quality proves to be a problem.
4. **Per-archetype chain ordering** — Different authoring sequences per archetype. Deferred until performance data reveals which archetypes work best on which platforms.
5. **Performance data ingestion** — Automated reading of Postiz/platform analytics into performance-log.md. Required for the performance review skill.

---

## Sources & References

### Origin

- **Brainstorm document:** [docs/brainstorms/2026-04-13-gtm-multi-platform-engine-brainstorm.md](docs/brainstorms/2026-04-13-gtm-multi-platform-engine-brainstorm.md) — Key decisions: flat backlog with topic_id, extend gtm-artifact-refresh (not new skill), shared playbooks with product overrides

### Internal References

- GTM artifact refresh skill: `skills/canonical/gtm-artifact-refresh/skill.md`
- Content factory skill: `skills/canonical/content-factory/skill.md`
- Content scheduler skill: `skills/canonical/content-scheduler/skill.md`
- Postiz client: `packages/tools/social_tools/postiz_client.py`
- Social media publishing nuances: `docs/solutions/integration-issues/social-media-publishing-nuances.md`
- Content pipeline orchestration: `docs/solutions/integration-issues/content-pipeline-multi-tool-orchestration.md`
- GTM chain validator: `packages/tools/product_artifacts/gtm_chain.py`
- Backlog: `docs/products/catchbook/gtm/content-backlog.yaml`

### Institutional Learnings Applied

- Never ask Gemini to render text (use Pillow) — from `content-pipeline-multi-tool-orchestration.md`
- Both `id` and `path` required for Postiz media attachment — from `social-media-publishing-nuances.md`
- Rate-limit delays must be 4s minimum for Gemini free tier — from `content-pipeline-multi-tool-orchestration.md`
- Platform settings are mandatory per platform (cryptic 400 errors without) — from `social-media-publishing-nuances.md`
- X settings not yet tested for publishing — document learnings when first post goes live — from `social-media-publishing-nuances.md`

### External Research (2026)

- X algorithm: replies worth 27x a like, conversations 150x. External links get near-zero distribution for non-Premium. Posts lose ~50% visibility every 6 hours.
- Facebook algorithm: Shares-to-Stories and Saves worth 50+ Likes. Reels get 3-5x reach. Account "tag" built from last 9-12 posts — scattered topics kill reach.
- Cross-platform: stagger posting 24-48 hours between platforms to avoid duplicate content penalties.
- Postiz: confirmed support for X and Facebook (30+ platforms total). REST API compatible with automation.

### Review Agent Findings Applied

- **Architecture:** Use `slides is null` for factory skip (not platform names). Add `performance-review.md` as future read dependency for gtm-artifact-refresh.
- **Simplicity:** Dropped format enum, audience field, platform suitability scores, hook platform tags, formal litmus test, chain ordering. ~35% plan complexity reduction.
- **Agent-native:** Added idempotent re-run, atomic writes, progress checkpointing. Flagged performance data ingestion as a gap for future plan.
- **Pattern consistency:** Added contract.yaml requirement for future skills. Noted platform enum mismatch (niche-research-brief has youtube, not facebook — fixed in Phase 2.5).
- **Performance:** Capped topics-per-invocation at 3-5. Added Gemini retry-with-backoff. Added lazy platform loading. Added Postiz rate-limit delay.
- **Security:** Added threat model update, Keychain migration, content injection checks, filename sanitization, draft-only assertion.
- **Migration:** Added null-guarded validation, explicit Postiz payload fix, item_number sequencing rule, verification script.
