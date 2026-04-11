"""Phase 5.4 — claude output policy tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from packages.policies.claude_output import (
    ClaudeOutputViolation,
    validate_claude_output,
)


HAPPY = """---
last_updated: 2026-04-10
source_session_id: session-abc123
parent: product-brief.md
---

# Positioning
body text
"""


def test_happy_path(tmp_path: Path):
    p = tmp_path / "app-store-positioning.md"
    p.write_text(HAPPY)
    header = validate_claude_output(p, expected_parent="product-brief.md")
    assert header.last_updated == "2026-04-10"
    assert header.source_session_id == "session-abc123"
    assert header.parent == "product-brief.md"


def test_missing_header_rejected(tmp_path: Path):
    p = tmp_path / "raw.md"
    p.write_text("# just a title\n\nno header at all")
    with pytest.raises(ClaudeOutputViolation) as exc:
        validate_claude_output(p)
    assert exc.value.code == "claude_output_header_missing"


def test_bad_last_updated(tmp_path: Path):
    p = tmp_path / "bad.md"
    p.write_text(
        "---\nlast_updated: yesterday\nsource_session_id: s1\n---\nbody\n"
    )
    with pytest.raises(ClaudeOutputViolation) as exc:
        validate_claude_output(p)
    assert exc.value.code == "last_updated_missing"


def test_missing_session_id(tmp_path: Path):
    p = tmp_path / "bad.md"
    p.write_text("---\nlast_updated: 2026-04-10\n---\nbody\n")
    with pytest.raises(ClaudeOutputViolation) as exc:
        validate_claude_output(p)
    assert exc.value.code == "source_session_id_missing"


def test_missing_parent_when_expected(tmp_path: Path):
    p = tmp_path / "ok.md"
    p.write_text(
        "---\nlast_updated: 2026-04-10\nsource_session_id: s1\n---\nbody\n"
    )
    with pytest.raises(ClaudeOutputViolation) as exc:
        validate_claude_output(p, expected_parent="product-brief.md")
    assert exc.value.code == "parent_link_missing"


def test_html_comment_header_fallback(tmp_path: Path):
    p = tmp_path / "legacy.md"
    p.write_text(
        "<!-- claude-output\nlast_updated: 2026-04-10\nsource_session_id: s2\nparent: founder-brief.md\n-->\n\n# body\n"
    )
    header = validate_claude_output(p, expected_parent="founder-brief.md")
    assert header.source_session_id == "s2"
