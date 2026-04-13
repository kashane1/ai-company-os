---
title: "feat: Content Pipeline Skills"
type: feat
status: active
date: 2026-04-12
origin: docs/brainstorms/2026-04-12-content-pipeline-skills-brainstorm.md
deepened: 2026-04-12
---

## Enhancement Summary

**Deepened on:** 2026-04-12
**Sections enhanced:** All 6 phases + acceptance criteria
**Research agents used:** Pillow best practices, Gemini image API, architecture
strategist, code simplicity reviewer, performance oracle

### Key Improvements
1. Simplified status lifecycle from 5 states to 3 (`draft → generated → scheduled`)
2. Flattened hashtags to single list (scheduler handles platform limits)
3. Separated backlog migration as a one-time script (removes dual-format parsing)
4. Added concrete Pillow rendering code with safe zones, alpha compositing, font caching
5. Updated Gemini prompt strategy with style anchors and 2K resolution
6. Changed inter-request delay from 2s to 4s (matches free-tier rate limit exactly)
7. Removed soft voice guardrail, manifest generation, and unused dataclasses (YAGNI)

### New Considerations Discovered
- Pillow's `ImageDraw` does NOT alpha-blend — must use `Image.alpha_composite()`
- Use static Montserrat-Bold.ttf, not the variable font (Pillow renders it poorly)
- Gemini 2K at 9:16 produces ~1152x2048 — slight downscale to 1080x1920 is ideal
- Phase 1a (validator update) and migration must be atomic to avoid breaking live test
- Content-factory has an edit boundary violation — must declare backlog YAML write access

# Content Pipeline Skills

## Overview

Build the missing Lane 3 (Content Factory) and Lane 4 (Content Scheduler)
of the GTM pipeline for Catchbook. This also modifies the existing
gtm-artifact-refresh skill to author full slide text in a new YAML backlog
format, and adds a Pillow-based text overlay utility.

The end-to-end pipeline after this work:

```
niche-research-brief → gtm-artifact-refresh (authors slides in YAML)
→ content-factory (Gemini backgrounds + Pillow text) → human preview
→ content-scheduler (Postiz drafts) → human publishes from phone
```

(see brainstorm: `docs/brainstorms/2026-04-12-content-pipeline-skills-brainstorm.md`)

## Problem Statement

The GTM pipeline can research niches, score topics, and create a content
backlog — but it cannot produce finished visual content or push it to social
media drafts. The founder must manually create images, write captions, and
upload to Postiz. This bottleneck means zero posts have been published.

## Proposed Solution

Four deliverables, built in dependency order:

1. **Migrate backlog to YAML + update chain validator** (unblocks everything)
2. **Pillow text overlay utility** (`text_overlay.py`)
3. **content-factory skill** (Gemini backgrounds + Pillow text → finished slides)
4. **content-scheduler skill** (validated slides → Postiz drafts)

Plus modifications to existing code:
- gtm-artifact-refresh: output YAML with full slide specs
- gemini_images.py: remove text-overlay prompt suffix, add retry logic
- gtm_chain.py: parse YAML instead of markdown
- 6 skill/adapter files: update `content-backlog.md` references to `.yaml`

## Technical Approach

### Phase 1: Foundation (unblocks all other phases)

#### 1a. Migrate backlog to YAML + update chain validator (ATOMIC)

These two steps must land in the same commit to avoid breaking the live-repo
test (`test_real_catchbook_chain_valid`).

**Step 1: One-time migration script** (throwaway, do not commit)

Write a 30-line Python script that reads `content-backlog.md`, parses the
numbered items, and outputs `content-backlog.yaml` with minimal fields:
`item_number`, `hook`, `archetype`, `platform`, `campaign`, `composite_score`,
`status: draft`, `topic_id` (null for pre-research items 18-30). Preserve
`item_number` values to keep `backlog_item_number` cross-references valid in
`niche-research-memory.yaml`. Run once, verify, delete script.

**Step 2: Update chain validator**

**File:** `packages/tools/product_artifacts/gtm_chain.py`

- Change `REQUIRED_FILES`: replace `content-backlog.md` with `content-backlog.yaml`
- Replace markdown line-counting with YAML parsing (`yaml.safe_load()`,
  count items in the list)
