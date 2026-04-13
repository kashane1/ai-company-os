# Skill: content-scheduler

Kind: agentic
Owner: gtm
Runtimes: claude

## Purpose

Push generated slide images to Postiz as draft posts for human review.
Runs the social-post-safety validator as a hard gate before any upload.
The founder reviews drafts in Postiz and publishes manually from their phone.

This is Lane 4 of the GTM pipeline.

## Contract

Inputs:

- `product_id`: string — product identifier.
- `item_numbers`: list of int — which backlog items to schedule.
- `channel_ids`: dict of string to string — platform to Postiz channel ID
  mapping, e.g. `{"tiktok": "ch_123", "instagram": "ch_456"}`.
- `scheduled_date`: string — ISO 8601 date for the draft.

Outputs:

- `posts_created`: int — number of draft posts created.
- `platforms`: list of string — which platforms received drafts.
- `post_ids`: list of string — Postiz post IDs.

## Allowed edit boundaries

- `docs/products/<product_id>/gtm/content-backlog.yaml` (status field only)

## Forbidden areas

- `apps/`, `packages/`, `infra/`, `products/`

## Dependencies

- `state/artifacts/content-factory/<product_id>/item_<NNN>/` (read)
- `packages/tools/social_tools/postiz_client.upload_media()`
- `packages/tools/social_tools/postiz_client.create_draft_post()`
- `packages/tools/product_artifacts/gtm_chain.validate_backlog_item()`
- `skills/canonical/social-post-safety/validator.py` (hard gate)

---

## Instructions

### Phase 1 — Load and validate

1. **For each requested item_number**, read the generated slides from
   `state/artifacts/content-factory/<product_id>/item_<NNN>/`.
   If the directory does not exist, abort: "Item N has not been generated.
   Run content-factory first."

2. **Read `metadata.yaml`** from the item directory for caption, hashtags,
   platform, and archetype.

3. **Run the `social-post-safety` validator** on the caption. This is a
   hard gate — if the validator returns `verdict: fail`, abort with the
   failure reasons. Do not upload anything.

### Phase 2 — Upload and create drafts

4. **For each platform in `channel_ids`:**

   a. Upload each slide image via `upload_media()`. Collect the returned
      `media_id` and `url` (path) for each.

   b. Trim hashtags to the platform limit:
      - TikTok: max 5
      - Instagram: max 8
      - Threads: max 3

   c. Call `create_draft_post()` with:
      - `channel_id` from the channel_ids mapping
      - `caption` from metadata
      - `media_ids` and `media_urls` from uploads
      - `hashtags` (trimmed to platform limit)
      - `platform` name
      - `scheduled_at` from input

   d. Log the post ID and platform.

5. **Posts always go to DRAFT status.** The Postiz client enforces this.
   The founder reviews and publishes manually.

### Phase 3 — Update status

6. **Update the item's status** to `scheduled` in `content-backlog.yaml`.

7. **Print a summary:** item number, platforms, post IDs.

## Non-goals

- This skill does not generate images. That is `content-factory`.
- This skill does not author content. That is `gtm-artifact-refresh`.
- This skill does not publish posts. The founder does that from Postiz.
- This skill does not write manifest files. The Postiz dashboard and the
  backlog status field provide sufficient tracking.
