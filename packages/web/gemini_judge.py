"""Independent visual judge (Gemini vision) — Phase 6 of the design engine.

The builder is Claude; the judge MUST be a different model family to neutralize
self-preference bias (the loop's whole point). This wraps Gemini's vision endpoint
to score desktop+mobile screenshots against `visual_rubric.md` and return
`VisualScore`s the loop + `review_visual_quality` consume.

The HTTP call is gated on a Gemini API key (raises a clear error without one). The
response PARSER is pure and tested so the contract holds even when the live model
isn't reachable.
"""

from __future__ import annotations

import base64
import json
import re
import ssl
from pathlib import Path
from urllib.request import Request, urlopen

from packages.config.settings import GEMINI_API_KEY_ENV_VAR, get_api_key
from packages.web.design_studio import VisualScore

_MODEL = "gemini-2.5-flash"
_BASE = "https://generativelanguage.googleapis.com/v1beta/models"

# The six rubric categories the judge must score (see visual_rubric.md).
RUBRIC_CATEGORIES = [
    "visual_thesis",
    "hero_impact",
    "imagery_art_direction",
    "typography",
    "layout_composition",
    "copy_specificity",
]

_PROMPT = (
    "You are an exacting design critic scoring a website screenshot set (desktop + "
    "mobile) against a five-figure studio bar. Score EACH category 0-5 (0 generic "
    "template, 5 portfolio-grade). Grade DOWN on doubt. Categories: "
    + ", ".join(RUBRIC_CATEGORIES)
    + ". Return ONLY a JSON array: "
    '[{"category": "...", "score": 0-5, "note": "concrete reason"}].'
)


def parse_judge_response(text: str) -> list[VisualScore]:
    """Parse the judge's JSON array (tolerating code fences/prose) into scores."""

    match = re.search(r"\[.*\]", text, re.DOTALL)
    if not match:
        raise ValueError(f"no JSON array in judge response: {text[:200]}")
    rows = json.loads(match.group(0))
    scores = [
        VisualScore(
            category=str(r["category"]),
            score=int(r["score"]),
            note=str(r.get("note", "")),
        )
        for r in rows
    ]
    got = {s.category for s in scores}
    missing = [c for c in RUBRIC_CATEGORIES if c not in got]
    if missing:
        raise ValueError(f"judge omitted categories: {missing}")
    return scores


def _inline_image(path: str) -> dict:
    data = base64.b64encode(Path(path).read_bytes()).decode()
    return {"inlineData": {"mimeType": "image/png", "data": data}}


def gemini_vision_judge(
    screenshots: dict[str, str], *, api_key: str | None = None
) -> list[VisualScore]:
    """Score the screenshots with Gemini vision (a non-Claude judge)."""

    key = api_key or get_api_key(GEMINI_API_KEY_ENV_VAR)
    if not key:
        raise EnvironmentError(
            f"Missing {GEMINI_API_KEY_ENV_VAR}. The independent judge needs a Gemini "
            "key (a different model family from the Claude builder)."
        )
    parts: list[dict] = [{"text": _PROMPT}]
    for name in ("desktop", "mobile"):
        if screenshots.get(name):
            parts.append({"text": f"--- {name} ---"})
            parts.append(_inline_image(screenshots[name]))

    payload = {"contents": [{"parts": parts}]}
    request = Request(
        f"{_BASE}/{_MODEL}:generateContent?key={key}",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urlopen(request, timeout=120, context=ssl.create_default_context()) as response:
        result = json.loads(response.read())
    text = result["candidates"][0]["content"]["parts"][0]["text"]
    return parse_judge_response(text)
