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

**Text-only items:** The factory gracefully skips backlog items that have no
`slides` array (null, missing, or empty). This is normal for text platforms
like X and Facebook that produce caption-only items. The factory no longer
aborts when it encounters these items — it logs a skip message and continues
processing the remaining items.

## Steps

1. Read items from `content-backlog.yaml` by item_number
2. Filter out text-only items (no `slides` array) — skip gracefully, do not abort
3. Validate remaining items have slides with text + visual_hint
4. For each slide: generate background via Gemini, overlay text via Pillow
5. Wait 4 seconds between Gemini calls (rate limit); retry on 429/5xx with backoff
6. Write metadata.yaml sidecar with caption + hashtags
7. Open output folder in Finder for preview
8. Update item status to `generated` (only for items that had slides processed)

## Boundaries

- **May edit**: `state/artifacts/content-factory/<product_id>/`, `content-backlog.yaml` (status only)
- **Must not touch**: `apps/`, `packages/`, `infra/`, `products/`
- **Tools used**: `gemini_images.generate_image()`, `text_overlay.overlay_text()`, `text_overlay.compose_post()`
