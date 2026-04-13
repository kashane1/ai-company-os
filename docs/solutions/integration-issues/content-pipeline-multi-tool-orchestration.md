---
title: "GTM Content Pipeline — Multi-Tool Orchestration from Research to Social Media"
category: integration-issues
tags:
  - gtm
  - content-pipeline
  - gemini
  - pillow
  - postiz
  - yaml-migration
  - social-media
  - catchbook
module: worker-gtm
symptom: |
  The GTM pipeline could research niches and create a scored content backlog,
  but could not produce finished visual content or publish to social media.
  Zero posts had been published despite a 37-item backlog with research data.
root_cause: |
  Missing infrastructure between content ideation (gtm-artifact-refresh) and
  manual publishing. Three critical gaps: no visual asset generation, no text
  composition tool, and an incorrectly wired Postiz API client. The backlog
  format (flat markdown) could not hold the per-slide metadata needed for
  production.
date_solved: 2026-04-12
---

# GTM Content Pipeline — Multi-Tool Orchestration

## Problem

The Catchbook GTM pipeline had working research and strategy layers
(niche-research-brief, gtm-artifact-refresh) but no way to turn scored
topics into finished visual content or push it to social media drafts.
The founder was bottlenecked at zero published posts.

## Investigation Steps

1. Attempted to use `generate_slide_set()` in gemini_images.py to produce
   full slides with text baked in via Gemini prompts. Result: garbled text
   rendering ("WANKO STYILE" instead of "Wacky Style", mangled headlines).

2. Discovered Gemini is good at atmospheric backgrounds but unreliable for
   text rendering. Decided to split: Gemini for backgrounds, Pillow for text.

3. Found the Postiz client's `create_draft_post()` used a flat `channelId`
   payload that the API rejected. The real API requires a deeply nested
   structure with `posts[].integration.id`, `value[].image[{id, path}]`,
   and platform-specific settings.

4. Realized the markdown backlog format (numbered list of one-liners) could
   not hold per-slide text, visual direction, captions, and hashtags needed
   for the content factory.

## Root Cause

Four infrastructure gaps:

1. **Format gap**: Backlog was flat markdown — couldn't hold per-item slide
   specs, visual hints, captions, or hashtags.
2. **Gemini antipattern**: The client asked Gemini to render text on images.
   Gemini produces garbled typography. Text rendering must be deterministic.
3. **Postiz API mismatch**: The client payload structure was wrong. Postiz
   requires nested `posts[]` with `integration: {id}` and platform-specific
   `settings` (TikTok needs privacy_level, duet, stitch, comment, etc.;
   Instagram needs post_type).
4. **Missing tool**: No Pillow-based text compositor existed for deterministic
   text overlay on generated backgrounds.

## Working Solution

### 1. Backlog migration (markdown to YAML)

One-time Python script parsed the 37 markdown items into structured YAML
with typed fields. Chain validator (`gtm_chain.py`) updated atomically in
the same commit to prevent breaking the live-repo test.

Key: preserve `item_number` values so `backlog_item_number` cross-references
in `niche-research-memory.yaml` remain valid.

### 2. Gemini client — background-only generation

Changed the prompt suffix from requesting "legible text overlays" to
explicitly excluding text:

```python
# Before (garbled text)
"Style: clean, modern, high contrast, legible text overlays. No watermarks."

# After (clean backgrounds)
"No text, no writing, no logos, no watermarks, no UI elements. Background image only."
```

Also raised `urlopen` timeout from 60s to 120s and deleted ~120 lines of
dead code (`generate_slide_set`, `generate_weekly_stockpile`, `SlideSet`).

### 3. Pillow text overlay — alpha compositing pattern

**Critical gotcha: `ImageDraw` does NOT alpha-blend.** Drawing a
semi-transparent rectangle with `fill=(0, 0, 0, 128)` replaces pixels
instead of blending. Must use a separate RGBA layer:

