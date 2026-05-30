"""Tests for the Astro landing scaffold (F3).

The important guarantee: the scaffold the platform emits is itself clean — it
fills every token, writes a buildable project, and its rendered landing page
passes the same web gate (responsive + a11y) the worker enforces.
"""

from __future__ import annotations

from pathlib import Path

from packages.web.scaffold import (
    default_context,
    render_landing_html,
    scaffold_site,
    unfilled_tokens,
)
from packages.web.validation import parse_page, validate_web_dist


def test_default_context_is_complete_no_unfilled_tokens() -> None:
    html = render_landing_html(default_context("Acme", audience="freelancers"))
    assert unfilled_tokens(html) == [], "every template token must have a default"
    assert "{{" not in html


def test_rendered_landing_passes_the_web_gate(tmp_path: Path) -> None:
    html = render_landing_html(default_context("Acme", tagline="Stop chasing invoices"))
    dist = tmp_path / "dist"
    dist.mkdir()
    (dist / "index.html").write_text(html, encoding="utf-8")

    report = validate_web_dist(dist)
    assert report.passed, report.to_dict()


def test_rendered_landing_is_responsive_and_accessible() -> None:
    page = parse_page(render_landing_html(default_context("Acme")))
    assert page.has_viewport_device_width is True   # responsive baseline
    assert page.lang == "en"
    assert page.h1_count == 1                        # single, clear page heading
    assert page.title and "Acme" in page.title
    assert page.images_missing_alt == 0
    assert page.interactive_without_name == 0


def test_content_reflects_the_product() -> None:
    html = render_landing_html(default_context("Northwind", tagline="Invoices on autopilot"))
    assert "Northwind" in html
    assert "Invoices on autopilot" in html


def test_scaffold_site_writes_buildable_project(tmp_path: Path) -> None:
    target = tmp_path / "acme-web"
    written = scaffold_site(target, default_context("Acme"))
    names = {p.relative_to(target).as_posix() for p in written}

    assert "package.json" in names
    assert "astro.config.mjs" in names
    assert "src/pages/index.astro" in names
    assert "src/styles/global.css" in names

    # package.json got a real, slugified name (no leftover token).
    pkg = (target / "package.json").read_text()
    assert "{{" not in pkg
    assert '"name": "acme"' in pkg

    # The scaffolded page also has no leftover tokens.
    assert "{{" not in (target / "src" / "pages" / "index.astro").read_text()


def test_unknown_template_raises(tmp_path: Path) -> None:
    import pytest

    with pytest.raises(FileNotFoundError):
        scaffold_site(tmp_path / "x", default_context("Acme"), template="does-not-exist")
