# Skill: content-factory

Kind: agentic
Owner: gtm
Runtimes: claude

## Purpose

Generate finished slide images for social media posts. Takes authored backlog
items from content-backlog.yaml, generates atmospheric background images via
Gemini, overlays text via Pillow, and outputs ready-to-schedule slides.

This is Lane 3 of the GTM pipeline.

## Contract

Inputs:

- `product_id`: string — product identifier from `infra/products.json`.
- `item_numbers`: list of int — which backlog items to generate slides for.

Outputs:

- `output_dir`: string — path to the generated content folder.
- `slides_generated`: int — total slide images produced.
- `items_processed`: int — number of backlog items processed.

## Allowed edit boundaries

- `state/artifacts/content-factory/<product_id>/`
- `docs/products/<product_id>/gtm/content-backlog.yaml` (status field only)

## Forbidden areas

- `apps/`, `packages/`, `infra/`, `products/`

## Dependencies

- `docs/products/<product_id>/gtm/content-backlog.yaml` (read + status write)
- `packages/tools/content_tools/gemini_images.generate_image()`
- `packages/tools/content_tools/text_overlay.overlay_text()`
- `packages/tools/content_tools/text_overlay.compose_post()`
- `packages/tools/product_artifacts/gtm_chain.validate_backlog_item()`

---

## Instructions

### Phase 1 — Load and validate

1. **Read the content backlog** at
   `docs/products/<product_id>/gtm/content-backlog.yaml`.

2. **For each requested item_number**, find the item in the YAML list.
   If not found, log a warning and skip.

3. **Filter text-only items.** Skip any item where `slides` is null, missing,
   or an empty list. This handles text-platform items (e.g. X, Facebook) that
   have caption-only content with no slides to generate.
   Log each skip: "Item N — no slides, skipping image generation."
   If ALL requested items lack slides, exit gracefully with
   `slides_generated: 0, items_processed: 0` (this is not an error).

4. **Validate each remaining item** using `validate_backlog_item()`. If any
   required fields are missing, abort with a clear error listing the invalid
   items.

5. **Check item status.** Only process items with `status: draft`. Skip items
   that are already `generated` or `scheduled` (log a note).

6. **Confirm each item has valid slide entries.** Every slide in the `slides`
   array must contain `text` and `visual_hint` fields. If a slide entry is
   malformed, abort: "Item N has invalid slide data. Run
   gtm-artifact-refresh first to author slide text."

### Phase 2 — Generate slides

7. **For each item, for each slide:**

   a. Call `generate_image(visual_hint, aspect_ratio="9:16")` to produce a
      background image from Gemini. The prompt should contain ONLY the
      `visual_hint` text — no text rendering instructions.

   b. Save the background to a temporary path.

   c. Build a `SlideTextConfig` from the slide's `text` fields:
      - `headline` from `text.headline`
      - `subhead` from `text.subhead`
      - `bullets` from `text.bullets`
      - `body` from `text.body`

   d. Call `overlay_text(background_path, text_config, output_path)` to
      composite the text onto the background using Pillow.

   e. Delete the temporary background file to free memory.

   f. **Wait 4 seconds** before the next `generate_image()` call. This
      matches the Gemini free-tier rate limit of 15 req/min exactly and
      avoids 429 errors.

   g. **On Gemini API 429 or 5xx errors**, retry with exponential backoff:
      - 1st retry: wait 8 seconds
      - 2nd retry: wait 16 seconds
      - 3rd retry: wait 32 seconds
      - After 3 retries: log the failure and skip this slide. The parent
        item remains at `status: draft` so it can be retried later.

8. **Write a `metadata.yaml` sidecar** in the item's output directory:
   ```yaml
   item_number: int
   hook: string
   archetype: string
   platform: string
   campaign: string
   caption: string
   hashtags: list of string
   slides: int  # count
   generated_at: ISO date
   ```

### Phase 3 — Preview and update status

9.  **Open the output directory in Finder** for human review:
    `subprocess.run(["open", str(output_dir)])`

10. **Update the item's status** to `generated` in `content-backlog.yaml`.
    Only update status for items that were actually processed (had slides
    generated). Items skipped in Phase 1 (no slides) retain their current
    status unchanged.

### Output directory structure

```
state/artifacts/content-factory/<product_id>/item_<NNN>/
  slide_1.jpg
  slide_2.jpg
  slide_3.jpg      # only if 3-slide item
  metadata.yaml
```

## Non-goals

- This skill does not author slide text. That is done by `gtm-artifact-refresh`.
- This skill does not schedule or publish posts. That is `content-scheduler`.
- This skill does not run safety validators. The scheduler handles that.
- This skill does not modify any GTM artifacts except the status field.