- Keep the 14-item minimum check
- Add `validate_backlog_item(item: dict) -> list[str]` function that checks
  required fields: `item_number`, `hook`, `archetype`, `platform`, `campaign`,
  `status`. Return list of error strings (empty = valid). Reuse this validator
  from the content-factory and content-scheduler pre-flight checks.

**File:** `tests/python/unit/test_gtm_chain_validator.py`

- Update all 4 tests to write `.yaml` instead of `.md`
- `test_real_catchbook_chain_valid` now validates the migrated YAML file

**Step 3: Delete `content-backlog.md`** after migration is verified.

#### 1b. Modify generate_image() prompt suffix

**File:** `packages/tools/content_tools/gemini_images.py`

Current suffix (line 93):
`"Style: clean, modern, high contrast, legible text overlays. No watermarks."`

Change to:
`"No text, no writing, no logos, no watermarks, no UI elements. Background image only."`

This prevents Gemini from rendering text (Pillow handles text now).

Also raise `urlopen` timeout from 60s to 120s (image generation can be slow
for detailed prompts).

### Research Insights: Gemini Image API

**Prompt patterns for clean backgrounds:**
- Use narrative descriptions, not keyword lists
- Always include explicit exclusions: "no text, no writing, no logos"
- Use "semantic negative prompts" — describe what you want positively
  rather than listing what to exclude
- Include camera language: lens type, lighting, angle

**Resolution:** Use `image_size="2K"` for 9:16 output (~1152x2048). This is
slightly above 1080x1920, so Pillow can downscale to exact target size
with no quality loss.

**Visual consistency across slides:** Use a style anchor prefix prepended to
every prompt in a slide set:
```
STYLE_ANCHOR = "Warm-toned palette of terracotta and cream. Soft watercolor
texture, matte finish, gentle ambient lighting. No text, no writing, no logos."
```

**Rate limiting (free tier):** 2 IPM (images per minute), ~500 RPD (per day).
At 2 images/minute, a 3-slide post takes ~90 seconds. A weekly batch of 5
posts (15 slides) takes ~8 minutes. This is sufficient for the current scale.

**Skip retry logic in v1.** The 4-second inter-call delay (see Phase 4)
already provides implicit rate limiting. If a 429 occurs, the error message
from the existing code is clear enough for the founder to re-run. Add retry
logic later if rate limits become a real problem.

**Output format:** Save backgrounds as JPEG (Gemini returns JPEG by default).
Convert to JPEG quality=90 after Pillow compositing for final slides.

#### 1c. Delete dead code in gemini_images.py

Delete `generate_slide_set()`, `generate_weekly_stockpile()`,
`_generate_hashtags()`, and the `SlideSet` dataclass. These are fully replaced
by the content-factory skill. They have zero callers. The code is in git
history if needed.

This removes ~120 lines and eliminates a competing pipeline.

#### 1d. Add Pillow to project dependencies

**File:** `pyproject.toml`

Add `"Pillow>=11,<12"` to `dependencies` list.

#### 1e. Bundle Montserrat Bold font

**Files:**
- `packages/tools/content_tools/fonts/Montserrat-Bold.ttf`
- `packages/tools/content_tools/fonts/OFL.txt`

Download the **static** weight file from Google Fonts (not the variable font).
Pillow renders static `.ttf` files more reliably than variable `Montserrat[wght].ttf`.
Include the SIL Open Font License alongside.

---

### Phase 2: Text Overlay Utility

**File:** `packages/tools/content_tools/text_overlay.py` (~200 lines)

Pure Python, deterministic, no AI. Uses Pillow (PIL) for image compositing.

**Dataclass:**

```python
@dataclass
class SlideTextConfig:
    headline: str | None = None
    subhead: str | None = None
    bullets: list[str] | None = None
    body: str | None = None
```

**Functions:**

```python
def overlay_text(
    background_path: Path,
    text_config: SlideTextConfig,
    output_path: Path,
    overlay_alpha: int = 178,          # 0-255, ~70% opacity
    target_size: tuple[int, int] = (1080, 1920),
) -> Path

def compose_post(
    backgrounds: list[Path],
    text_configs: list[SlideTextConfig],
    output_dir: Path,
    item_number: int,
) -> list[Path]  # returns output file paths
```

