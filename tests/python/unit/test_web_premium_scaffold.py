"""Tests for the astro-premium scaffold (design engine Phase 0).

The premium stack is the opt-in surface for five-figure builds. The guarantee
locked here: it materializes cleanly with no unfilled tokens, it consumes the
design-system role tokens (never hard-codes color), and it carries the
reduced-motion-safe baseline. The full `npm run build` + web-gate pass is verified
manually (it needs a node toolchain); these checks protect the template's shape.
"""

from __future__ import annotations

from pathlib import Path

from packages.web.scaffold import PREMIUM_TEMPLATE, default_context, scaffold_site


def _materialize(tmp_path: Path) -> Path:
    ctx = default_context("TrueLine Plumbing", tagline="Plumbing done with precision")
    scaffold_site(tmp_path, ctx, template=PREMIUM_TEMPLATE)
    return tmp_path


def test_premium_scaffold_materializes_expected_files(tmp_path) -> None:
    _materialize(tmp_path)
    for rel in (
        "package.json",
        "astro.config.mjs",
        "src/pages/index.astro",
        "src/styles/global.css",
        "src/styles/design-system.css",
        "src/scripts/motion.ts",
    ):
        assert (tmp_path / rel).exists(), f"missing {rel}"


def test_premium_scaffold_fills_every_token(tmp_path) -> None:
    _materialize(tmp_path)
    page = (tmp_path / "src/pages/index.astro").read_text()
    assert "{{" not in page
    assert "TrueLine Plumbing" in page


def test_premium_page_consumes_role_tokens_not_hardcoded_color(tmp_path) -> None:
    _materialize(tmp_path)
    css = (tmp_path / "src/styles/global.css").read_text()
    # global.css themes off role tokens so re-synthesis re-themes the whole site.
    for token in ("var(--canvas)", "var(--ink)", "var(--accent)", "var(--display-font)"):
        assert token in css
    # No raw hex colors in the base layer (they belong only in the token theme).
    import re

    assert not re.search(r":\s*#[0-9a-fA-F]{3,6}\b", css), "base layer hard-codes hex"


def test_premium_scaffold_is_reduced_motion_safe(tmp_path) -> None:
    _materialize(tmp_path)
    css = (tmp_path / "src/styles/global.css").read_text()
    motion = (tmp_path / "src/scripts/motion.ts").read_text()
    assert "prefers-reduced-motion" in css
    assert "prefers-reduced-motion" in motion  # JS bails out of smooth scroll/reveals
    # Content is visible without JS: reveal hiding is gated behind html.js.
    assert "html.js [data-reveal]" in css
