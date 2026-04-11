"""Gemini API client for AI image generation (Content Factory — Lane 3).

Uses Google's Gemini with Nano Banana 2 image generation model to produce
slideshow images for TikTok/Instagram marketing content.

Model: gemini-2.0-flash-exp (image generation preview)
Free tier: 15 requests/minute
Docs: https://ai.google.dev/gemini-api/docs/image-generation
"""

from __future__ import annotations

import base64
import json
import logging
from dataclasses import dataclass
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError

from packages.config.settings import GEMINI_API_KEY_ENV_VAR, get_api_key

logger = logging.getLogger(__name__)

GEMINI_IMAGE_MODEL = "gemini-2.5-flash-image"
GEMINI_API_BASE = "https://generativelanguage.googleapis.com/v1beta/models"


@dataclass
class GeneratedImage:
    """A single image returned by Gemini."""
    data: bytes
    mime_type: str

    def save(self, path: Path) -> Path:
        """Write image bytes to disk."""
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(self.data)
        logger.info("Saved image to %s (%d bytes)", path, len(self.data))
        return path


@dataclass
class SlideSet:
    """A set of 3 slideshow images for one social media post."""
    hook: GeneratedImage       # Slide 1: attention-grabbing opener
    main_value: GeneratedImage  # Slide 2: core information/benefit
    cta: GeneratedImage        # Slide 3: call-to-action + resolution
    caption: str
    hashtags: list[str]


def _get_api_key() -> str:
    """Retrieve the Gemini API key or raise a clear error."""
    key = get_api_key(GEMINI_API_KEY_ENV_VAR)
    if not key:
        raise EnvironmentError(
            f"Missing {GEMINI_API_KEY_ENV_VAR}. "
            "Add it to your .env file (see .env.example) or set it as an environment variable. "
            "Get a free key at https://ai.google.dev/gemini-api/docs/api-key"
        )
    return key


