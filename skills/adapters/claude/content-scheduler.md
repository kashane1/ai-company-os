---
description: Push generated slide images and text-only posts to Postiz as draft posts. Runs social-post-safety validator before upload or post creation. Creates drafts on TikTok, Instagram, X, Facebook, and Threads for human review and manual publishing.
canonical_source: skills/canonical/content-scheduler/skill.md
---

# Content Scheduler

You are running the content-scheduler skill from `skills/canonical/content-scheduler/skill.md`. Follow the canonical definition.

## Quick reference

This skill pushes content to Postiz as draft posts via two paths:

- **Visual path** — items with slides (TikTok, Instagram, Threads): reads
  generated artifacts from `state/artifacts/content-factory/`, uploads media,
  creates draft with images attached.
- **Text path** — items without slides (X, Facebook): reads caption and
  hashtags directly from `content-backlog.yaml`, creates draft with no media.

The founder reviews all drafts in Postiz and publishes from their phone.

**Prerequisites:**
- Visual-path items must have status `generated`. Run `content-factory` first.
- Text-path items may be in status `draft` (no generation step needed).

## Steps

1. **Pre-flight:** Call `list_channels()` and verify channels exist for all
   target platforms. Warn and skip any platform whose channel is missing.
2. **Route each item:**
   - Has slides + status `generated` -> visual path: read artifacts, upload media
   - No slides + status `draft` -> text path: read caption/hashtags from backlog YAML
   - Has slides + status != `generated` -> error, run content-factory first
3. Run social-post-safety hard gate on caption (ALL items, both paths)
4. **Visual path:** upload slides via `upload_media()`, create draft with media
5. **Text path:** create draft WITHOUT media (omit `image` key from payload entirely)
6. Trim hashtags to platform limit (TikTok 5, Instagram 8, Threads 3, X 3, Facebook 5)
7. Update item status to `scheduled` (text-path: `draft` -> `scheduled`;
   visual-path: `generated` -> `scheduled`)
8. Print summary

## Boundaries

- **May edit**: `content-backlog.yaml` (status only)
- **Must not touch**: `apps/`, `packages/`, `infra/`, `products/`
- **Tools used**: `postiz_client.list_channels()`, `postiz_client.upload_media()` (visual path only), `postiz_client.create_draft_post()`
- **Validators**: `social-post-safety` (hard gate, both paths)
