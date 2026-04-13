# Brainstorm: Content Pipeline Skills

**Date:** 2026-04-12
**Status:** Complete
**Product:** Catchbook
**Next step:** `/workflows:plan`

## What We're Building

Two new skills and one utility to complete the GTM content pipeline:

1. **Expand gtm-artifact-refresh** to author full slide text and visual
   direction per backlog item (not just one-line hooks)
2. **content-factory** skill — takes authored backlog items, generates
   background images via Gemini, overlays text via Pillow, auto-opens for
   review
3. **content-scheduler** skill — takes approved slides, pushes to Postiz as
   drafts for manual publishing
4. **text_overlay.py** utility — Pillow-based deterministic text compositor

Pipeline: niche-research-brief -> gtm-artifact-refresh (now authors slides)
-> content-factory (images + text overlay) -> human preview -> content-scheduler
(Postiz drafts) -> human publishes from phone

## Why This Approach

The three review agents flagged the original plan as over-engineered and missing
critical design decisions. This brainstorm resolves those gaps:

- **Text sourcing:** Authored during gtm-artifact-refresh when research context
  is richest — not generated at image-creation time
- **Slide flexibility:** Archetype-based templates with per-item storage, so the
  factory just reads and renders
- **Visual direction:** Stored per-item in the backlog, not derived at runtime
- **Preview before upload:** Auto-open generated slides in Finder/Preview for
  human review before scheduling

## Key Decisions

### 1. Text is authored during gtm-artifact-refresh

The refresh skill already has full research context (topics, evidence, lexicon,
archetypes). When it creates backlog items, it now also writes:
- Full text for each slide (headline, body, closing)
- Visual direction hints per slide (Gemini prompt keywords)
- Slide count and layout template
- Platform-specific hashtag set

### 2. Backlog moves from markdown to YAML

The content-backlog.md flat list cannot hold per-slide text and visual
direction. The new format is `content-backlog.yaml` with typed fields per item.

Example item structure:
```yaml
- item_number: 2
  hook: "3 bass lures that work when nothing else does"
  archetype: value_educational
  platform: tiktok
  campaign: zero
  composite_score: 64
  topic_id: three-lures-that-always-work
  slides:
    - slide: 1
      text:
        headline: "Nothing biting?"
        subhead: "Try these 3 lures"
      visual_hint: "underwater bass approaching a lure, murky green water, dramatic lighting"
    - slide: 2
      text:
        headline: "The 3 that always work"
        bullets:
          - "Ned rig — finesse king in clear water"
          - "Senko wacky — the slow fall they can't resist"
          - "Black & blue jig — triggers reaction strikes"
      visual_hint: "three bass lures on weathered wooden dock, morning light, overhead flat lay"
    - slide: 3
      text:
        headline: "Which one's your go-to?"
        subhead: "Drop it below"
      visual_hint: "calm lake surface at golden hour, warm orange and blue tones"
  caption: "3 lures that work when nothing else does. Ned rig for finesse. Senko for that slow fall. Black and blue jig for reaction strikes. Which one's your confidence lure?"
  hashtags:
    tiktok: ["#fishing", "#fishtok", "#bassfishing", "#fishingtips", "#catchandrelease"]
    instagram: ["#fishing", "#bassfishing", "#fishingtips", "#fishinglife", "#catchandrelease", "#largemouthbass", "#catchbookapp", "#loggedit"]
```

### 3. Archetype-based slide templates with per-item override

Default templates by archetype (refresh picks the template, stores result):

| Archetype | Default slides | Default layout |
|---|---|---|
| Value/Educational | 3 | headline + 3 bullets + closing question |
| Pain Point | 2 | provocative headline + "what if" resolution |
| Debate/Hot Take | 2 | claim + counter-argument |
| Identity/Tribal | 2 | identity statement + "if you know, you know" |
| Aspirational/Aesthetic | 2 | short text + emphasis on visual |
| Humor/Relatable | 2 | setup + punchline |
| Seasonal/Timely | 3 | headline + seasonal detail + "your log knows" |
| Behind-the-Scenes | 3 | headline + data/insight + reflection |

Any item can be hand-edited in the YAML to override the template.

### 3a. Slide text field schema

Each slide's `text` object uses these fields. All are optional — the text
overlay utility renders whichever fields are present.

