# Skill: content-scheduler

Kind: agentic
Owner: gtm
Runtimes: claude

## Purpose

Push generated slide images and text-only posts to Postiz as draft posts
for human review. Runs the social-post-safety validator as a hard gate
before any upload or post creation. The founder reviews drafts in Postiz
and publishes manually from their phone.

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

- `state/artifacts/content-factory/<product_id>/item_<NNN>/` (read — visual path only)
- `docs/products/<product_id>/gtm/content-backlog.yaml` (read for text-only items + status write)
- `packages/tools/social_tools/postiz_client.list_channels()`
- `packages/tools/social_tools/postiz_client.upload_media()`
- `packages/tools/social_tools/postiz_client.create_draft_post()`
- `packages/tools/product_artifacts/gtm_chain.validate_backlog_item()`
- `skills/canonical/social-post-safety/validator.py` (hard gate)

---

## Instructions

### Phase 1 — Load and validate

0. **Pre-flight channel check.** Call `list_channels()` and verify that
   channels exist for all target platforms in `channel_ids`. If a
   platform's channel is not connected, warn and skip items for that
   platform (do not abort the entire batch).

1. **For each requested item_number**, determine the routing path:

   **IF** the backlog item has `slides` AND status == `generated`:
     -> **Visual path** (existing): read slides from
        `state/artifacts/content-factory/<product_id>/item_<NNN>/`.
        Read `metadata.yaml` from the item directory for caption, hashtags,
        platform, and archetype.

   **ELIF** the backlog item has NO `slides` AND status == `draft`:
     -> **Text path**: read `caption` and `hashtags` directly from the
        item's entry in `content-backlog.yaml`. No artifact directory is
        required. Status transitions directly from `draft` to `scheduled`
        (skips the `generated` state).

   **ELSE** the item has slides but status != `generated`:
     -> Error: "Item N has slides but has not been generated. Run
        content-factory first."

2. **Run the `social-post-safety` validator** on the caption for ALL items
   regardless of path. This is a hard gate — if the validator returns
   `verdict: fail`, abort that item with the failure reasons. Do not
   upload or post anything for it.

### Phase 2 — Upload and create drafts

4. **For each platform in `channel_ids`:**

   **Visual-path items (have slides):**

   a. Upload each slide image via `upload_media()`. Collect the returned
      `media_id` and `url` (path) for each.

   b. Trim hashtags to the platform limit:
      - TikTok: max 5
      - Instagram: max 8
      - Threads: max 3
      - X: max 3
      - Facebook: max 5

   c. Call `create_draft_post()` with:
      - `channel_id` from the channel_ids mapping
      - `caption` from metadata
      - `media_ids` and `media_urls` from uploads
      - `hashtags` (trimmed to platform limit)
      - `platform` name
      - `scheduled_at` from input

   **Text-path items (no slides):**

   a. Trim hashtags to the platform limit (same limits as above).

   b. Call `create_draft_post()` with:
      - `channel_id` from the channel_ids mapping
      - `caption` from the backlog item
      - `hashtags` (trimmed to platform limit)
      - `platform` name
      - `scheduled_at` from input
      - Do NOT include `media_ids` or `media_urls`. The Postiz client
        must omit the `image` key entirely (do not send an empty list).

   d. Log the post ID and platform.

5. **Posts always go to DRAFT status.** The Postiz client enforces this.
   The founder reviews and publishes manually.

### Phase 3 — Update status

6. **Update the item's status** to `scheduled` in `content-backlog.yaml`.
   Visual-path items transition: `generated` -> `scheduled`.
   Text-path items transition: `draft` -> `scheduled` (skips `generated`).

7. **Print a summary:** item number, platforms, post IDs.

## Non-goals

- This skill does not generate images. That is `content-factory`.
- This skill does not author content. That is `gtm-artifact-refresh`.
- This skill does not publish posts. The founder does that from Postiz.
- This skill does not write manifest files. The Postiz dashboard and the
  backlog status field provide sufficient tracking.
