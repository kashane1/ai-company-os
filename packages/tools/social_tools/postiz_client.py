"""Postiz API client for social media scheduling (Lane 4).

Handles media uploads, post creation, and scheduling to drafts.
Postiz API docs: https://docs.postiz.com

This client is designed for the ai-company-os pipeline:
  Content Factory (Lane 3) → Postiz Scheduler (Lane 4) → Manual Posting (Lane 5)
"""

from __future__ import annotations

import json
import logging
import re
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError

from packages.config.settings import POSTIZ_API_KEY_ENV_VAR, get_api_key

logger = logging.getLogger(__name__)

POSTIZ_API_BASE = "https://api.postiz.com/public/v1"

# Regex for sanitizing filenames in multipart uploads.
_SAFE_FILENAME_RE = re.compile(r"[^a-zA-Z0-9._-]")

# Delay between consecutive API calls to avoid rate limits.
API_CALL_DELAY_SECONDS = 1.5


@dataclass
class PostizMedia:
    """A media file uploaded to Postiz."""
    media_id: str
    url: str
    filename: str


@dataclass
class PostizPost:
    """A scheduled post in Postiz."""
    post_id: str
    platform: str
    status: str  # "draft", "scheduled", "published"
    scheduled_at: str | None
    caption: str


@dataclass
class ScheduleManifest:
    """Summary of a scheduling batch — for review before publishing."""
    posts: list[PostizPost] = field(default_factory=list)
    total_media_uploaded: int = 0
    platforms: list[str] = field(default_factory=list)
    date_range: str = ""

    def summary(self) -> str:
        lines = [
            f"Scheduled {len(self.posts)} posts across {', '.join(self.platforms)}",
            f"Media files uploaded: {self.total_media_uploaded}",
            f"Date range: {self.date_range}",
            "",
            "Posts:",
        ]
        for p in self.posts:
            lines.append(f"  [{p.platform}] {p.status} @ {p.scheduled_at or 'unscheduled'}: {p.caption[:60]}...")
        return "\n".join(lines)


def _get_api_key() -> str:
    """Retrieve the Postiz API key or raise a clear error."""
    key = get_api_key(POSTIZ_API_KEY_ENV_VAR)
    if not key:
        raise EnvironmentError(
            f"Missing {POSTIZ_API_KEY_ENV_VAR}. "
            "Add it to your .env file (see .env.example) or set it as an environment variable. "
            "Sign up at https://postiz.com ($29/mo hosted plan)."
        )
    return key


def _api_request(
    method: str,
    endpoint: str,
    data: dict | bytes | None = None,
    content_type: str = "application/json",
    api_key: str | None = None,
) -> dict:
    """Make an authenticated request to the Postiz API."""
    key = api_key or _get_api_key()
    url = f"{POSTIZ_API_BASE}{endpoint}"

    headers = {
        "Authorization": key,
        "Content-Type": content_type,
    }

    if isinstance(data, dict):
        body = json.dumps(data).encode()
    elif isinstance(data, bytes):
        body = data
    else:
        body = None

    request = Request(url, data=body, headers=headers, method=method)

    try:
        with urlopen(request, timeout=30) as response:
            return json.loads(response.read())
    except HTTPError as e:
        body_text = (e.read().decode() if e.fp else "")[:500]
        logger.error("Postiz API error %d on %s %s: %s", e.code, method, endpoint, body_text)
        raise RuntimeError(f"Postiz API returned {e.code}: {body_text}") from e


def list_channels(api_key: str | None = None) -> list[dict]:
    """List all connected social media channels (Postiz calls these 'integrations').

    Returns list of channel dicts with id, platform, name, etc.
    Note: Postiz UI uses 'channel', but the API uses 'integrations'.
    """
    result = _api_request("GET", "/integrations", api_key=api_key)
    # API may return list directly or nested under a key
    if isinstance(result, list):
        channels = result
    else:
        channels = result.get("integrations", result.get("data", []))
    logger.info("Found %d connected channels", len(channels))
    return channels