def generate_image(
    prompt: str,
    aspect_ratio: str = "9:16",
    api_key: str | None = None,
) -> GeneratedImage:
    """Generate a single image via the Gemini API.

    Args:
        prompt: Descriptive prompt for the image. Include style direction,
                text-on-image content, and composition notes.
        aspect_ratio: "9:16" for TikTok/Reels vertical, "1:1" for IG feed,
                      "16:9" for landscape.
        api_key: Override API key (defaults to env var).

    Returns:
        GeneratedImage with raw bytes and MIME type.
    """
    key = api_key or _get_api_key()
    url = f"{GEMINI_API_BASE}/{GEMINI_IMAGE_MODEL}:generateContent?key={key}"

    payload = {
        "contents": [
            {
                "parts": [
                    {
                        "text": (
                            f"{prompt}\n\n"
                            f"Aspect ratio: {aspect_ratio}. "
                            "Style: clean, modern, high contrast, legible text overlays. "
                            "No watermarks."
                        )
                    }
                ]
            }
        ],
        "generationConfig": {
            "responseModalities": ["TEXT", "IMAGE"],
        },
    }

    request = Request(
        url,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urlopen(request, timeout=60) as response:
            result = json.loads(response.read())
    except HTTPError as e:
        body = e.read().decode() if e.fp else ""
        logger.error("Gemini API error %d: %s", e.code, body)
        raise RuntimeError(f"Gemini API returned {e.code}: {body}") from e

    # Extract the image from the response
    candidates = result.get("candidates", [])
    if not candidates:
        raise RuntimeError(f"No candidates in Gemini response: {json.dumps(result)[:500]}")

    parts = candidates[0].get("content", {}).get("parts", [])
    for part in parts:
        if "inlineData" in part:
            inline = part["inlineData"]
            return GeneratedImage(
                data=base64.b64decode(inline["data"]),
                mime_type=inline.get("mimeType", "image/png"),
            )

    raise RuntimeError("No image data found in Gemini response")


def generate_slide_set(
    app_name: str,
    niche: str,
    angle: str,
    topic: str,
    output_dir: Path,
    post_number: int = 1,
) -> SlideSet:
    """Generate a complete 3-slide set for one social media post.

    Args:
        app_name: The app being marketed (e.g., "Catchbook").
        niche: Target audience niche (e.g., "freshwater bass fishing").
        angle: One of "lifestyle", "tips", or "highlights".
        topic: Specific post topic (e.g., "5 lures that crush bass in April").
        output_dir: Where to save the 3 images.
        post_number: Sequential post number for file naming.

    Returns:
        SlideSet with all 3 images saved to disk.
    """
    angle_styles = {
        "lifestyle": {
            "visual": "serene fishing scenery, golden hour lighting, peaceful outdoor vibes",
            "tone": "aspirational, calm, nature-forward",
        },
        "tips": {
            "visual": "clean infographic style, bold data callouts, modern fishing gear",
            "tone": "educational, practical, data-backed",
        },
        "highlights": {
            "visual": "app screenshot aesthetic, organized data display, catch log style",
            "tone": "demonstrative, organized, tech-meets-outdoors",
        },
    }

    style = angle_styles.get(angle, angle_styles["lifestyle"])

    prompts = [
        # Slide 1: Hook
        (
            f"Social media slideshow slide 1 of 3 (HOOK). "
            f"Topic: {topic}. Niche: {niche}. "
            f"Visual style: {style['visual']}. "
            f"This slide grabs attention — bold headline text overlay, intriguing visual. "
            f"Tone: {style['tone']}. "
            f"Vertical 9:16 format for TikTok/Instagram Reels."
        ),
        # Slide 2: Main Value
        (
            f"Social media slideshow slide 2 of 3 (MAIN VALUE). "
            f"Topic: {topic}. Niche: {niche}. "
            f"Visual style: {style['visual']}. "
            f"This slide delivers the core information or benefit. "
            f"Include supporting text overlay with the key insight. "
            f"Tone: {style['tone']}. "
            f"Vertical 9:16 format."
        ),
        # Slide 3: CTA
        (
            f"Social media slideshow slide 3 of 3 (CALL TO ACTION). "
            f"Topic: {topic}. Niche: {niche}. App name: {app_name}. "
            f"Visual style: {style['visual']}. "
            f"This slide resolves the topic and includes a soft call-to-action: "
            f"'Track every catch — {app_name}' or similar. "
            f"Tone: {style['tone']}. "
            f"Vertical 9:16 format."
        ),
    ]

    slide_names = ["hook", "main_value", "cta"]
    images = []

    for i, (prompt, name) in enumerate(zip(prompts, slide_names)):
        logger.info("Generating slide %d/3 (%s) for post %d...", i + 1, name, post_number)
        img = generate_image(prompt)
        ext = "png" if "png" in img.mime_type else "jpg"
        path = output_dir / f"post{post_number:03d}_{name}.{ext}"
        img.save(path)
        images.append(img)

    # Generate caption and hashtags based on angle
    caption = f"{topic} 🎣 #fishing #{niche.replace(' ', '')}"
    hashtags = _generate_hashtags(niche, angle)

    return SlideSet(
        hook=images[0],
        main_value=images[1],
        cta=images[2],
        caption=caption,
        hashtags=hashtags,
    )


def _generate_hashtags(niche: str, angle: str) -> list[str]:
    """Generate up to 5 relevant hashtags (per posting rules)."""
    base = ["fishing", "catchbook", niche.replace(" ", "")]
    angle_tags = {
        "lifestyle": ["fishinglife", "outdoors"],
        "tips": ["fishingtips", "anglertips"],
        "highlights": ["fishinglog", "catchoftheday"],
    }
    tags = base + angle_tags.get(angle, ["fishinglife"])
    return [f"#{tag}" for tag in tags[:5]]


def generate_weekly_stockpile(
    app_name: str,
    niche: str,
    topics: list[dict],
    output_dir: Path,
) -> list[SlideSet]:
    """Generate a full week of content (7 posts = 21 images).

    Args:
        app_name: App being marketed.
        niche: Target niche.
        topics: List of dicts with keys "angle" and "topic", one per post.
                Example: [{"angle": "lifestyle", "topic": "Why I keep a fishing journal"}]
        output_dir: Root output directory. Each post gets a subfolder.

    Returns:
        List of 7 SlideSets.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    slide_sets = []

    for i, entry in enumerate(topics[:7], start=1):
        logger.info("=== Generating post %d/7: %s ===", i, entry["topic"])
        slide_set = generate_slide_set(
            app_name=app_name,
            niche=niche,
            angle=entry["angle"],
            topic=entry["topic"],
            output_dir=output_dir,
            post_number=i,
        )
        slide_sets.append(slide_set)

    logger.info("Weekly stockpile complete: %d posts, %d images", len(slide_sets), len(slide_sets) * 3)
    return slide_sets
