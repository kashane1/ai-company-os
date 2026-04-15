---
title: "Multi-Platform Social Publishing: Expanding the GTM Content Pipeline to 5 Platforms"
problem_type: integration-issues
date: 2026-04-14
symptoms:
  - Postiz API rejects text-only posts when image key is present but empty (must omit key entirely)
  - Unicode smart quotes and confusables cause incorrect character counts and malformed content
  - Accidental @mentions slip through to live platforms
  - Content backlog has no per-platform routing — all items flow through image generation pipeline
  - Gemini image generation fails transiently with no retry, silently dropping visual posts
  - Rate-limit 429 errors from Postiz when scheduling batches without inter-request delay
  - Existing backlog items break validation when new required fields (platform, topic_id) are added
components_affected:
  - packages/tools/social_tools/postiz_client.py
  - skills/canonical/social-post-safety/validator.py
  - packages/tools/product_artifacts/gtm_chain.py
  - skills/canonical/gtm-artifact-refresh/skill.md
  - skills/canonical/gtm-artifact-refresh/platforms.md
  - skills/canonical/content-factory/skill.md
  - skills/canonical/content-scheduler/skill.md
  - skills/canonical/content-voice-guardrail/skill.md
  - skills/canonical/niche-research-brief/contract.yaml
  - skills/registry.yaml
tags:
  - postiz
  - social-media
  - multi-platform
  - x-twitter
  - facebook
  - tiktok
  - instagram
  - threads
  - text-only-posts
  - image-pipeline
  - unicode-normalization
  - safety-validation
  - rate-limiting
  - gemini
  - retry-backoff
  - backward-compatibility
  - content-scheduler
  - content-factory
  - skill-graph
related_skills:
  - niche-research-brief
  - gtm-artifact-refresh
  - content-factory
  - content-scheduler
  - social-post-safety
  - content-voice-guardrail
related_docs:
  - docs/solutions/integration-issues/social-media-publishing-nuances.md
  - docs/solutions/integration-issues/content-pipeline-multi-tool-orchestration.md
  - docs/brainstorms/2026-04-13-gtm-multi-platform-engine-brainstorm.md
  - docs/plans/2026-04-13-feat-gtm-multi-platform-content-engine-plan.md
---

# Multi-Platform Social Publishing: Expanding the GTM Content Pipeline to 5 Platforms

Expanding the GTM skill pipeline from 3 platforms (TikTok, Instagram, Threads) to 5 (+ X/Twitter and Facebook) surfaced five distinct failure modes. This doc captures the architectural patterns and concrete fixes so the next platform expansion is a 30-minute task, not a research session.

## The Skill Graph

```
niche-research-brief
       ↓
gtm-artifact-refresh    ← generates backlog items per platform
       ↓
content-factory         ← generates images (SKIPS text-only items)
       ↓
content-scheduler       ← dual-path: visual or text-only
       ↓
[Postiz API]
```

X and Facebook are **text-only platforms** in this pipeline — no generated images. They enter at `gtm-artifact-refresh` and skip `content-factory` entirely.

---

## Root Cause Analysis

### 1. Postiz API: absent ≠ empty

The biggest blocker. When posting text-only content, `postiz_client.py` was including `"image": []` unconditionally. Postiz treats an absent `image` key differently from an empty array — the empty array caused rejections.

**Never construct a payload skeleton and conditionally populate it.** Build the payload from scratch based on what's actually present.

### 2. Platform-aware routing was missing

`content-factory` assumed all posts needed Gemini image generation. `content-scheduler` had no dual-path logic. The correct gate is `slides is null` (data shape), not a platform name check.

### 3. Safety validator gaps for new platforms

X's 280-character limit is far stricter than existing platforms. Two specific gaps: Unicode confusables caused incorrect character counts; no detection of accidental `@mention` strings.

### 4. Backlog schema not platform-aware

37 existing items had no `platform` or `topic_id` field. Adding required fields broke validation. New fields must always be nullable.

### 5. Reliability gaps

Gemini had no retry logic. Postiz calls had no rate limiting. Error bodies were logged in full (sometimes huge), obscuring the actual error.

---

## Working Solution

### Fix 1 — Postiz payload: omit image key when no media

