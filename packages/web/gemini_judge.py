"""Independent visual judge (Gemini vision) — design engine Phase 6 / v3.

The builder is Claude; the judge MUST be a different model family to neutralize
self-preference bias (the loop's whole point). This wraps Gemini's vision endpoint
to score the build against `visual_rubric.md` and return `VisualScore`s the loop +
`review_visual_quality` consume.

v3 upgrades (so the gate can actually perceive what it certifies):
* **It sees motion.** Beyond the desktop+mobile static PNGs it ingests
  *scroll-frame* captures (motion enabled), so `motion_quality` / `signature_moment`
  are scored from real scroll choreography, not a frozen still.
* **It scores against the repo's rubric.** The full `visual_rubric.md` anchors are
  injected into the prompt — the judge grades against our bar, not its own taste.
* **It's more deterministic.** Low temperature + optional N-sample median per
  category (`samples`) damps single-call variance on a high-stakes gate.

The HTTP call is gated on a Gemini API key (raises a clear error without one). The
response PARSER is pure and tested so the contract holds even when the live model
isn't reachable.
"""

from __future__ import annotations

import base64
import json
import re
import ssl
import statistics
from collections.abc import Sequence
from pathlib import Path
from urllib.request import Request, urlopen

from packages.config.settings import GEMINI_API_KEY_ENV_VAR, get_api_key
from packages.web.design_studio import RUBRIC_CATEGORIES, VisualScore

_MODEL = "gemini-2.5-flash"
_BASE = "https://generativelanguage.googleapis.com/v1beta/models"
_RUBRIC_PATH = Path(__file__).resolve().parent / "design_reference" / "visual_rubric.md"

# Low temperature: this is a gate, not a brainstorm — we want stable scores.
_GENERATION_CONFIG = {"temperature": 0.15, "topP": 0.5}

PROVENANCE = "gemini-vision"  # stamped on scores so a hand-written file is detectable


def _prompt() -> str:
    """Build the judge prompt, injecting the repo's rubric anchors."""

    try:
        rubric = _RUBRIC_PATH.read_text(encoding="utf-8")
    except OSError:  # pragma: no cover - rubric is always present in-repo
        rubric = ""
    return (
        "You are an exacting Awwwards-caliber design juror scoring a website against a "
        "FIVE-FIGURE studio bar. You are given desktop + mobile full-page screenshots and "
        "a sequence of scroll-frame captures (motion enabled) — use the scroll frames to "
        "judge motion_quality and signature_moment (whether the page has real scroll "
        "choreography / one memorable on-concept moment), not just the static stills.\n\n"
        "Score EACH category 0-5 against the anchors in the rubric below (0 = generic "
        "template, 5 = portfolio-grade). GRADE DOWN ON DOUBT — reserve 5 for work you'd put "
        "in a studio portfolio. For `ai_house_style`, score 5 only if NONE of the cheap/AI "
        "tells are present (default sans, purple/indigo aurora gradient, gradient headline, "
        "three-icon feature grid, centered-everything hero, glassmorphism everywhere, one "
        "timid shadow, fake stat bar, bouncing scroll-mouse, fake dashboard mockup, generic "
        'copy); each tell drives it down. Categories (score ALL): '
        + ", ".join(RUBRIC_CATEGORIES)
        + ".\n\nReturn ONLY a JSON array: "
        '[{"category": "...", "score": 0-5, "note": "concrete reason citing a specific '
        'observable"}].\n\n--- RUBRIC ---\n'
        + rubric
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


def median_scores(samples: Sequence[list[VisualScore]]) -> list[VisualScore]:
    """Median score per category across N judge samples (damps single-call variance).

    The note is taken from the sample whose score is the median (or the first on an
    even split), so the audit trail stays a real reason, not a synthesized one.
    """

    if not samples:
        return []
    by_category: dict[str, list[VisualScore]] = {}
    for sample in samples:
        for score in sample:
            by_category.setdefault(score.category, []).append(score)
    out: list[VisualScore] = []
    for category in RUBRIC_CATEGORIES:
        scored = by_category.get(category)
        if not scored:
            continue
        med = int(round(statistics.median(s.score for s in scored)))
        note = next((s.note for s in scored if s.score == med), scored[0].note)
        out.append(VisualScore(category=category, score=med, note=note))
    return out


def _inline_image(path: str) -> dict:
    data = base64.b64encode(Path(path).read_bytes()).decode()
    return {"inlineData": {"mimeType": "image/png", "data": data}}


def _one_judgment(parts: list[dict], key: str) -> list[VisualScore]:
    payload = {"contents": [{"parts": parts}], "generationConfig": _GENERATION_CONFIG}
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


def gemini_vision_judge(
    screenshots: dict[str, str],
    *,
    frames: Sequence[str] | None = None,
    samples: int = 1,
    api_key: str | None = None,
) -> list[VisualScore]:
    """Score the build with Gemini vision (a non-Claude judge).

    ``screenshots`` are the desktop/mobile stills; ``frames`` are optional ordered
    scroll-frame PNGs (motion enabled) so the judge can see scroll choreography.
    ``samples`` > 1 calls the model N times and returns the per-category median —
    use it on a real gate to damp variance.
    """

    key = api_key or get_api_key(GEMINI_API_KEY_ENV_VAR)
    if not key:
        raise EnvironmentError(
            f"Missing {GEMINI_API_KEY_ENV_VAR}. The independent judge needs a Gemini "
            "key (a different model family from the Claude builder)."
        )
    parts: list[dict] = [{"text": _prompt()}]
    for name in ("desktop", "mobile"):
        if screenshots.get(name):
            parts.append({"text": f"--- {name} ---"})
            parts.append(_inline_image(screenshots[name]))
    for i, frame in enumerate(frames or []):
        parts.append({"text": f"--- scroll frame {i + 1}/{len(frames)} ---"})
        parts.append(_inline_image(frame))

    runs = [_one_judgment(parts, key) for _ in range(max(1, samples))]
    return runs[0] if len(runs) == 1 else median_scores(runs)
