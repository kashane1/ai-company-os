"""Tests for the web gate's contrast check (design-intelligence work).

Offline, filesystem-only. A temp ``dist`` with crafted inlined ``:root`` CSS
exercises pass, fail, skip-on-unresolvable, and dark-mode-ignored behavior.
"""

from __future__ import annotations

from pathlib import Path

from packages.web.validation import _root_vars, check_contrast


def _write(dist: Path, css: str) -> None:
    dist.mkdir(parents=True, exist_ok=True)
    (dist / "index.html").write_text(
        f"<!doctype html><html lang='en'><head><title>t</title>"
        f"<style>{css}</style></head><body><h1>h</h1></body></html>",
        encoding="utf-8",
    )


def test_good_contrast_passes(tmp_path: Path):
    _write(tmp_path, ":root{ --text:#15172b; --bg:#ffffff; --brand:#1e40af; --brand-contrast:#ffffff; }")
    check = check_contrast(tmp_path)
    assert check.passed
    assert check.code is None


def test_low_contrast_text_fails(tmp_path: Path):
    # Light gray text on white ~1.6:1 — well under 4.5.
    _write(tmp_path, ":root{ --text:#cccccc; --bg:#ffffff; }")
    check = check_contrast(tmp_path)
    assert not check.passed
    assert check.code == "web_contrast"
    assert "--text on --bg" in check.details


def test_accent_label_uses_large_bar(tmp_path: Path):
    # Orange #EA580C with white ~3.3:1: passes the 3:1 on-color bar, would fail 4.5.
    _write(tmp_path, ":root{ --text:#111; --bg:#fff; --accent:#EA580C; --on-accent:#ffffff; }")
    assert check_contrast(tmp_path).passed


def test_unresolvable_value_is_skipped_not_failed(tmp_path: Path):
    _write(tmp_path, ":root{ --text:var(--ink); --bg:#ffffff; }")
    check = check_contrast(tmp_path)
    assert check.passed  # skipped, not failed
    assert "skipped" in check.details


def test_dark_mode_root_is_ignored(tmp_path: Path):
    # A bad pair only inside a dark @media block must not trip the gate.
    css = (
        ":root{ --text:#15172b; --bg:#ffffff; }"
        "@media (prefers-color-scheme: dark){ :root{ --text:#222; --bg:#000; } }"
    )
    _write(tmp_path, css)
    assert check_contrast(tmp_path).passed


def test_root_vars_last_wins_and_strips_at_blocks():
    html = (
        "<style>:root{ --bg:#fff; } @media (x){ :root{ --bg:#000; } }</style>"
        "<style>:root{ --bg:#eee; }</style>"
    )
    vars_ = _root_vars(html)
    assert vars_["--bg"] == "#eee"  # last top-level wins; @media ignored


def test_missing_pair_is_noop(tmp_path: Path):
    _write(tmp_path, ":root{ --brand:#1e40af; }")  # no --text/--bg
    assert check_contrast(tmp_path).passed