```python
# postiz_client.py
payload = {"content": text, "date": scheduled_at, "type": "post"}
if media_ids:
    payload["image"] = [{"id": mid} for mid in media_ids]
# NEVER: payload["image"] = []
```

Platform settings for the new platforms:

```python
# X/Twitter
"x": {"settings": {"twitter": True}}

# Facebook
"facebook": {"settings": {"facebook": True, "facebookType": "page"}}
```

Also added: 1.5s inter-call delay, error body truncation to 500 chars, filename sanitization.

### Fix 2 — content-factory: skip null-slides items

```python
for item in backlog_items:
    if item.get("slides") is None:
        continue  # text-only platform — skip Gemini entirely
    generate_gemini_image_with_retry(item)
```

Gemini retry-with-backoff:

```python
def generate_with_retry(prompt, retries=3):
    delays = [8, 16, 32]
    for attempt, delay in enumerate(delays):
        try:
            return gemini_client.generate(prompt)
        except TransientAPIError:
            if attempt == retries - 1:
                raise
            time.sleep(delay)
```

### Fix 3 — content-scheduler: dual-path routing

Route on data shape, never on platform name:

```python
for item in backlog_items:
    if item.get("slides") is None:
        # Text-only path: build payload from backlog fields
        text = f"{item['hook']}\n\n{item['body']}\n\n{item['cta']}"
        media_ids = []
    else:
        # Visual path: upload generated image, get media IDs
        image_path = resolve_image_path(item)
        media_ids = upload_media(image_path)
        text = item["hook"]
    schedule_post(item["platform"], text, media_ids)
```

### Fix 4 — Safety validator: Unicode normalization + char limits

```python
import unicodedata, re

PLATFORM_CHAR_LIMITS = {
    "x": 280,
    "twitter": 280,
    "instagram": 2200,
    "tiktok": 2200,
    "threads": 500,
    "facebook": 63206,
}

MENTION_RE = re.compile(r"(?<!\w)@\w+")

def validate_post(text: str, platform: str) -> list[str]:
    errors = []
    text = unicodedata.normalize("NFKC", text)  # normalize BEFORE counting
    limit = PLATFORM_CHAR_LIMITS.get(platform)
    if limit and len(text) > limit:
        errors.append(f"Exceeds {platform} char limit ({len(text)}/{limit})")
    mentions = MENTION_RE.findall(text)
    if mentions:
        errors.append(f"Accidental @mentions: {mentions}")
    return errors
```

### Fix 5 — Backlog schema: nullable new fields

```yaml
# Backlog item — all new fields nullable for backward compat
- id: "post-001"
  topic_id: "fishing-season-prep"  # groups cross-platform variants; null for legacy items
  platform: "x"                    # enum: x|instagram|tiktok|threads|facebook
  hook: "..."
  body: "..."
  slides: null                      # null = text-only; populated = visual pipeline
  cta: "..."
  status: "approved"
```

37 existing items without `slides`, `platform`, or `topic_id` continue to load cleanly via null-guard.

---

## Skill Graph Changes Summary

| Skill | Change |
|---|---|
| `niche-research-brief` | No change — platform list is downstream |
| `gtm-artifact-refresh` | Added X/Facebook to platform enum; generates `slides: null` for text-only platforms; added `topic_id` grouping; reads `platforms.md` playbook |
| `content-factory` | `slides is null` guard skips Gemini; Gemini retry-with-backoff (8s→16s→32s) |
| `content-scheduler` | Dual-path routing (visual vs text-only); X/Facebook Postiz settings; 1.5s rate limit delay; 500-char error truncation |
| `social-post-safety` | NFKC normalization; per-platform char limits (X=280, Facebook=63206); `@mention` detection |
| `content-voice-guardrail` | Added `facebook` to platform enum |
| `niche-research-brief` contract | Added `facebook` to platforms values list |

---

## Prevention Strategies

### API Contracts
- **Audit absent-vs-empty semantics** before wiring any new third-party endpoint. These are silent failures — the API accepts the payload and misbehaves downstream.
- **Build payloads from scratch** based on what's present. Never initialize a skeleton and conditionally populate.
- **Assert JSON structure in integration tests**, not just response codes.

### Platform Registry
- Maintain a single source-of-truth config for per-platform constants: char limit, rate limit, supported content types, API settings. Nothing hardcoded in pipeline logic.
- When adding a new platform, **write the registry entry first**, before any pipeline code.

