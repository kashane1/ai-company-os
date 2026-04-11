"""Phase 4.3 — central redaction spec.

Any log excerpt, rollup payload, or briefing body that is produced by the
platform MUST pass through :func:`redact` before it is persisted to
``state/artifacts/briefings/`` or emitted to a Gmail draft. The redaction
test suite (``tests/python/unit/test_observability_rollup.py``) asserts
that planted credentials never appear in rollup output.

The patterns are deliberately broad. False positives (a few characters
of a real identifier getting masked) are preferred over leaking a token.
"""

from __future__ import annotations

import re
from dataclasses import dataclass


REDACTED = "[REDACTED]"


# Ordered list of patterns. Each tuple is (compiled_regex, description).
# Patterns are tried in order; the first match wins for a given span.
PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"sk-[A-Za-z0-9_\-]{16,}"), "openai_or_anthropic_key"),
    (re.compile(r"ghp_[A-Za-z0-9]{20,}"), "github_personal_access_token"),
    (re.compile(r"ghs_[A-Za-z0-9]{20,}"), "github_app_token"),
    (re.compile(r"github_pat_[A-Za-z0-9_]{20,}"), "github_fine_grained_pat"),
    (re.compile(r"AKIA[0-9A-Z]{16}"), "aws_access_key_id"),
    (re.compile(r"ASIA[0-9A-Z]{16}"), "aws_temp_access_key_id"),
    # JWT: three base64url chunks separated by dots, each ≥8 chars
    (
        re.compile(r"eyJ[A-Za-z0-9_\-]{8,}\.[A-Za-z0-9_\-]{8,}\.[A-Za-z0-9_\-]{8,}"),
        "jwt",
    ),
    # Generic Authorization: Bearer <token>
    (
        re.compile(r"(?i)\bbearer\s+[A-Za-z0-9_\-\.=]{16,}"),
        "bearer_token",
    ),
    # Generic "api_key=..." or "token=..." fragments
    (
        re.compile(r"(?i)\b(?:api[_-]?key|token|secret)\s*[:=]\s*[A-Za-z0-9_\-\.]{12,}"),
        "inline_secret_assignment",
    ),
    # Postiz / Gemini / RevenueCat env-style keys in logs
    (
        re.compile(r"\b(?:POSTIZ|GEMINI|REVENUECAT)_[A-Z_]*KEY\s*=\s*\S+"),
        "gtm_env_key",
    ),
]


@dataclass(frozen=True)
class RedactionResult:
    text: str
    hits: tuple[str, ...]


def redact(text: str) -> RedactionResult:
    """Return ``(redacted_text, hit_labels)``.

    ``hit_labels`` is a tuple of pattern descriptions that fired, so
    callers can count credential leaks per-rollup without re-scanning.
    """
    hits: list[str] = []
    redacted = text
    for pattern, label in PATTERNS:

        def _sub(_match, _label=label):
            hits.append(_label)
            return REDACTED

        redacted = pattern.sub(_sub, redacted)
    return RedactionResult(text=redacted, hits=tuple(hits))


def redact_lines(lines: list[str]) -> list[str]:
    return [redact(line).text for line in lines]
