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

3. **Validate each item** using `validate_backlog_item()`. If any required
   fields are missing, abort with a clear error listing the invalid items.

4. **Check item status.** Only process items with `status: draft`. Skip items
   that are already `generated` or `scheduled` (log a note).

5. **Confirm each item has slide data.** The item must have a `slides` array
   with at least one entry, each containing `text` and `visual_hint` fields.
   If slides are missing, abort: "Item N has no slide data. Run
   gtm-artifact-refresh first to author slide text."

### Phase 2 — Generate slides

6. **For each item, for each slide:**

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

7. **Write a `metadata.yaml` sidecar** in the item's output directory:
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

8. **Open the output directory in Finder** for human review:
   `subprocess.run(["open", str(output_dir)])`

9. **Update the item's status** to `generated` in `content-backlog.yaml`.

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
