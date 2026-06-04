"""Local SEO page generation (Agency layer, Phase 6).

Generates a differentiated set of locally-targeted pages from a service x geo
matrix (e.g. "Roof Repair Dallas", "Emergency Roof Repair Dallas"). This is the
highest-AI-leverage recurring service: dozens of quality local pages in minutes.

Guards against thin / near-duplicate content: each page must carry a unique
title, slug, and meta description, and the body must clear a minimum word count.
The generator reuses the per-page metadata conventions of the web scaffold rather
than forking a new templating system.
"""

from __future__ import annotations

import html
import json
import re
from dataclasses import dataclass
from pathlib import Path

# A page whose body has fewer than this many words is "thin" and rejected.
MIN_BODY_WORDS = 60


class ThinContentError(ValueError):
    """Raised when a generated page would be thin / near-duplicate."""


class LocalSeoMatrixError(ValueError):
    """Raised when ``LOCAL_SEO.md`` is missing approved generation inputs."""


@dataclass(frozen=True)
class LocalSeoMatrix:
    primary_city: str
    services: list[str]
    service_area_cities: list[str]
    matrix_approved: bool = False


@dataclass(frozen=True)
class SeoPage:
    slug: str
    title: str
    meta_description: str
    h1: str
    body: str

    def word_count(self) -> int:
        return len(self.body.split())

    def to_dict(self) -> dict[str, object]:
        return {
            "slug": self.slug,
            "title": self.title,
            "meta_description": self.meta_description,
            "h1": self.h1,
            "body": self.body,
        }


def _slug(*parts: str) -> str:
    joined = "-".join(parts)
    return re.sub(r"[^a-z0-9]+", "-", joined.strip().lower()).strip("-")


def generate_page(
    business_name: str,
    service: str,
    city: str,
    *,
    differentiators: list[str] | None = None,
    min_words: int = MIN_BODY_WORDS,
) -> SeoPage:
    """Generate one service x geo page with unique metadata + non-thin body.

    Raises :class:`ThinContentError` if the body has fewer than ``min_words``
    words — a guard against publishing thin pages that hurt SEO.
    """
    differentiators = differentiators or []
    title = f"{service} in {city} | {business_name}"
    slug = _slug(service, city)
    meta = (
        f"Looking for {service.lower()} in {city}? {business_name} offers fast, "
        f"reliable {service.lower()} for {city} homes and businesses. Free estimates."
    )
    h1 = f"{service} in {city}"
    diff_line = ""
    if differentiators:
        diff_line = " ".join(f"We're known for {d.lower()}." for d in differentiators[:3])
    body = (
        f"{business_name} provides professional {service.lower()} throughout {city} "
        f"and the surrounding area. Whether you need routine {service.lower()} or an "
        f"urgent fix, our local team responds quickly and gets the job done right the "
        f"first time. {diff_line} "
        f"As a {city}-based business, we understand the needs of {city} property owners "
        f"and stand behind every job with upfront pricing and a satisfaction guarantee. "
        f"Call today for a free {service.lower()} estimate in {city}."
    )
    page = SeoPage(slug=slug, title=title, meta_description=meta, h1=h1, body=body)
    if page.word_count() < min_words:
        raise ThinContentError(
            f"page {slug!r} is thin ({page.word_count()} words < {min_words})"
        )
    return page


def generate_matrix(
    business_name: str,
    services: list[str],
    cities: list[str],
    *,
    differentiators: list[str] | None = None,
    min_words: int = MIN_BODY_WORDS,
) -> list[SeoPage]:
    """Generate the full service x geo matrix, rejecting thin/duplicate pages.

    Raises ``ThinContentError`` if any two pages collide on slug or title (a sign
    the matrix has duplicate inputs that would produce near-duplicate pages).
    """
    pages: list[SeoPage] = []
    seen_slugs: set[str] = set()
    seen_titles: set[str] = set()
    for service in services:
        for city in cities:
            page = generate_page(
                business_name,
                service,
                city,
                differentiators=differentiators,
                min_words=min_words,
            )
            if page.slug in seen_slugs or page.title in seen_titles:
                raise ThinContentError(
                    f"duplicate page for {service!r} x {city!r} (slug {page.slug!r})"
                )
            seen_slugs.add(page.slug)
            seen_titles.add(page.title)
            pages.append(page)
    return pages