**Rendering rules** (see brainstorm section 3a):
- `headline` only → centered vertically, large font (72-96pt auto-sized)
- `headline` + `subhead` → headline upper-third, subhead center (48-56pt)
- `headline` + `bullets` → headline top, bullets stacked center (36-44pt each)
- `headline` + `body` → headline top, body paragraph below (36pt)
- Background resized/cropped to 1080x1920 (9:16 TikTok/Reels)
- Font: Montserrat Bold (static .ttf), cached with `@lru_cache(maxsize=16)`
- Text wrapping via `draw.textlength()` with word-level line breaking
- Dynamic font sizing via binary search to fit text within bounds
- Output as JPEG quality=90 (not PNG — faster and sufficient for social)

### Research Insights: Pillow Text Rendering

**Critical: ImageDraw does NOT alpha-blend.** Drawing a semi-transparent
rectangle with `fill=(0,0,0,128)` directly REPLACES pixels instead of blending.
Must use a separate RGBA overlay layer + `Image.alpha_composite()`:

```python
base = Image.open(bg_path).resize((1080, 1920)).convert("RGBA")
overlay = Image.new("RGBA", base.size, (0, 0, 0, 0))
overlay_draw = ImageDraw.Draw(overlay)
overlay_draw.rectangle(region, fill=(0, 0, 0, overlay_alpha))
base = Image.alpha_composite(base, overlay)
```

**Safe zones for TikTok/Reels (1080x1920):**
- Top: 120px (platform UI clearance)
- Bottom: 200px (captions + action buttons)
- Side margins: 80px each (text area width = 920px)
- Usable text region: ~1600px height

**Recommended overlay alpha values:**
- 153 (60%) — light, for already-dark backgrounds
- 178 (70%) — standard, most versatile
- 204 (80%) — heavy, for text-heavy slides

**Font sizing ranges (at 1080x1920):**
- Headlines: 48-96pt (binary search within range)
- Subheads: 36-56pt
- Bullets/body: 28-44pt
- Line spacing: 8px (Pillow default 4px is too tight for social)
- Block spacing: 24-40px between headline and body

**Text wrapping gotchas:**
- `textlength()` does not accept newlines — split by `\n` first
- Kerning means character-by-character width sums are wrong — measure full strings
- `textbbox()` may return negative top values for Montserrat Bold ascender overshoot
- Always use `bbox[3] - bbox[1]` for height, not just `bbox[3]`

**Output naming:** `item_{item_number:03d}_slide_{slide_number}.jpg`

---

### Phase 3: Modify gtm-artifact-refresh for YAML Output

**Files to modify:**
- `skills/canonical/gtm-artifact-refresh/skill.md` — rewrite Phase 6 (backlog
  creation) to output YAML with full slide specs
- `skills/adapters/claude/gtm-artifact-refresh.md` — update quick reference
  and boundary list
- `.claude/skills/gtm-artifact-refresh.md` — update description if needed

**What changes in the refresh skill:**

Phase 6 currently writes markdown numbered list items. New behavior:

1. Read existing `content-backlog.yaml` (or create empty list if missing)
2. Lock items already scheduled or published (do not modify)
3. For each unused topic (sorted by composite score):
   a. Select archetype-based slide template (see brainstorm table)
   b. Author full slide text using research context (topic description,
      source evidence, lexicon vocabulary)
   c. Write `visual_hint` per slide (Gemini prompt keywords, no text
      instructions)
   d. Write platform-specific caption
   e. Select hashtag combos from `hashtag-strategy.md` per platform
4. Append new items to the YAML list
5. Run archetype mix balance check (same logic, now on YAML data)
6. Write `content-backlog.yaml`

**YAML item schema** (from brainstorm, simplified per review):

```yaml
- item_number: int
  hook: string
  archetype: enum  # value_educational | pain_point | debate_hot_take |
                   # identity_tribal | aspirational_aesthetic |
                   # humor_relatable | seasonal_timely | behind_the_scenes
  platform: enum   # tiktok | instagram | threads
  campaign: enum   # zero | one
  composite_score: int
  topic_id: string | null     # null for pre-research items (18-30)
  status: enum     # draft | generated | scheduled
  slides:
    - slide: int
      text:
        headline: string | null
        subhead: string | null
        bullets: list[string] | null
        body: string | null
      visual_hint: string
  caption: string
  hashtags: list[string]      # flat list; scheduler trims to platform limit
```

**Status lifecycle (3 states, not 5):**
- `draft` — created by refresh, ready for factory
- `generated` — factory produced slides, awaiting scheduling
- `scheduled` — scheduler pushed to Postiz as draft

