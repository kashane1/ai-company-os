"""Web UX audit — deeper responsive / a11y / performance scoring (F7).

The F2 gate is the fail-closed minimum (build, links, assets, a viewport, basic
a11y). This audit goes further and *scores* the built site the way a Lighthouse
pass would, across four categories, so the web lane can judge polish — not just
"does it render". Advisory by default (a report with scores + findings), but the
worker can treat a low score as a blocker.

All heuristics are static (parse the built HTML/CSS + file sizes), so it's
offline and unit-testable. Categories:

* **responsive** — a real viewport (zoom not disabled) plus evidence of
  responsive technique (media queries / fluid units / flexible grids).
* **accessibility** — lang, title, single h1, no skipped heading levels, image
  alts, named controls, labelled form inputs.
* **performance** — total page weight budget, render-blocking resource count,
  oversized images.
* **seo** — title length, meta description, Open Graph tags.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from html.parser import HTMLParser
from pathlib import Path

RESPONSIVE_CSS_SIGNALS = ("@media", "clamp(", "minmax(", "auto-fit", "auto-fill",
                          "flex-wrap", "vw", "vh", "%", "grid-template")

# Budgets (static, Lighthouse-flavored).
MAX_PAGE_WEIGHT_BYTES = 2_000_000      # total dist weight
MAX_BLOCKING_RESOURCES = 8             # stylesheets + sync scripts in <head>
MAX_IMAGE_BYTES = 600_000              # any single image


@dataclass
class _AuditedPage:
    title: str | None = None
    lang: str | None = None
    viewport_content: str | None = None
    meta_description: str | None = None
    og_tags: int = 0
    heading_levels: list[int] = field(default_factory=list)
    images_missing_alt: int = 0
    interactive_without_name: int = 0
    inputs_total: int = 0
    inputs_labelled: int = 0
    stylesheet_links: int = 0
    blocking_scripts: int = 0
    inline_styles: list[str] = field(default_factory=list)
    label_for_ids: set[str] = field(default_factory=set)


class _AuditParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.page = _AuditedPage()
        self._in_title = False
        self._in_style = False
        self._interactive_depth = 0
        self._interactive_attrs: list[dict[str, str]] = []
        self._interactive_text: list[str] = []
        # Two-pass-ish: collect label[for] then resolve inputs at end.
        self._pending_inputs: list[dict[str, str]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        a = {k: (v or "") for k, v in attrs}
        if tag == "html" and a.get("lang", "").strip():
            self.page.lang = a["lang"].strip()
        if tag == "title":
            self._in_title = True
        if tag == "style":
            self._in_style = True
        if tag == "meta":
            name = a.get("name", "").lower()
            prop = a.get("property", "").lower()
            if name == "viewport":
                self.page.viewport_content = a.get("content", "")
            if name == "description":
                self.page.meta_description = a.get("content", "")
            if prop.startswith("og:"):
                self.page.og_tags += 1
        if tag in ("h1", "h2", "h3", "h4", "h5", "h6"):
            self.page.heading_levels.append(int(tag[1]))
        if tag == "img" and "alt" not in a:
            self.page.images_missing_alt += 1
        if tag == "link" and "stylesheet" in a.get("rel", "").lower():
            self.page.stylesheet_links += 1
        if tag == "script" and a.get("src") and "defer" not in a and "async" not in a:
            self.page.blocking_scripts += 1
        if tag == "label" and a.get("for", "").strip():
            self.page.label_for_ids.add(a["for"].strip())
        if tag in ("input", "select", "textarea") and a.get("type", "") not in (
            "hidden", "submit", "button"
        ):
            self._pending_inputs.append(a)
        if tag in ("a", "button"):
            self._interactive_depth += 1
            self._interactive_attrs.append(a)
            self._interactive_text.append("")

    def handle_endtag(self, tag: str) -> None:
        if tag == "title":
            self._in_title = False
        if tag == "style":
            self._in_style = False
        if tag in ("a", "button") and self._interactive_attrs:
            attrs = self._interactive_attrs.pop()
            text = self._interactive_text.pop().strip()
            named = bool(text or attrs.get("aria-label", "").strip()
                         or attrs.get("title", "").strip()
                         or attrs.get("aria-labelledby", "").strip())
            if not named:
                self.page.interactive_without_name += 1

    def handle_data(self, data: str) -> None:
        if self._in_title:
            self.page.title = (self.page.title or "") + data
        if self._in_style:
            self.page.inline_styles.append(data)
        if self._interactive_text:
            self._interactive_text[-1] += data

    def finalize(self) -> _AuditedPage:
        for attrs in self._pending_inputs:
            self.page.inputs_total += 1
            labelled = bool(
                attrs.get("aria-label", "").strip()
                or attrs.get("aria-labelledby", "").strip()
                or (attrs.get("id", "").strip() in self.page.label_for_ids)
            )
            if labelled:
                self.page.inputs_labelled += 1
        if self.page.title is not None:
            self.page.title = self.page.title.strip() or None
        return self.page


def _audit_page(html: str) -> _AuditedPage:
    parser = _AuditParser()
    parser.feed(html)
    return parser.finalize()


@dataclass(frozen=True)
class Finding:
    severity: str  # "error" | "warn"
    message: str


@dataclass(frozen=True)
class AuditCategory:
    name: str
    score: int            # 0-100
    findings: list[Finding] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "score": self.score,
            "findings": [{"severity": f.severity, "message": f.message} for f in self.findings],
        }


@dataclass(frozen=True)
class UxAuditReport:
    categories: list[AuditCategory]
    pass_threshold: int = 70

    @property
    def scores(self) -> dict[str, int]:
        return {c.name: c.score for c in self.categories}

    @property
    def overall(self) -> int:
        if not self.categories:
            return 0
        return round(sum(c.score for c in self.categories) / len(self.categories))

    @property
    def passed(self) -> bool:
        return all(c.score >= self.pass_threshold for c in self.categories)

    def to_dict(self) -> dict[str, object]:
        return {
            "overall": self.overall,
            "passed": self.passed,
            "pass_threshold": self.pass_threshold,
            "categories": [c.to_dict() for c in self.categories],
        }


def _clamp(score: int) -> int:
    return max(0, min(100, score))


def _html_files(dist_dir: Path) -> list[Path]:
    return sorted(p for p in dist_dir.rglob("*.html") if p.is_file())


def _score_responsive(pages: list[_AuditedPage], css_blob: str) -> AuditCategory:
    findings: list[Finding] = []
    score = 100
    for i, p in enumerate(pages):
        vp_compact = (p.viewport_content or "").replace(" ", "")
        if "width=device-width" not in vp_compact:
            findings.append(Finding("error", f"page {i}: missing width=device-width viewport"))
            score -= 40
        vp = (p.viewport_content or "").replace(" ", "").lower()
        if "user-scalable=no" in vp or "maximum-scale=1" in vp:
            findings.append(Finding("error", f"page {i}: viewport disables zoom (a11y)"))
            score -= 20
    if not any(sig in css_blob for sig in RESPONSIVE_CSS_SIGNALS):
        findings.append(Finding("warn", "no responsive CSS technique detected "
                                "(media query / clamp / fluid units / flexible grid)"))
        score -= 25
    return AuditCategory("responsive", _clamp(score), findings)


def _score_accessibility(pages: list[_AuditedPage]) -> AuditCategory:
    findings: list[Finding] = []
    penalty = 0

    def flag(severity: str, message: str, cost: int) -> None:
        nonlocal penalty
        findings.append(Finding(severity, message))
        penalty += cost

    for i, p in enumerate(pages):
        if not p.lang:
            flag("error", f"page {i}: <html> missing lang", 15)
        if not p.title:
            flag("error", f"page {i}: missing <title>", 15)
        h1s = [lvl for lvl in p.heading_levels if lvl == 1]
        if len(h1s) == 0:
            flag("error", f"page {i}: no <h1>", 15)
        elif len(h1s) > 1:
            flag("warn", f"page {i}: {len(h1s)} <h1> (want 1)", 8)
        if _skips_heading_level(p.heading_levels):
            flag("warn", f"page {i}: skipped heading level", 8)
        if p.images_missing_alt:
            flag("error", f"page {i}: {p.images_missing_alt} img without alt", 12)
        if p.interactive_without_name:
            flag("error", f"page {i}: {p.interactive_without_name} control without a name", 12)
        unlabelled = p.inputs_total - p.inputs_labelled
        if unlabelled > 0:
            flag("error", f"page {i}: {unlabelled} form input(s) without a label", 12)
    return AuditCategory("accessibility", _clamp(100 - penalty), findings)


def _skips_heading_level(levels: list[int]) -> bool:
    prev = 0
    for lvl in levels:
        if prev and lvl > prev + 1:
            return True
        prev = lvl
    return False


def _score_performance(dist_dir: Path, pages: list[_AuditedPage]) -> AuditCategory:
    findings: list[Finding] = []
    score = 100
    total = sum(p.stat().st_size for p in dist_dir.rglob("*") if p.is_file())
    if total > MAX_PAGE_WEIGHT_BYTES:
        findings.append(Finding("warn", f"total weight {total // 1024}KB exceeds "
                                f"{MAX_PAGE_WEIGHT_BYTES // 1024}KB budget"))
        score -= 25
    blocking = max((p.stylesheet_links + p.blocking_scripts) for p in pages) if pages else 0
    if blocking > MAX_BLOCKING_RESOURCES:
        findings.append(Finding("warn", f"{blocking} render-blocking resources "
                                f"(budget {MAX_BLOCKING_RESOURCES})"))
        score -= 20
    image_exts = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".avif"}
    for img in dist_dir.rglob("*"):
        if not (img.is_file() and img.suffix.lower() in image_exts):
            continue
        if img.stat().st_size > MAX_IMAGE_BYTES:
            findings.append(Finding("warn", f"{img.name} is {img.stat().st_size // 1024}KB "
                                    f"(>{MAX_IMAGE_BYTES // 1024}KB)"))
            score -= 10
    return AuditCategory("performance", _clamp(score), findings)


def _score_seo(pages: list[_AuditedPage]) -> AuditCategory:
    findings: list[Finding] = []
    penalty = 0

    def flag(severity: str, message: str, cost: int) -> None:
        nonlocal penalty
        findings.append(Finding(severity, message))
        penalty += cost

    for i, p in enumerate(pages):
        if not p.title:
            flag("error", f"page {i}: missing <title>", 25)
        elif not (10 <= len(p.title) <= 70):
            flag("warn", f"page {i}: title length {len(p.title)} outside 10-70 chars", 8)
        if not p.meta_description:
            flag("warn", f"page {i}: missing meta description", 20)
        if p.og_tags == 0:
            flag("warn", f"page {i}: no Open Graph tags", 10)
    return AuditCategory("seo", _clamp(100 - penalty), findings)


def audit_dist(dist_dir: Path, *, pass_threshold: int = 70) -> UxAuditReport:
    """Audit a built site directory across all four categories."""
    html_files = _html_files(dist_dir)
    pages = [_audit_page(f.read_text(encoding="utf-8", errors="ignore")) for f in html_files]
    css_blob = "".join(f.read_text(encoding="utf-8", errors="ignore")
                       for f in dist_dir.rglob("*.css") if f.is_file())
    css_blob += "".join("".join(p.inline_styles) for p in pages)
    return UxAuditReport(
        categories=[
            _score_responsive(pages, css_blob),
            _score_accessibility(pages),
            _score_performance(dist_dir, pages),
            _score_seo(pages),
        ],
        pass_threshold=pass_threshold,
    )
