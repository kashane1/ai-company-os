"""Gemini API client for AI background image generation (Content Factory — Lane 3).

Uses Google's Gemini image generation model to produce background images
(no text, no overlays) for the content pipeline. Text overlays are handled
separately by text_overlay.py using Pillow.

Model: gemini-2.5-flash-image
Free tier: ~2 images/minute, ~500/day
Docs: https://ai.google.dev/gemini-api/docs/image-generation
"""

from __future__ import annotations

import base64
import json
import logging
import ssl
from dataclasses import dataclass
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from packages.config.settings import GEMINI_API_KEY_ENV_VAR, get_api_key

logger = logging.getLogger(__name__)


def _ssl_context() -> ssl.SSLContext:
    """Verified TLS context, preferring certifi's CA bundle.

    Some interpreters (e.g. python.org macOS builds) ship without OS trust
    roots wired in, so a bare urlopen fails CERTIFICATE_VERIFY_FAILED. Fall
    back to the system default if certifi isn't installed.
    """
    try:
        import certifi  # noqa: PLC0415 — optional dependency
        return ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        return ssl.create_default_context()

GEMINI_IMAGE_MODEL = "gemini-2.5-flash-image"
# The premium design lane uses the Pro image model ("Nano Banana Pro") for
# art-directed, brand-grade imagery (see the concept-led-imagery playbook). It's
# opt-in per call so the content factory keeps the cheaper/faster flash default.
GEMINI_IMAGE_MODEL_PRO = "gemini-3-pro-image-preview"
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
    *,
    model: str | None = None,
    seed: int | None = None,
) -> GeneratedImage:
    """Generate a single background image via the Gemini API.

    The prompt should describe the visual scene only — no text rendering
    instructions. Text overlays are handled by text_overlay.py.

    Args:
        prompt: Descriptive prompt for the background image. Include style
                direction, composition, lighting. No text instructions.
        aspect_ratio: "9:16" for TikTok/Reels vertical, "1:1" for IG feed,
                      "16:9" for landscape.
        api_key: Override API key (defaults to env var).
        model: Override the image model (e.g. GEMINI_IMAGE_MODEL_PRO for the
               premium design lane). Defaults to the flash model.
        seed: Fixed seed for reproducible/cohesive sets (a hero + supporting shots
              that share one look). Omitted → the model's default randomness.

    Returns:
        GeneratedImage with raw bytes and MIME type.
    """
    key = api_key or _get_api_key()
    url = f"{GEMINI_API_BASE}/{model or GEMINI_IMAGE_MODEL}:generateContent?key={key}"

    generation_config: dict[str, object] = {"responseModalities": ["TEXT", "IMAGE"]}
    if seed is not None:
        generation_config["seed"] = seed
    payload = {
        "contents": [
            {
                "parts": [
                    {
                        "text": (
                            f"{prompt}\n\n"
                            f"Aspect ratio: {aspect_ratio}. "
                            "No text, no writing, no logos, no watermarks, "
                            "no UI elements. Background image only."
                        )
                    }
                ]
            }
        ],
        "generationConfig": generation_config,
    }

    request = Request(
        url,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urlopen(request, timeout=120, context=_ssl_context()) as response:
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