Removed `approved` (nothing sets it) and `published` (tracked in Postiz, not YAML).

**Hashtags are a flat list.** The content-scheduler applies platform-specific
limits from `PLATFORM_HASHTAG_LIMITS` in `postiz_client.py` at post creation
time (TikTok max 5, Instagram max 8, Threads max 3). This avoids duplicating
platform decisions during authoring.

**Archetype-to-template defaults:**

| Archetype | Slides | Layout |
|---|---|---|
| value_educational | 3 | headline + 3 bullets + closing question |
| pain_point | 2 | provocative headline + resolution |
| debate_hot_take | 2 | claim + counter-argument |
| identity_tribal | 2 | identity statement + closer |
| aspirational_aesthetic | 2 | short text + visual emphasis |
| humor_relatable | 2 | setup + punchline |
| seasonal_timely | 3 | headline + seasonal detail + closer |
| behind_the_scenes | 3 | headline + data/insight + reflection |

**Campaign Zero CTA rules:** No product mentions. Slide 3 (if present) uses
engagement closers: "Which one's your go-to?", "Save this for your next trip",
"Drop your answer below."

**Migration:** Already handled in Phase 1a (one-time script). By the time
the refresh skill is modified, `content-backlog.yaml` already exists with
all 37 items in minimal YAML format (no slides yet). The first refresh run
after this modification authors full slide text for all `status: draft` items.

**Lock rule:** The refresh skill must lock items with status in
`{generated, scheduled}` — do not modify their slides, captions, or
visual_hints, as the factory may have already produced images from them.

**Additional files to update** (6 references to `content-backlog.md`):
- `skills/canonical/niche-research-brief/skill.md` — line reading backlog
- `skills/adapters/claude/niche-research-brief.md` — boundary list
- `docs/claude-orchestrator-readiness-plan.md` — documentation reference
- `niche-research-memory.yaml` — historical `artifacts_updated` entries left
  as-is; future runs write `.yaml`

---

### Phase 4: content-factory Skill

**Files to create:**
- `skills/canonical/content-factory/skill.md`
- `skills/adapters/claude/content-factory.md`
- `.claude/skills/content-factory.md`

**Contract:**

```
Inputs:
  - product_id: string
  - item_numbers: list[int]  # which backlog items to generate

Outputs:
  - output_dir: string
  - slides_generated: int
  - items_processed: int

Allowed edit boundaries:
  - state/artifacts/content-factory/<product_id>/
  - docs/products/<product_id>/gtm/content-backlog.yaml (status field only)

Forbidden areas:
  - apps/, packages/, infra/, products/

Dependencies:
  - Reads: docs/products/<product_id>/gtm/content-backlog.yaml
  - Uses: packages/tools/content_tools/gemini_images.generate_image()
  - Uses: packages/tools/content_tools/text_overlay.compose_post()
  - Uses: packages/tools/product_artifacts/gtm_chain.validate_backlog_item()
```

**Pipeline per item:**

1. Read item from `content-backlog.yaml` by `item_number`
2. Validate item with `validate_backlog_item()` — abort with clear error
   listing missing fields
3. For each slide in item:
   a. Call `generate_image(visual_hint, aspect_ratio="9:16")` — Gemini returns
      ~1152x2048 at 2K setting
   b. Save background as temp JPEG
   c. Build `SlideTextConfig` from slide's `text` fields
   d. Call `overlay_text(background, text_config, output_path)` — Pillow
      resizes to 1080x1920, applies dark overlay, renders text, saves JPEG
   e. Delete temp background (free memory before next Gemini call)
   f. Sleep 4 seconds before next `generate_image()` call (matches 15 req/min
      free tier exactly)
4. Write caption + hashtags to `metadata.yaml` sidecar
5. Open output directory in Finder: `subprocess.run(["open", output_dir])`
6. Update item `status` to `generated` in `content-backlog.yaml`

**Output directory:** `state/artifacts/content-factory/<product_id>/item_<NNN>/`

**Output files per item:**
```
item_002/
  slide_1.png
  slide_2.png
  slide_3.png      # only if 3-slide item
  metadata.yaml    # caption, hashtags, platform, archetype
```

**Rate limiting:** 4-second delay between `generate_image()` calls (matches
free-tier 15 req/min exactly — avoids 429 retries). For a 3-slide item,
that's ~20 seconds total. For a batch of 5 three-slide items, ~90 seconds.

