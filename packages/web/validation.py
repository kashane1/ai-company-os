"""Web lane validation — the quality gate for a built site (F2).

The WEB worker (``apps/worker-web``) builds a site into a ``dist/`` directory and
then runs these checks before anything can advance. The logic here is pure and
filesystem-only (no network, no browser, stdlib HTML parsing), so it's fully
unit-testable and runs anywhere — the worker just points it at the build output.

Checks, each producing a :class:`ValidationCheck` (so they slot into the same
review/approval surface the engineering and iOS lanes use):

* **build** — the production build command exited cleanly.
* **internal-links** — every relative link/anchor resolves to a real file or id.
* **assets** — every locally referenced asset (css/js/img/font) exists on disk.
* **responsive** — every page declares a ``width=device-width`` viewport (the
  baseline that makes a layout render cleanly on phones/tablets). Deeper
  responsive/a11y auditing lives in the ``web-ux-audit`` skill (F7); this is the
  fail-closed minimum the build gate enforces.
* **accessibility** — baseline a11y: ``<html lang>``, a ``<title>``, exactly one
  ``<h1>``, images carry ``alt``, and interactive elements have an accessible
  name.
* **contrast** — WCAG AA color contrast on declared light-mode ``:root``
  foreground/background pairs (body text 4.5:1; on-color labels 3:1).
  Deliberately sound-not-complete: unresolvable values (``var()``,
  ``color-mix()``, alpha<1, dark-mode ``@media`` overrides) are skipped, not
  guessed.

``validate_web_dist`` aggregates them into a :class:`WebValidationReport`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from html.parser import HTMLParser
from pathlib import Path
import re
from urllib.parse import urldefrag, urlparse

from packages.schemas.task_run import ValidationCheck
from packages.web.palette import AA_LARGE, AA_NORMAL, Unresolvable, contrast_ratio

# Tag/attribute pairs that reference a URL or asset.
_URL_ATTRS = {
    "a": "href",
    "link": "href",
    "script": "src",
    "img": "src",
    "source": "src",
    "video": "src",
    "audio": "src",
    "iframe": "src",
}

_INTERACTIVE_TAGS = {"a", "button"}


@dataclass
class _ParsedPage:
    """The handful of facts the checks need from one HTML document."""

    title: str | None = None
    lang: str | None = None
    has_viewport_device_width: bool = False
    h1_count: int = 0
    ids: set[str] = field(default_factory=set)
    links: list[str] = field(default_factory=list)  # href/src values (any tag)
    images_missing_alt: int = 0
    interactive_without_name: int = 0


class _PageParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.page = _ParsedPage()
        self._in_title = False
        self._open_interactive: list[dict[str, str]] = []
        self._interactive_text: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        a = {k: (v or "") for k, v in attrs}

        if tag == "html" and "lang" in a and a["lang"].strip():
            self.page.lang = a["lang"].strip()

        if tag == "title":
            self._in_title = True

        if tag == "meta" and a.get("name", "").lower() == "viewport":
            if "width=device-width" in a.get("content", "").replace(" ", "").lower():
                self.page.has_viewport_device_width = True

        if tag == "h1":
            self.page.h1_count += 1

        if "id" in a and a["id"].strip():
            self.page.ids.add(a["id"].strip())

        url_attr = _URL_ATTRS.get(tag)
        if url_attr and a.get(url_attr):
            self.page.links.append(a[url_attr].strip())

        if tag == "img":
            # A meaningful image needs alt text; alt="" is allowed (decorative).
            if "alt" not in a:
                self.page.images_missing_alt += 1

        if tag in _INTERACTIVE_TAGS:
            self._open_interactive.append(a)
            self._interactive_text.append("")

    def handle_endtag(self, tag: str) -> None:
        if tag == "title":
            self._in_title = False
        if tag in _INTERACTIVE_TAGS and self._open_interactive:
            attrs = self._open_interactive.pop()
            text = self._interactive_text.pop().strip()
            has_name = bool(
                text
                or attrs.get("aria-label", "").strip()
                or attrs.get("title", "").strip()
                or attrs.get("aria-labelledby", "").strip()
            )
            # An <a> that only wraps an image inherits the image's alt; treat a
            # link/button with no text and no label as missing an accessible name.
            if not has_name:
                self.page.interactive_without_name += 1

    def handle_data(self, data: str) -> None:
        if self._in_title:
            self.page.title = (self.page.title or "") + data
        if self._interactive_text:
            self._interactive_text[-1] += data


def parse_page(html: str) -> _ParsedPage:
    parser = _PageParser()
    parser.feed(html)
    page = parser.page
    if page.title is not None:
        page.title = page.title.strip() or None
    return page


def _html_files(dist_dir: Path) -> list[Path]:
    return sorted(p for p in dist_dir.rglob("*.html") if p.is_file())


def _is_external(url: str) -> bool:
    """True for links we don't resolve locally: absolute URLs, protocol-relative,
    mailto:/tel:, and pure fragments are handled separately."""
    parsed = urlparse(url)
    return bool(parsed.scheme) or url.startswith("//")


def check_build(exit_code: int, stdout: str = "", stderr: str = "") -> ValidationCheck:
    """Did the production build succeed? ``exit_code == 0`` is the contract."""
    passed = exit_code == 0
    detail = "build succeeded" if passed else f"build failed (exit {exit_code})"
    tail = (stderr or stdout or "").strip().splitlines()[-3:]
    if not passed and tail:
        detail += ": " + " / ".join(tail)
    return ValidationCheck(
        name="web-build",
        passed=passed,
        details=detail,
        code=None if passed else "web_build_failed",
    )


def check_internal_links(dist_dir: Path) -> ValidationCheck:
    """Every relative link and in-page anchor must resolve inside ``dist``."""
    broken: list[str] = []
    for html_file in _html_files(dist_dir):
        page = parse_page(html_file.read_text(encoding="utf-8", errors="ignore"))
        for raw in page.links:
            if not raw or raw.startswith(("mailto:", "tel:", "data:")) or _is_external(raw):
                continue
            target, frag = urldefrag(raw)
            if not target:
                # Pure fragment ("#features") → must exist on this page.
                if frag and frag not in page.ids:
                    broken.append(f"{html_file.name} → #{frag}")
                continue
            resolved = _resolve(dist_dir, html_file, target)
            if resolved is None or not resolved.exists():
                broken.append(f"{html_file.name} → {raw}")
    passed = not broken
    return ValidationCheck(
        name="web-internal-links",
        passed=passed,
        details="all internal links resolve"
        if passed
        else f"{len(broken)} broken link(s): " + "; ".join(broken[:8]),
        code=None if passed else "web_broken_internal_link",
    )


def check_assets(dist_dir: Path) -> ValidationCheck:
    """Every locally referenced asset (css/js/img/font/etc.) exists on disk."""
    missing: list[str] = []
    asset_exts = {".css", ".js", ".mjs", ".png", ".jpg", ".jpeg", ".gif", ".svg",
                  ".webp", ".avif", ".ico", ".woff", ".woff2", ".ttf", ".otf", ".mp4", ".webm"}
    for html_file in _html_files(dist_dir):
        page = parse_page(html_file.read_text(encoding="utf-8", errors="ignore"))
        for raw in page.links:
            if not raw or _is_external(raw) or raw.startswith(("data:", "mailto:", "tel:", "#")):
                continue
            target, _ = urldefrag(raw)
            if Path(target).suffix.lower() not in asset_exts:
                continue
            resolved = _resolve(dist_dir, html_file, target)
            if resolved is None or not resolved.exists():
                missing.append(f"{html_file.name} → {raw}")
    passed = not missing
    return ValidationCheck(
        name="web-assets",
        passed=passed,
        details="all referenced assets exist"
        if passed
        else f"{len(missing)} missing asset(s): " + "; ".join(missing[:8]),
        code=None if passed else "web_missing_asset",
    )


def check_responsive(dist_dir: Path) -> ValidationCheck:
    """Every page must declare a ``width=device-width`` viewport — the baseline
    that lets phones/tablets render the layout at the right scale."""
    offenders = [
        html_file.name
        for html_file in _html_files(dist_dir)
        if not parse_page(html_file.read_text(encoding="utf-8", errors="ignore"))
        .has_viewport_device_width
    ]
    passed = not offenders
    return ValidationCheck(
        name="web-responsive",
        passed=passed,
        details="every page sets a responsive viewport"
        if passed
        else f"{len(offenders)} page(s) missing width=device-width viewport: "
        + ", ".join(offenders[:8]),
        code=None if passed else "web_missing_viewport",
    )


def check_accessibility(dist_dir: Path) -> ValidationCheck:
    """Baseline a11y per page: lang, title, exactly one h1, image alts, named
    interactive elements."""
    problems: list[str] = []
    for html_file in _html_files(dist_dir):
        page = parse_page(html_file.read_text(encoding="utf-8", errors="ignore"))
        name = html_file.name
        if not page.lang:
            problems.append(f"{name}: <html> missing lang")
        if not page.title:
            problems.append(f"{name}: missing <title>")
        if page.h1_count == 0:
            problems.append(f"{name}: no <h1>")
        elif page.h1_count > 1:
            problems.append(f"{name}: {page.h1_count} <h1> (want 1)")
        if page.images_missing_alt:
            problems.append(f"{name}: {page.images_missing_alt} img without alt")
        if page.interactive_without_name:
            problems.append(f"{name}: {page.interactive_without_name} link/button without a name")
    passed = not problems
    return ValidationCheck(
        name="web-accessibility",
        passed=passed,
        details="baseline accessibility checks pass"
        if passed
        else f"{len(problems)} issue(s): " + "; ".join(problems[:8]),
        code=None if passed else "web_accessibility",
    )


# --- contrast (color a11y) -------------------------------------------------
#
# Sound, not complete: resolve only literal light-mode top-level :root custom
# properties, check a fixed set of foreground/background pairs, and SKIP (never
# guess) any value we can't resolve to an opaque literal — var(), color-mix(),
# alpha<1, or anything declared inside an @media/@supports/@container block
# (so a dark-mode :root override is deliberately out of scope).

_STYLE_RE = re.compile(r"<style[^>]*>(.*?)</style>", re.DOTALL | re.IGNORECASE)
_ROOT_RE = re.compile(r":root\s*\{([^}]*)\}")
_DECL_RE = re.compile(r"(--[\w-]+)\s*:\s*([^;]+)")
_AT_RULE_RE = re.compile(r"@(?:media|supports|container)\b", re.IGNORECASE)

# Pairs to check: (foreground var, background var, is_large_text). On-color
# labels (CTA text on accent, text on brand) sit on buttons/headers — large/UI,
# so the WCAG bar is 3:1; body text on the page background is normal, 4.5:1.
_CONTRAST_PAIRS = [
    ("--text", "--bg", False),
    ("--brand-contrast", "--brand", True),
    ("--on-accent", "--accent", True),
]


def _strip_at_blocks(css: str) -> str:
    """Remove ``@media``/``@supports``/``@container`` blocks (and their nested
    braces) so only top-level, light-mode rules remain."""
    out: list[str] = []
    i = 0
    for m in _AT_RULE_RE.finditer(css):
        out.append(css[i : m.start()])
        # Walk to the block's opening brace, then to its matching close.
        j = css.find("{", m.end())
        if j == -1:
            i = m.end()
            break
        depth = 1
        k = j + 1
        while k < len(css) and depth:
            if css[k] == "{":
                depth += 1
            elif css[k] == "}":
                depth -= 1
            k += 1
        i = k
    out.append(css[i:])
    return "".join(out)


def _root_vars(html: str) -> dict[str, str]:
    """Resolve top-level light-mode ``:root`` custom properties from inlined
    ``<style>`` blocks, applying last-wins across declarations."""
    css = "\n".join(_STYLE_RE.findall(html))
    css = _strip_at_blocks(css)
    resolved: dict[str, str] = {}
    for block in _ROOT_RE.findall(css):
        for name, value in _DECL_RE.findall(block):
            resolved[name] = value.strip()
    return resolved


def check_contrast(dist_dir: Path) -> ValidationCheck:
    """WCAG AA color-contrast on declared ``:root`` foreground/background pairs.

    Resolves only literal light-mode values; pairs whose colors can't be
    resolved to opaque literals are skipped (reported in details), not failed —
    a guessed pass would be worse than an honest skip.
    """
    problems: list[str] = []
    skipped: list[str] = []
    for html_file in _html_files(dist_dir):
        name = html_file.name
        vars_ = _root_vars(html_file.read_text(encoding="utf-8", errors="ignore"))
        for fg, bg, large in _CONTRAST_PAIRS:
            if fg not in vars_ or bg not in vars_:
                continue  # pair not defined on this page
            try:
                ratio = contrast_ratio(vars_[fg], vars_[bg])
            except Unresolvable as exc:
                skipped.append(f"{name}: {fg}/{bg} ({exc})")
                continue
            floor = AA_LARGE if large else AA_NORMAL
            if ratio < floor:
                problems.append(f"{name}: {fg} on {bg} = {ratio:.2f}:1 (need {floor})")
    passed = not problems
    detail = "contrast pairs meet WCAG AA" if passed else (
        f"{len(problems)} low-contrast pair(s): " + "; ".join(problems[:6])
    )
    if skipped:
        detail += f" [{len(skipped)} skipped: " + "; ".join(skipped[:3]) + "]"
    return ValidationCheck(
        name="web-contrast",
        passed=passed,
        details=detail,
        code=None if passed else "web_contrast",
    )


def _resolve(dist_dir: Path, html_file: Path, target: str) -> Path | None:
    """Resolve a link target (root-relative or document-relative) to a path in
    ``dist``. Directory links map to their ``index.html``. Returns None if the
    target escapes ``dist``."""
    if target.startswith("/"):
        base = dist_dir / target.lstrip("/")
    else:
        base = (html_file.parent / target).resolve()
    try:
        base.relative_to(dist_dir.resolve())
    except ValueError:
        return None
    if base.is_dir() or target.endswith("/"):
        return base / "index.html"
    return base


@dataclass(frozen=True)
class WebValidationReport:
    checks: list[ValidationCheck]

    @property
    def passed(self) -> bool:
        return all(check.passed for check in self.checks)

    @property
    def failures(self) -> list[ValidationCheck]:
        return [check for check in self.checks if not check.passed]

    def to_dict(self) -> dict[str, object]:
        return {
            "passed": self.passed,
            "checks": [check.to_dict() for check in self.checks],
        }


def validate_web_dist(
    dist_dir: Path,
    *,
    build_exit_code: int | None = None,
    build_stdout: str = "",
    build_stderr: str = "",
) -> WebValidationReport:
    """Run the full web gate over a built ``dist`` directory.

    Pass ``build_exit_code`` to include the build result (the worker has it);
    omit it to validate an already-built directory (tests, re-checks).
    """
    checks: list[ValidationCheck] = []
    if build_exit_code is not None:
        checks.append(check_build(build_exit_code, build_stdout, build_stderr))
    checks.append(check_internal_links(dist_dir))
    checks.append(check_assets(dist_dir))
    checks.append(check_responsive(dist_dir))
    checks.append(check_accessibility(dist_dir))
    checks.append(check_contrast(dist_dir))
    return WebValidationReport(checks=checks)