def parse_local_seo_matrix(path_or_text: Path | str) -> LocalSeoMatrix:
    """Parse approved service-area inputs from ``LOCAL_SEO.md`` text or path.

    YAML fenced blocks are preferred. A markdown table is accepted for services
    and cities, but approval still must be present as ``matrix_approved: true``.
    """
    text = (
        path_or_text.read_text(encoding="utf-8")
        if isinstance(path_or_text, Path)
        else path_or_text
    )
    yaml_block = _fenced_yaml(text)
    primary_city = _yaml_scalar(yaml_block, "primary_city")
    services = _yaml_list(yaml_block, "services")
    cities = _yaml_list(yaml_block, "service_area_cities")
    matrix_approved = _yaml_bool(yaml_block, "matrix_approved")
    if not services or not cities:
        table_services, table_cities = _table_matrix(text)
        services = services or table_services
        cities = cities or table_cities
    if not primary_city:
        primary_city = cities[0] if cities else ""
    if not primary_city or not services or not cities:
        raise LocalSeoMatrixError("LOCAL_SEO.md must include primary city, services, and service-area cities")
    if _has_tbd(primary_city, services, cities):
        raise LocalSeoMatrixError("LOCAL_SEO.md still contains TBD matrix values")
    if not matrix_approved:
        raise LocalSeoMatrixError("LOCAL_SEO.md matrix_approved must be true before generation")
    return LocalSeoMatrix(
        primary_city=primary_city,
        services=services,
        service_area_cities=cities,
        matrix_approved=matrix_approved,
    )


def emit_seo_pages_to_site(
    site_root: Path,
    pages: list[SeoPage],
    *,
    site_url: str = "https://example.com",
) -> list[Path]:
    """Write SEO pages into an Astro site and emit a local sitemap."""
    pages_dir = site_root / "src" / "pages"
    if not pages_dir.is_dir():
        raise FileNotFoundError(f"Astro pages directory not found: {pages_dir}")
    written: list[Path] = []
    for page in pages:
        path = pages_dir / f"{page.slug}.astro"
        path.write_text(_astro_page(page), encoding="utf-8")
        written.append(path)
    public_dir = site_root / "public"
    public_dir.mkdir(exist_ok=True)
    sitemap = public_dir / "sitemap-local-seo.xml"
    sitemap.write_text(_sitemap(pages, site_url=site_url), encoding="utf-8")
    written.append(sitemap)
    return written


def _fenced_yaml(text: str) -> str:
    match = re.search(r"```ya?ml\s*(.*?)```", text, flags=re.DOTALL | re.IGNORECASE)
    return match.group(1) if match else ""


def _yaml_scalar(text: str, key: str) -> str:
    match = re.search(rf"^{re.escape(key)}:\s*(.*?)\s*$", text, flags=re.MULTILINE)
    if not match:
        return ""
    return match.group(1).strip().strip('"').strip("'")


def _yaml_bool(text: str, key: str) -> bool:
    return _yaml_scalar(text, key).lower() == "true"


def _yaml_list(text: str, key: str) -> list[str]:
    match = re.search(rf"^{re.escape(key)}:\s*(\[.*?\])\s*$", text, flags=re.MULTILINE)
    if not match:
        return []
    raw = match.group(1)
    try:
        values = json.loads(raw)
    except json.JSONDecodeError:
        values = [part.strip().strip('"').strip("'") for part in raw.strip("[]").split(",")]
    return [str(value).strip() for value in values if str(value).strip()]


def _table_matrix(text: str) -> tuple[list[str], list[str]]:
    services: set[str] = set()
    cities: set[str] = set()
    for line in text.splitlines():
        if not line.startswith("|") or "---" in line or "Service" in line:
            continue
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if len(cells) < 2:
            continue
        service, city = cells[0], cells[1]
        if service and city:
            services.add(service)
            cities.add(city)
    return sorted(services), sorted(cities)


def _has_tbd(primary_city: str, services: list[str], cities: list[str]) -> bool:
    values = [primary_city, *services, *cities]
    return any(value.strip().lower() in {"_tbd_", "tbd", ""} for value in values)


def _astro_page(page: SeoPage) -> str:
    return "\n".join(
        [
            "---",
            'import "../styles/global.css";',
            "---",
            "<!doctype html>",
            '<html lang="en">',
            "<head>",
            '  <meta charset="utf-8" />',
            '  <meta name="viewport" content="width=device-width, initial-scale=1" />',
            f"  <title>{html.escape(page.title)}</title>",
            f'  <meta name="description" content="{html.escape(page.meta_description)}" />',
            "</head>",
            "<body>",
            '  <main class="section">',
            '    <div class="container stack-lg">',
            f"      <h1>{html.escape(page.h1)}</h1>",
            f"      <p>{html.escape(page.body)}</p>",
            '      <p><a href="/">Back home</a></p>',
            "    </div>",
            "  </main>",
            "</body>",
            "</html>",
            "",
        ]
    )


def _sitemap(pages: list[SeoPage], *, site_url: str) -> str:
    base = site_url.rstrip("/")
    urls = "\n".join(
        f"  <url><loc>{html.escape(base)}/{page.slug}</loc></url>" for page in pages
    )
    return "\n".join(
        [
            '<?xml version="1.0" encoding="UTF-8"?>',
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
            urls,
            "</urlset>",
            "",
        ]
    )