---

### Phase 5: content-scheduler Skill

**Files to create:**
- `skills/canonical/content-scheduler/skill.md`
- `skills/adapters/claude/content-scheduler.md`
- `.claude/skills/content-scheduler.md`

**Contract:**

```
Inputs:
  - product_id: string
  - item_numbers: list[int]
  - channel_ids: dict[str, str]  # e.g. {"tiktok": "ch_123"}
  - scheduled_date: string       # ISO 8601 date

Outputs:
  - posts_created: int
  - platforms: list[str]
  - post_ids: list[str]

Allowed edit boundaries:
  - docs/products/<product_id>/gtm/content-backlog.yaml (status field only)

Forbidden areas:
  - apps/, packages/, infra/, products/

Dependencies:
  - Reads: state/artifacts/content-factory/<product_id>/item_<NNN>/
  - Uses: packages/tools/social_tools/postiz_client.upload_media()
  - Uses: packages/tools/social_tools/postiz_client.create_draft_post()
  - Uses: packages/tools/product_artifacts/gtm_chain.validate_backlog_item()
  - Validates with: social-post-safety (hard gate)
```

**Pipeline per item:**

1. Read item's generated slides from `state/artifacts/content-factory/`
2. Read `metadata.yaml` for caption and hashtags
3. Run `social-post-safety` validator on caption (hard gate — abort on failure)
4. For each platform in `channel_ids`:
   a. Upload each slide image via `upload_media()`
   b. Collect media IDs
   c. Trim hashtags to platform limit (TikTok 5, Instagram 8, Threads 3)
   d. Call `create_draft_post(channel_id, caption, media_ids, hashtags,
      platform, scheduled_at)`
5. Update item `status` to `scheduled` in `content-backlog.yaml`
6. Print summary: item number, platforms, post IDs

**Uses `create_draft_post()` per-item** — NOT `schedule_content_batch()`,
which requires exactly 3 slides and would silently skip 2-slide items.

**Posts always go to DRAFT status.** Never direct publish.

**No manifest files in v1.** The Postiz dashboard shows all drafts, and the
backlog YAML's `status: scheduled` field tracks which items have been pushed.
Add manifest generation if multi-person review becomes a requirement.

---

### Phase 6: Registry + Trigger Phrases

**File:** `skills/registry.yaml`

Add under a new section comment `# ----- Phase 5 content pipeline skills -----`:

```yaml
- id: content-factory
  name: Content Factory
  path: canonical/content-factory/skill.md
  owner_agent: gtm
  target_runtimes: [claude]
  stage: active
  kind: agentic
  fixture_status: missing
  source: internal
  adapters:
    claude: adapters/claude/content-factory.md
  project_skill: .claude/skills/content-factory.md

- id: content-scheduler
  name: Content Scheduler
  path: canonical/content-scheduler/skill.md
  owner_agent: gtm
  target_runtimes: [claude]
  stage: active
  kind: agentic
  fixture_status: missing
  source: internal
  adapters:
    claude: adapters/claude/content-scheduler.md
  project_skill: .claude/skills/content-scheduler.md
```

**File:** `CLAUDE.md`

Add trigger phrases:

```
- "create content" / "generate slides" / "make posts" / "run the content factory"
  → skills/adapters/claude/content-factory.md
- "schedule posts" / "push to postiz" / "send to drafts" / "schedule content"
  → skills/adapters/claude/content-scheduler.md
```

## Acceptance Criteria

### Phase 1: Foundation
- [ ] `content-backlog.yaml` exists with all 37 items (migrated from .md)
- [ ] `content-backlog.md` deleted
- [ ] `gtm_chain.py` validates `.yaml` with `validate_backlog_item()` function
- [ ] All 4 chain validator tests pass with YAML format
- [ ] `generate_image()` prompt suffix says "no text, no writing" (background only)
- [ ] `generate_image()` timeout raised to 120s
- [ ] `generate_slide_set()`, `generate_weekly_stockpile()`, `SlideSet` deleted
- [ ] Pillow declared in `pyproject.toml`
- [ ] Static Montserrat-Bold.ttf + OFL license bundled in `fonts/`

### Phase 2: Text Overlay
- [ ] `overlay_text()` renders headline-only, headline+subhead, headline+bullets,
      and headline+body layouts correctly