### Character Limits
- Apply **Unicode NFKC normalization before any character count**, always.
- Validate at the schema level (input validation), not at the API boundary.

### Schema Evolution
- **All new fields are nullable** with a sensible default. Required fields may only exist in new schema versions, never retrofitted.
- **Store schema version in file header**. Validation branches on version.
- Run a null-guard pass on load for any YAML backlog file.

### Routing Logic
- **Route on data shape, never on platform name.** Platform names are labels; data shape is the contract.
- The visual-vs-text gate is expressed once, in one place.

### Rate Limiting and Retries
- Every external API call is wrapped in a rate-limit-aware client reading its delay from the platform registry.
- Every transient API has exponential backoff with configurable max-retry.
- **Log every retry**: attempt number, delay applied, error received.

---

## Test Cases to Add

**API Serialization**
- `test_text_only_post_omits_image_field` — assert `"image"` key absent from serialized payload
- `test_image_post_includes_image_field` — assert `"image"` key present and non-empty
- `test_each_platform_serializer_produces_valid_payload` — parameterized across all platforms

**Character Limits**
- `test_nfkc_normalization_applied_before_count` — full-width chars; assert normalized count is used
- `test_character_limit_exact_boundary_per_platform` — `limit` chars passes; `limit+1` fails
- `test_character_limit_fires_before_api_call` — mock API; assert not called when content too long

**Schema Backward Compatibility**
- `test_legacy_backlog_item_loads_without_error` — pre-`platform`/`topic_id` item deserializes cleanly
- `test_new_field_defaults_to_null_when_absent` — assert `item.platform is None`, `item.topic_id is None`

**Routing Logic**
- `test_visual_path_selected_when_slides_present` — assert visual path regardless of platform
- `test_text_path_selected_when_slides_is_null` — assert text path regardless of platform
- `test_routing_does_not_branch_on_platform_name` — static check: no string comparison against platform names in router

**Rate Limiting and Retries**
- `test_rate_limit_delay_applied_between_calls` — mock `time.sleep`; assert called with platform delay
- `test_429_triggers_exponential_backoff` — mock 429×2 then 200; assert delay escalates
- `test_gemini_transient_failure_retried_with_backoff` — mock transient error×2; retry fires with increasing delay
- `test_retry_exhaustion_raises_clean_error` — always-fail mock; assert structured error after max retries

---

## Red Flags for Adding a 6th Platform

**API Design**
- Docs say "optional" without specifying absent-vs-empty — test both before wiring
- Platform uses bytes or grapheme clusters as its limit unit, not Unicode code points — shared counter needs a platform-specific override
- Separate content-type endpoints (image URL ≠ text URL) — routing fork belongs in the platform registry

**Schema**
- New platform requires a field with no sensible null default — needs a platform-specific extension object, not a shared field
- You find a platform-name check inside a shared function — missing parameter; let the registry drive it

**Rate Limits**
- Per-minute limit (not per-call delay) — fixed-delay model is insufficient; need token-bucket
- 200 status with error body on rate limit — retry logic won't trigger; needs response-body inspection hook

**Operations**
- No sandbox environment — add a dry-run flag that logs payload without sending
- Platform requires media preprocessing (aspect ratio, resolution) different from existing platforms — preprocessing step keyed from registry, not inside image generation flow
- Retry attempts not logged — structured retry logging must be in place before going live

---

## Related Docs

- [`social-media-publishing-nuances.md`](social-media-publishing-nuances.md) — Postiz API payload details per platform (living doc; update after first X/Facebook posts go live)
- [`content-pipeline-multi-tool-orchestration.md`](content-pipeline-multi-tool-orchestration.md) — Gemini/Pillow split, atomic YAML writes, rate-limit calculations
- [`docs/brainstorms/2026-04-13-gtm-multi-platform-engine-brainstorm.md`](../../brainstorms/2026-04-13-gtm-multi-platform-engine-brainstorm.md) — decisions: flat backlog, topic_id grouping, no new repurpose lane
- [`docs/plans/2026-04-13-feat-gtm-multi-platform-content-engine-plan.md`](../../plans/2026-04-13-feat-gtm-multi-platform-content-engine-plan.md) — phased implementation spec
