---
description: Generate finished slide images for social media posts. Takes authored backlog items, generates Gemini backgrounds, overlays text via Pillow, and outputs ready-to-schedule slides with auto-preview in Finder.
canonical_source: skills/canonical/content-factory/skill.md
---

# Content Factory

You are running the content-factory skill from `skills/canonical/content-factory/skill.md`. Follow the canonical definition.

## Quick reference

This skill takes backlog items (with pre-authored slide text and visual hints)
and produces finished slide images. It does NOT author text — that was done
by `gtm-artifact-refresh` when the backlog items were created.

**Prerequisite:** Items must have `slides` data in `content-backlog.yaml`.
If slides are missing, run `gtm-artifact-refresh` first.

## Steps

1. Read items from `content-backlog.yaml` by item_number
2. Validate each item has slides with text + visual_hint
3. For each slide: generate background via Gemini, overlay text via Pillow
4. Wait 4 seconds between Gemini calls (rate limit)
5. Write metadata.yaml sidecar with caption + hashtags
6. Open output folder in Finder for preview
7. Update item status to `generated`

## Boundaries

- **May edit**: `state/artifacts/content-factory/<product_id>/`, `content-backlog.yaml` (status only)
- **Must not touch**: `apps/`, `packages/`, `infra/`, `products/`
- **Tools used**: `gemini_images.generate_image()`, `text_overlay.overlay_text()`, `text_overlay.compose_post()`