- [ ] Dark overlay uses `Image.alpha_composite()` (not direct ImageDraw)
- [ ] Dynamic font sizing via binary search fits text within safe zones
- [ ] Text is legible on both light and dark backgrounds
- [ ] Output images are 1080x1920 JPEG quality=90
- [ ] Long text wraps without overflow
- [ ] Font loaded with `@lru_cache` (no repeated disk reads)

### Phase 3: Refresh Skill Modification
- [ ] `gtm-artifact-refresh` outputs `content-backlog.yaml` with full slide specs
- [ ] Each item has slides array with text + visual_hint per slide
- [ ] Archetype-based template selection works for all 8 archetypes
- [ ] Campaign Zero items never contain app mentions in any field
- [ ] Refresh locks items with status in {generated, scheduled}
- [ ] Archetype mix balance check works on YAML data
- [ ] All files referencing `content-backlog.md` updated to `.yaml`

### Phase 4: Content Factory
- [ ] Reads items from `content-backlog.yaml` by number
- [ ] Validates items with `validate_backlog_item()` before processing
- [ ] Generates one background per slide via Gemini (no text in prompt)
- [ ] 4-second delay between Gemini calls (matches free-tier rate limit)
- [ ] Overlays text via Pillow using slide's text config
- [ ] Outputs slides to `state/artifacts/content-factory/<product_id>/item_<NNN>/`
- [ ] Auto-opens output folder in Finder after generation
- [ ] Handles both 2-slide and 3-slide items
- [ ] Updates item status to `generated` in backlog YAML

### Phase 5: Content Scheduler
- [ ] Reads generated slides from content-factory output directory
- [ ] Runs `social-post-safety` hard gate before any upload
- [ ] Uploads slides and creates draft posts via Postiz per-item
- [ ] Trims hashtags to platform limit at post creation time
- [ ] Creates drafts on both TikTok and Instagram when both channels specified
- [ ] Updates item status to `scheduled` in backlog YAML

### End-to-End
- [ ] Run refresh on Catchbook fishing niche → produces YAML backlog with slides
- [ ] Run content-factory on item 2 → produces 3 slides, opens in Finder
- [ ] Run content-scheduler on item 2 → creates drafts in Postiz on both channels
- [ ] Verify drafts appear in Postiz dashboard

## Dependencies & Risks

**Dependencies:**
- Gemini API key configured (confirmed working)
- Postiz API key configured (confirmed working, TikTok + Instagram connected)
- Pillow 11.3.0 (installed, needs declaring in pyproject.toml)

**Risks:**
- Gemini rate limit (15 req/min free tier) limits batch size to ~5 three-slide
  posts before delays accumulate. Mitigated by per-call delays + retry logic.
- Font rendering quality in Pillow may not match professional design tools.
  Mitigated by Montserrat Bold (designed for screens) + dim overlay for contrast.
- YAML backlog migration touches a working pipeline. Mitigated by updating
  chain validator first and preserving item numbers.

## Known Limitations (v1)

- No single-slide re-generation (must re-generate entire post)
- No dry-run mode for Gemini prompts
- No support for non-slideshow formats (single image, video, carousel >3)
- Campaign calendar stays markdown (does not migrate to YAML)
- GTM worker task handler stubs not wired (skills work via trigger phrases only)

## Sources & References

### Origin

- **Brainstorm:** [docs/brainstorms/2026-04-12-content-pipeline-skills-brainstorm.md](docs/brainstorms/2026-04-12-content-pipeline-skills-brainstorm.md)
  Key decisions carried forward: YAML backlog format, slide text authored during
  refresh, archetype-based templates, Montserrat Bold font, manual scheduling,
  auto-open preview.

### Internal References

- gtm-artifact-refresh canonical: `skills/canonical/gtm-artifact-refresh/skill.md`
- Chain validator: `packages/tools/product_artifacts/gtm_chain.py`
- Chain validator tests: `tests/python/unit/test_gtm_chain_validator.py`
- Gemini client: `packages/tools/content_tools/gemini_images.py`
- Postiz client: `packages/tools/social_tools/postiz_client.py`
- Skill registry: `skills/registry.yaml`
- Wiring convention: `skills/WIRING.md`
- Content backlog: `docs/products/catchbook/gtm/content-backlog.md`
- Content taxonomy: `docs/products/catchbook/gtm/content-taxonomy.md`
- Hashtag strategy: `docs/products/catchbook/gtm/hashtag-strategy.md`