def upload_media(file_path: Path, api_key: str | None = None) -> PostizMedia:
    """Upload a media file to Postiz for use in posts.

    Args:
        file_path: Local path to image/video file.
        api_key: Override API key.

    Returns:
        PostizMedia with the uploaded file's ID and URL.
    """
    import mimetypes
    import uuid

    mime_type = mimetypes.guess_type(str(file_path))[0] or "image/png"
    file_bytes = file_path.read_bytes()

    # Sanitize filename to prevent header injection.
    safe_name = _SAFE_FILENAME_RE.sub("_", file_path.name)

    # Multipart form data boundary
    boundary = uuid.uuid4().hex
    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="file"; filename="{safe_name}"\r\n'
        f"Content-Type: {mime_type}\r\n\r\n"
    ).encode() + file_bytes + f"\r\n--{boundary}--\r\n".encode()

    key = api_key or _get_api_key()
    url = f"{POSTIZ_API_BASE}/upload"
    headers = {
        "Authorization": key,
        "Content-Type": f"multipart/form-data; boundary={boundary}",
    }

    request = Request(url, data=body, headers=headers, method="POST")

    try:
        with urlopen(request, timeout=60) as response:
            result = json.loads(response.read())
    except HTTPError as e:
        err_body = (e.read().decode() if e.fp else "")[:500]
        raise RuntimeError(f"Media upload failed ({e.code}): {err_body}") from e

    media = PostizMedia(
        media_id=result.get("id", result.get("media_id", "")),
        url=result.get("path", result.get("url", "")),
        filename=file_path.name,
    )
    logger.info("Uploaded %s → media_id=%s", file_path.name, media.media_id)
    return media


# Per-platform hashtag limits (from hashtag-strategy.md convention).
PLATFORM_HASHTAG_LIMITS: dict[str, int] = {
    "tiktok": 5,
    "instagram": 8,
    "threads": 3,
    "x": 3,
    "facebook": 2,
}
DEFAULT_HASHTAG_LIMIT = 5


