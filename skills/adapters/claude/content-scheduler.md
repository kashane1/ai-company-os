---
description: Push generated slide images to Postiz as draft posts. Runs social-post-safety validator before upload. Creates drafts on TikTok and Instagram for human review and manual publishing.
canonical_source: skills/canonical/content-scheduler/skill.md
---

# Content Scheduler

You are running the content-scheduler skill from `skills/canonical/content-scheduler/skill.md`. Follow the canonical definition.

## Quick reference

This skill takes generated slides from the content-factory output and pushes
them to Postiz as draft posts. The founder reviews in Postiz and publishes
from their phone.

**Prerequisite:** Items must be generated (status: `generated`). Run
`content-factory` first.

## Steps

1. Read generated slides from `state/artifacts/content-factory/<product_id>/item_<NNN>/`
2. Read metadata.yaml for caption and hashtags
3. Run social-post-safety hard gate on caption (abort on failure)
4. For each platform: upload slides, trim hashtags to limit, create draft post
5. Update item status to `scheduled`
6. Print summary

## Boundaries

- **May edit**: `content-backlog.yaml` (status only)
- **Must not touch**: `apps/`, `packages/`, `infra/`, `products/`
- **Tools used**: `postiz_client.upload_media()`, `postiz_client.create_draft_post()`
- **Validators**: `social-post-safety` (hard gate)
