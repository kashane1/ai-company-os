# Social Media Publishing Nuances

**Date:** 2026-04-12
**Status:** Active — update as new platforms are added
**Related:** `content-pipeline-multi-tool-orchestration.md`, `docs/failure-modes/gtm-lane.md`

## Problem

Publishing to social media platforms via Postiz has platform-specific
behaviors that are not obvious from the API docs. Without capturing
these, every future publish attempt re-discovers the same gotchas.

## Postiz API — Core Lessons

### Draft vs Publish

- **There is no "publish a draft" endpoint.** The Postiz public API
  (`/public/v1/posts`) only supports `type: "draft"` or `type: "now"` at
  creation time.
- To publish immediately, create the post with `"type": "now"`. You
  cannot change a draft's state after creation via the API.
- Drafts are useful for human review in the Postiz UI — the founder can
  publish from their phone.

### Media Upload Requirements

- Media must be uploaded first via `POST /public/v1/upload`.
- The response returns an `id` and a `path` (URL on `uploads.postiz.com`).
- When attaching media to a post, **both `id` and `path` are required**.
  Omitting the path causes a 400 error: "URL must contain the domain:
  uploads.postiz.com".
- Media IDs are reusable across multiple posts (no need to re-upload for
  cross-platform posting).

### Post Payload Structure

```python
payload = {
    "type": "now",        # or "draft"
    "date": iso_timestamp,
    "shortLink": False,
    "tags": [],
    "posts": [{
        "integration": {"id": channel_id},  # NOT "channelId"
        "value": [{
            "content": caption,
            "image": [{"id": media_id, "path": media_url}],
        }],
        "settings": platform_settings,  # REQUIRED, platform-specific
    }],
}
```

### Listing Posts

- `GET /posts` requires `startDate` and `endDate` query params (ISO 8601).
  Omitting them returns a 400.

## Platform-Specific Behaviors

### TikTok

- **Channel identifier:** `tiktok`
- **Required settings:**
  ```python
  {
      "__type": "tiktok",
      "privacy_level": "PUBLIC_TO_EVERYONE",
      "duet": True,
      "stitch": True,
      "comment": True,
      "autoAddMusic": "no",
      "brand_content_toggle": False,
      "brand_organic_toggle": False,
      "content_posting_method": "UPLOAD",
  }
  ```
- **Hashtag limit:** 5 max
- **Post-publish behavior:** State shows `PUBLISHED` but `releaseURL`
  often points to `tiktok.com/messages` instead of the actual post.
  `releaseId` may show `missing`. Verify in the TikTok app.
- **Carousel/multi-image:** TikTok photo mode supports multiple images
  as a swipeable carousel.

### Instagram

- **Channel identifier:** `instagram-standalone`
- **Required settings:**
  ```python
  {
      "__type": "instagram",
      "post_type": "post",  # or "story"
  }
  ```
- **Hashtag limit:** 8 max (platform allows 30, but 8 is the engagement
  sweet spot per current strategy)
- **Post-publish behavior:** Returns a clean `releaseURL`
  (e.g., `https://www.instagram.com/p/XXXXX/`) and a numeric `releaseId`.
  Reliable for verification.
- **Carousel/multi-image:** Instagram carousel posts work with multiple
  images attached.

### Threads

- **Channel identifier:** `threads`
- **Required settings:** `{"__type": "threads"}`
- **Hashtag limit:** 3 max
- **Not yet tested for publishing** — update when first post goes live.

### X (Twitter)

- **Channel identifier:** `x`
- **Hashtag limit:** 3 max
- **Not yet tested for publishing** — update when first post goes live.

## Text Overlay — Formatting Fix (2026-04-12)

**Bug:** `_wrap_text()` in `text_overlay.py` used `text.split()` which
collapsed all whitespace including intentional newlines. Bullet lists
got mushed into a single paragraph.

**Fix:** Changed to split on `\n` first, then word-wrap each line
independently. This preserves authored line breaks (bullets, stanzas)
while still wrapping long lines to fit the canvas width.

## Content Pipeline Flow

```
gtm-artifact-refresh (authors text per archetype template)
    → content-backlog.yaml (structured slides with headline/subhead/bullets)
        → content-factory (Gemini backgrounds + Pillow text overlay)
            → content-scheduler (upload to Postiz as draft or publish)
```

## Prevention Checklist

- [ ] Always verify `releaseURL` after TikTok publishes — don't trust the API response
- [ ] Always include both `id` and `path` when attaching media
- [ ] Use `type: "draft"` for review workflows, `type: "now"` for immediate publish
- [ ] Run social-post-safety validator before any publish (hard gate)
- [ ] Check platform-specific settings are included (400 errors are cryptic without them)

## Related Files

- `packages/tools/social_tools/postiz_client.py` — API client
- `packages/tools/content_tools/text_overlay.py` — Pillow compositor
- `skills/canonical/content-scheduler/skill.md` — scheduling skill
- `docs/failure-modes/gtm-lane.md` — failure detection table