def _platform_settings(platform: str | None) -> dict:
    """Return required platform-specific settings for Postiz post creation."""
    p = (platform or "tiktok").lower()
    if p == "tiktok":
        return {
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
    elif p == "instagram" or p == "instagram-standalone":
        return {
            "__type": "instagram",
            "post_type": "post",
        }
    elif p == "threads":
        return {
            "__type": "threads",
        }
    elif p == "x":
        return {
            "__type": "x",
            "who_can_reply_post": "everyone",
        }
    elif p == "facebook":
        return {
            "__type": "facebook",
        }
    else:
        return {
            "__type": p,
        }


def create_draft_post(
    channel_id: str,
    caption: str,
    media_ids: list[str],
    scheduled_at: datetime | None = None,
    hashtags: list[str] | None = None,
    platform: str | None = None,
    api_key: str | None = None,
    media_urls: list[str] | None = None,
) -> PostizPost:
    """Create a post in DRAFT status on a specific channel.

    Follows the posting rules:
    - Always sends to DRAFTS (not direct publish)
    - Platform-aware hashtag limits (Instagram 8, TikTok 5, Threads 3)
    - Caption under 1,000 characters

    Args:
        channel_id: Postiz channel ID (from list_channels).
        caption: Post caption text.
        media_ids: List of media IDs from upload_media.
        scheduled_at: Optional schedule time.
        hashtags: Hashtags (trimmed to platform limit if over).
        platform: Platform name for hashtag limit lookup. Falls back to 5.
        api_key: Override API key.
    """
    # Enforce posting rules with platform-aware hashtag limits
    if hashtags:
        limit = PLATFORM_HASHTAG_LIMITS.get(
            (platform or "").lower(), DEFAULT_HASHTAG_LIMIT
        )
        hashtags = hashtags[:limit]
        caption = f"{caption}\n\n{' '.join(hashtags)}"

    if len(caption) > 1000:
        logger.warning("Caption exceeds 1000 chars (%d), truncating", len(caption))
        caption = caption[:997] + "..."

    # Safety: only ever create drafts. Refuse any other type.
    post_type = "draft"

    # Postiz API uses a nested structure:
    # {type, date, posts: [{integration: {id}, value: [{content, image}], settings}]}
    from datetime import datetime as _dt

    schedule_date = scheduled_at or _dt.now()

    # Build the value entry. X requires "image" key to be present as an
    # array even for text-only posts. Other platforms also accept empty arrays.
    value_entry: dict = {"content": caption}
    if media_ids and media_urls:
        value_entry["image"] = [
            {"id": mid, "path": murl}
            for mid, murl in zip(media_ids, media_urls)
        ]
    else:
        value_entry["image"] = []

    payload: dict = {
        "type": post_type,
        "date": schedule_date.isoformat(),
        "shortLink": False,
        "tags": [],
        "posts": [
            {
                "integration": {"id": channel_id},
                "value": [value_entry],
                "settings": _platform_settings(platform),
            }
        ],
    }

    time.sleep(API_CALL_DELAY_SECONDS)
    result = _api_request("POST", "/posts", data=payload, api_key=api_key)

    # API may return a list of post objects or a single object
    if isinstance(result, list):
        first = result[0] if result else {}
    else:
        first = result

    post = PostizPost(
        post_id=first.get("id", first.get("post_id", str(result)[:50])),
        platform=first.get("platform", platform or "unknown"),
        status="draft",
        scheduled_at=scheduled_at.isoformat() if scheduled_at else None,
        caption=caption,
    )
    logger.info("Created draft post %s on %s", post.post_id, post.platform)
    return post


def schedule_content_batch(
    content_dir: Path,
    channel_ids: dict[str, str],
    start_date: datetime,
    posts_per_day: int = 1,
    api_key: str | None = None,
) -> ScheduleManifest:
    """Schedule a batch of content from a Content Factory output directory.

    Expects the directory to contain files named like:
        post001_hook.png, post001_main_value.png, post001_cta.png
        post002_hook.png, ...

    Args:
        content_dir: Directory with generated slide images.
        channel_ids: Mapping of platform name to Postiz channel ID.
                     Example: {"tiktok": "ch_123", "instagram": "ch_456"}
        start_date: First posting date.
        posts_per_day: Number of posts per day per platform.
        api_key: Override API key.

    Returns:
        ScheduleManifest summarizing all scheduled posts.
    """
    from datetime import timedelta

    manifest = ScheduleManifest(platforms=list(channel_ids.keys()))

    # Discover post groups (post001, post002, etc.)
    image_files = sorted(content_dir.glob("post*_hook.*"))
    post_numbers = [f.stem.split("_")[0] for f in image_files]

    current_date = start_date
    posts_today = 0

    for post_num in post_numbers:
        # Find all 3 slides for this post
        slides = sorted(content_dir.glob(f"{post_num}_*.*"))
        if len(slides) < 3:
            logger.warning("Post %s has only %d slides, skipping", post_num, len(slides))
            continue

        # Upload all slides
        media_ids = []
        for slide_path in slides:
            media = upload_media(slide_path, api_key=api_key)
            media_ids.append(media.media_id)
            manifest.total_media_uploaded += 1

        # Read caption from sidecar file if it exists
        caption_file = content_dir / f"{post_num}_caption.txt"
        caption = caption_file.read_text().strip() if caption_file.exists() else f"🎣 #{post_num}"

        # Schedule on each platform
        for platform, channel_id in channel_ids.items():
            post = create_draft_post(
                channel_id=channel_id,
                caption=caption,
                media_ids=media_ids,
                scheduled_at=current_date,
                api_key=api_key,
            )
            post.platform = platform
            manifest.posts.append(post)

        posts_today += 1
        if posts_today >= posts_per_day:
            posts_today = 0
            current_date += timedelta(days=1)

    if manifest.posts:
        first = manifest.posts[0].scheduled_at or ""
        last = manifest.posts[-1].scheduled_at or ""
        manifest.date_range = f"{first} → {last}"

    logger.info("Batch scheduling complete:\n%s", manifest.summary())
    return manifest