```yaml
text:
  headline: string     # Large text, top of slide. Present on almost every slide.
  subhead: string      # Smaller text below headline. Used for closers, taglines.
  bullets:             # List of short strings. Used for Value/Educational lists.
    - string
  body: string         # Paragraph text. Used for Behind-the-Scenes, longer formats.
```

**Rendering rules for text_overlay.py:**
- `headline` only → centered, large font
- `headline` + `subhead` → headline top-third, subhead center
- `headline` + `bullets` → headline top, bullets stacked center
- `headline` + `body` → headline top, body paragraph below
- Any combination is valid; the overlay utility stacks fields top-to-bottom

### 3b. Migration of existing backlog items

The 37 existing items in content-backlog.md must be migrated to the new YAML
format. Strategy: the next gtm-artifact-refresh run converts all items. Items
already published or scheduled are locked (migrated as-is with minimal slide
text). Unpublished items get full slide text authored from research context.

### 4. Visual direction stored per-item, not derived at runtime

Each slide gets a `visual_hint` field — a short Gemini prompt string describing
the background image. No text instructions in the prompt. The content-factory
passes this directly to `generate_image()`.

### 5. Campaign Zero = no CTA, no app mentions

Posts with `campaign: zero` never get a CTA slide with product mentions.
Slide 3 (if present) uses engagement closers: "Which one's your go-to?",
"Save this for your next trip", "Drop your answer below."

### 6. Each slide gets a different background image

One `generate_image()` call per slide. For a 3-slide post, that's 3 Gemini
API calls. Rate limit at 15 req/min means max ~5 posts per batch before
needing delays.

### 7. Content-factory auto-opens slides for preview

After generating and compositing all slides, the factory opens the output
folder in Finder / Preview.app so you can visually review before running
the scheduler.

### 8. Content-scheduler is manual — you pick items and dates

No auto-scheduling from the campaign calendar. You tell the scheduler:
"schedule item 2 for tomorrow on TikTok and Instagram." Full control.

## Changes to Existing Skills

### gtm-artifact-refresh (modify)

- Output format changes from markdown to YAML (content-backlog.yaml)
- Each backlog item now includes: slides array, caption, hashtags, visual hints
- Archetype-based template selection for slide structure
- Still reads from niche-research-memory.yaml topics
- Still enforces archetype mix balance (now in YAML)

### gemini_images.py (modify)

- `generate_slide_set()` and `generate_weekly_stockpile()` deprecated
- `generate_image()` remains the core function (background-only, no text)
- Add retry logic with exponential backoff on 429/5xx

## New Files

| File | Purpose |
|------|---------|
| `packages/tools/content_tools/text_overlay.py` | Pillow text compositor |
| `packages/tools/content_tools/fonts/` + license | Bundled font + OFL license |
| `skills/canonical/content-factory/skill.md` | Canonical definition |
| `skills/adapters/claude/content-factory.md` | Claude adapter |
| `.claude/skills/content-factory.md` | Project skill pointer |
| `skills/canonical/content-scheduler/skill.md` | Canonical definition |
| `skills/adapters/claude/content-scheduler.md` | Claude adapter |
| `.claude/skills/content-scheduler.md` | Project skill pointer |

## Resolved Questions

1. **Where does slide text come from?** During gtm-artifact-refresh, when
   research context is richest.
2. **How many slide formats?** Archetype-based defaults (2 or 3 slides per
   archetype), stored per-item in YAML, hand-editable.
3. **How does the factory know what background to generate?** Per-slide
   `visual_hint` field authored during refresh.
4. **What goes on the CTA slide for Campaign Zero?** Engagement closers
   (questions, "save this"), never product mentions.
5. **Is there a preview step?** Yes — auto-open in Finder after generation.
6. **How is scheduling handled?** Manual — user picks items and dates.
7. **Backlog format?** YAML (content-backlog.yaml replaces content-backlog.md).

8. **Font choice?** Montserrat Bold. Bundle `.ttf` + OFL license in
   `packages/tools/content_tools/fonts/`.
9. **Keep markdown backlog?** No. YAML only (`content-backlog.yaml` fully
   replaces `content-backlog.md`). One source of truth.

## Open Questions

None — all resolved.