```python
# WRONG — ImageDraw replaces, does not blend
draw = ImageDraw.Draw(base)
draw.rectangle(region, fill=(0, 0, 0, 128))  # No transparency!

# RIGHT — separate overlay + alpha_composite
base = base.convert("RGBA")
overlay = Image.new("RGBA", base.size, (0, 0, 0, 0))
overlay_draw = ImageDraw.Draw(overlay)
overlay_draw.rectangle(region, fill=(0, 0, 0, 178))  # 70% opacity
base = Image.alpha_composite(base, overlay)
```

Other Pillow patterns:
- **Font caching**: `@lru_cache(maxsize=16)` on `ImageFont.truetype()` calls
- **Dynamic font sizing**: Binary search between min/max pt sizes
- **Text wrapping**: `draw.textlength()` for word-level line breaking
- **Safe zones**: 120px top, 200px bottom, 80px sides for TikTok/Reels
- **Use static .ttf**: Variable Montserrat font renders poorly in Pillow;
  use the static `Montserrat-Bold.ttf` weight file

### 4. Postiz API — correct payload structure

The API requires a nested structure, not flat fields:

```python
payload = {
    "type": "draft",
    "date": schedule_date.isoformat(),
    "posts": [{
        "integration": {"id": channel_id},  # NOT "channelId"
        "value": [{
            "content": caption,
            "image": [
                {"id": media_id, "path": media_url}  # from upload response
            ],
        }],
        "settings": platform_settings,  # platform-specific!
    }],
}
```

Platform-specific settings required:

- **TikTok**: `privacy_level`, `duet`, `stitch`, `comment`, `autoAddMusic`,
  `brand_content_toggle`, `brand_organic_toggle`, `content_posting_method`
- **Instagram**: `post_type` ("post" or "story")

The upload endpoint returns `{id, path}` where `path` is a URL — both must
be passed in the `image` array of the post payload.

### 5. Rate limiting — 4-second delay, not 2

Gemini free tier is 15 req/min. A 2-second delay yields ~30 req/min,
overshooting by 2x and triggering 429 errors. Use 4-second delays to match
the rate limit exactly. For a 3-slide post, total generation time is ~20
seconds (3 API calls + 2 inter-call delays).

## Prevention Strategies

1. **Never ask generative AI to render text on images.** Split concerns:
   AI generates visuals, deterministic tools render typography.

2. **Always use `Image.alpha_composite()` for transparency in Pillow.**
   Never rely on ImageDraw's RGBA fill — it does not blend.

3. **Test external API payloads with curl first.** Before coding a client,
   verify one successful request manually and document the exact payload.

4. **Calculate rate limit delays from the limit**, not from intuition:
   `delay = 60 / requests_per_minute` (15 req/min = 4 sec minimum).

5. **Make data format migrations atomic.** Update the validator, migrate the
   data, and fix all references in the same commit. Grep for all references
   to the old format before starting.

6. **Use static font weight files with Pillow.** Variable fonts
   (`Font[wght].ttf`) render inconsistently. Download the specific weight
   file (`Font-Bold.ttf`) from Google Fonts' `static/` subfolder.

## Related Files

- **Brainstorm**: `docs/brainstorms/2026-04-12-content-pipeline-skills-brainstorm.md`
- **Plan**: `docs/plans/2026-04-12-feat-content-pipeline-skills-plan.md`
- **Text overlay**: `packages/tools/content_tools/text_overlay.py`
- **Gemini client**: `packages/tools/content_tools/gemini_images.py`
- **Postiz client**: `packages/tools/social_tools/postiz_client.py`
- **Chain validator**: `packages/tools/product_artifacts/gtm_chain.py`
- **Content factory skill**: `skills/canonical/content-factory/skill.md`
- **Content scheduler skill**: `skills/canonical/content-scheduler/skill.md`
- **YAML backlog**: `docs/products/catchbook/gtm/content-backlog.yaml`
- **Location model rollout**: `docs/solutions/integration-issues/catchbook-layered-location-model-rollout.md`
