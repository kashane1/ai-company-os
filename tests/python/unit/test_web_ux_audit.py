"""Tests for the web UX audit (F7).

The scaffold should score well across all categories; a deliberately bad page
should fail the relevant ones. Offline and static.
"""

from __future__ import annotations

from pathlib import Path

from packages.web.scaffold import default_context, render_landing_html
from packages.web.ux_audit import audit_dist


def _dist_with(tmp_path: Path, html: str) -> Path:
    dist = tmp_path / "dist"
    dist.mkdir()
    (dist / "index.html").write_text(html, encoding="utf-8")
    return dist


def test_scaffold_passes_the_audit(tmp_path: Path) -> None:
    html = render_landing_html(default_context("Acme", tagline="Invoices on autopilot"))
    report = audit_dist(_dist_with(tmp_path, html))
    assert report.passed, report.to_dict()
    assert report.overall >= 70
    assert set(report.scores) == {"responsive", "accessibility", "performance", "seo"}


def test_zoom_disabled_fails_responsive(tmp_path: Path) -> None:
    html = """<!doctype html><html lang="en"><head>
      <meta name="viewport" content="width=device-width, maximum-scale=1, user-scalable=no">
      <title>Acme — early access page</title>
      <meta name="description" content="A page.">
      <style>@media(max-width:600px){body{padding:0}}</style></head>
      <body><h1>Hi</h1></body></html>"""
    report = audit_dist(_dist_with(tmp_path, html))
    assert report.scores["responsive"] < 100
    msgs = " ".join(f.message for c in report.categories for f in c.findings)
    assert "zoom" in msgs


def test_no_responsive_css_warns(tmp_path: Path) -> None:
    html = """<!doctype html><html lang="en"><head>
      <meta name="viewport" content="width=device-width, initial-scale=1">
      <title>Acme — early access page</title>
      <meta name="description" content="A page.">
      <style>.x{width:1200px}</style></head><body><h1>Hi</h1></body></html>"""
    report = audit_dist(_dist_with(tmp_path, html))
    msgs = " ".join(f.message for c in report.categories for f in c.findings)
    assert "responsive CSS" in msgs


def test_accessibility_and_seo_failures(tmp_path: Path) -> None:
    # No lang, no title, no h1, an unlabelled input, no meta description.
    html = """<!doctype html><html><head>
      <meta name="viewport" content="width=device-width"></head>
      <body><img src="/x.png"><input type="email"><a href="/y/"></a></body></html>"""
    report = audit_dist(_dist_with(tmp_path, html))
    assert report.scores["accessibility"] < 70
    assert report.scores["seo"] < 100
    assert report.passed is False


def test_unlabelled_input_flagged_but_labelled_ok(tmp_path: Path) -> None:
    good = """<!doctype html><html lang="en"><head>
      <meta name="viewport" content="width=device-width, initial-scale=1">
      <title>Acme — early access</title><meta name="description" content="d">
      <style>@media(max-width:1px){a{}}</style></head>
      <body><h1>Hi</h1>
      <label for="e">Email</label><input id="e" type="email"></body></html>"""
    report = audit_dist(_dist_with(tmp_path, good))
    a11y = next(c for c in report.categories if c.name == "accessibility")
    assert all("input" not in f.message for f in a11y.findings)


def test_implicit_label_and_aria_hidden_inputs_not_flagged(tmp_path: Path) -> None:
    # A control nested inside a <label> is labelled by that label's text (implicit
    # association — valid WCAG, no for/id needed), and an aria-hidden control (e.g. a
    # honeypot) is out of the a11y tree. Neither should count as an unlabelled input.
    html = """<!doctype html><html lang="en"><head>
      <meta name="viewport" content="width=device-width, initial-scale=1">
      <title>Acme — early access</title><meta name="description" content="d">
      <style>@media(max-width:1px){a{}}</style></head>
      <body><h1>Hi</h1>
      <label>Email <input type="email"></label>
      <label><input type="checkbox"> I agree</label>
      <input type="text" aria-hidden="true" tabindex="-1">
      </body></html>"""
    report = audit_dist(_dist_with(tmp_path, html))
    a11y = next(c for c in report.categories if c.name == "accessibility")
    assert all("input" not in f.message for f in a11y.findings), a11y.to_dict()
    assert a11y.score == 100
