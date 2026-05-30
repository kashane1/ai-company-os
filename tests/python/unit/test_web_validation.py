"""Tests for the web lane gate: validation checks + build orchestration (F2).

Filesystem-only and offline — a temp ``dist`` exercises each check, and a fake
command runner exercises the build orchestration without Node.
"""

from __future__ import annotations

from pathlib import Path

from packages.web.build import BuildResult, build_and_validate, build_site
from packages.web.validation import (
    check_accessibility,
    check_assets,
    check_internal_links,
    check_responsive,
    parse_page,
    validate_web_dist,
)

GOOD_PAGE = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Acme — get early access</title>
  <link rel="stylesheet" href="/styles.css">
</head>
<body>
  <h1>Stop chasing invoices</h1>
  <nav><a href="/about/">About</a> <a href="#features">Features</a></nav>
  <img src="/hero.png" alt="Dashboard screenshot">
  <section id="features"><h2>Features</h2></section>
  <a href="https://example.com">External</a>
  <button aria-label="Join the waitlist"></button>
  <script src="/app.js"></script>
</body>
</html>
"""


def _write_good_dist(root: Path) -> Path:
    dist = root / "dist"
    dist.mkdir()
    (dist / "index.html").write_text(GOOD_PAGE, encoding="utf-8")
    (dist / "about").mkdir()
    (dist / "about" / "index.html").write_text(
        GOOD_PAGE.replace('href="/about/"', 'href="/"'), encoding="utf-8"
    )
    (dist / "styles.css").write_text("body{margin:0}", encoding="utf-8")
    (dist / "app.js").write_text("console.log(1)", encoding="utf-8")
    (dist / "hero.png").write_bytes(b"\x89PNG\r\n")
    return dist


def test_parse_page_extracts_facts() -> None:
    page = parse_page(GOOD_PAGE)
    assert page.lang == "en"
    assert page.title == "Acme — get early access"
    assert page.has_viewport_device_width is True
    assert page.h1_count == 1
    assert "features" in page.ids
    assert page.images_missing_alt == 0
    assert page.interactive_without_name == 0


def test_clean_dist_passes_all_checks(tmp_path: Path) -> None:
    dist = _write_good_dist(tmp_path)
    report = validate_web_dist(dist, build_exit_code=0)
    assert report.passed, report.to_dict()
    assert {c.name for c in report.checks} >= {
        "web-build", "web-internal-links", "web-assets", "web-responsive", "web-accessibility",
    }


def test_broken_internal_link_and_anchor_fail(tmp_path: Path) -> None:
    dist = tmp_path / "dist"
    dist.mkdir()
    (dist / "index.html").write_text(
        GOOD_PAGE.replace('href="/about/"', 'href="/missing/"').replace(
            'href="#features"', 'href="#nope"'
        ),
        encoding="utf-8",
    )
    (dist / "styles.css").write_text("x", encoding="utf-8")
    (dist / "app.js").write_text("x", encoding="utf-8")
    (dist / "hero.png").write_bytes(b"x")
    check = check_internal_links(dist)
    assert check.passed is False
    assert "missing" in check.details or "nope" in check.details


def test_missing_asset_fails(tmp_path: Path) -> None:
    dist = tmp_path / "dist"
    dist.mkdir()
    (dist / "index.html").write_text(GOOD_PAGE, encoding="utf-8")
    # styles.css / app.js / hero.png intentionally absent
    (dist / "about").mkdir()
    (dist / "about" / "index.html").write_text(GOOD_PAGE, encoding="utf-8")
    check = check_assets(dist)
    assert check.passed is False
    assert check.code == "web_missing_asset"


def test_missing_viewport_fails_responsive(tmp_path: Path) -> None:
    dist = tmp_path / "dist"
    dist.mkdir()
    viewport_tag = '<meta name="viewport" content="width=device-width, initial-scale=1">'
    (dist / "index.html").write_text(GOOD_PAGE.replace(viewport_tag, ""), encoding="utf-8")
    check = check_responsive(dist)
    assert check.passed is False
    assert check.code == "web_missing_viewport"


def test_accessibility_flags_missing_alt_and_lang_and_h1(tmp_path: Path) -> None:
    dist = tmp_path / "dist"
    dist.mkdir()
    bad = """<!doctype html><html><head>
      <meta name="viewport" content="width=device-width"></head>
      <body><img src="/x.png"><a href="/y/"></a></body></html>"""
    (dist / "index.html").write_text(bad, encoding="utf-8")
    check = check_accessibility(dist)
    assert check.passed is False
    details = check.details
    assert "lang" in details and "title" in details and "h1" in details
    assert "without alt" in details


def test_build_site_stops_at_first_failure(tmp_path: Path) -> None:
    project = tmp_path / "proj"
    project.mkdir()
    calls: list[list[str]] = []

    def runner(args, cwd):  # noqa: ANN001
        calls.append(list(args))
        # Fail on `npm ci` so `npm run build` should never run.
        return (1, "", "npm ci failed") if list(args[:2]) == ["npm", "ci"] else (0, "ok", "")

    result = build_site(project, runner=runner)
    assert result.succeeded is False
    assert calls == [["npm", "ci"]]  # build step skipped after ci failed


def test_build_and_validate_happy_path(tmp_path: Path) -> None:
    project = tmp_path / "proj"
    project.mkdir()
    _write_good_dist(project)  # pretend the build produced dist/

    def runner(args, cwd):  # noqa: ANN001
        return (0, "built", "")

    build, report = build_and_validate(project, runner=runner)
    assert isinstance(build, BuildResult)
    assert build.succeeded
    assert report.passed


def test_build_failure_yields_build_only_report(tmp_path: Path) -> None:
    project = tmp_path / "proj"
    project.mkdir()  # no dist produced

    def runner(args, cwd):  # noqa: ANN001
        return (2, "", "boom")

    build, report = build_and_validate(project, runner=runner)
    assert build.succeeded is False
    assert report.passed is False
    assert [c.name for c in report.checks] == ["web-build"]
