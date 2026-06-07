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

import hashlib
import html
import json
import re
from dataclasses import dataclass
from pathlib import Path

# A page whose body has fewer than this many words is "thin" and rejected.
MIN_BODY_WORDS = 60

# Two pages whose bodies share at least this fraction of word 3-grams are
# "near-duplicate" — the doorway-page pattern Google penalizes. Above this, the
# matrix is rejected so the operator must add real per-page content instead of
# silently shipping token-swapped clones (the whole point of the service).
MAX_BODY_SIMILARITY = 0.5

# Deterministically-selected sentence pools. Each page draws one line from each
# pool keyed on a hash of (service, city, slot), so two pages that differ only by
# city still diverge across most slots — varied prose, not a find-replace clone.
_INTRO = (
    "{biz} delivers {svc_l} that {city} homeowners and businesses can count on.",
    "When you need {svc_l} in {city}, {biz} is the local team to call.",
    "{biz} has become a trusted name for {svc_l} across {city}.",
    "For dependable {svc_l} in {city}, neighbors turn to {biz}.",
    "{biz} brings hands-on {svc_l} expertise to every corner of {city}.",
    "Looking for {svc_l} done right the first time in {city}? Start with {biz}.",
)
_SCOPE = (
    "Our crew handles everything from routine work to urgent, same-day jobs.",
    "We take on projects large and small, from quick fixes to full installs.",
    "Whether it's a planned upgrade or an emergency, we scope the job honestly.",
    "Each visit starts with a clear assessment so you know exactly what's needed.",
    "We size every job to your property — no upsells, no surprises.",
    "From the first call to the final walkthrough, we keep the work tidy and on time.",
)
_DETAIL = (
    "We arrive on time, explain the options in plain language, and clean up after.",
    "Our team uses quality materials and proven methods built to last for years.",
    "Expect clear communication, fair timelines, and workmanship you can inspect.",
    "We document the job with photos and a simple summary you can keep.",
    "Scheduling is easy, and we'll work around the hours that suit your day.",
    "You'll deal with seasoned pros, not a rotating cast of subcontractors.",
)
_LOCAL = (
    "As a {city}-based business, we know the neighborhoods, codes, and weather here.",
    "Being local to {city} means faster arrival times and answers you can trust.",
    "We're part of the {city} community and treat every job like it's next door.",
    "Years of work in {city} mean we've seen the quirks of local properties.",
    "Our roots in {city} keep us accountable to the people we serve.",
    "We understand what {city} property owners expect because we live here too.",
)
_TRUST = (
    "Every job is backed by upfront pricing and a satisfaction guarantee.",
    "You get a written estimate before we start and a guarantee when we finish.",
    "Licensed, insured, and reviewed by your {city} neighbors.",
    "We stand behind our work with clear warranties and honest follow-up.",
    "No hidden fees — just transparent quotes and workmanship we warranty.",
    "Our reputation in {city} is built on doing what we say we'll do.",
)
_CTA = (
    "Call today for a free {svc_l} estimate in {city}.",
    "Reach out now to schedule your {svc_l} appointment in {city}.",
    "Get a fast, free quote for {svc_l} anywhere in {city}.",
    "Book your {city} {svc_l} service today and see the difference.",
    "Contact {biz} for {svc_l} in {city} — we respond quickly.",
    "Ready to get started? Request your free {city} {svc_l} estimate.",
)


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


def _pick(pool: tuple[str, ...], service: str, city: str, slot: int) -> str:
    """Deterministically choose one line from ``pool`` for this (service, city, slot).

    Uses a stable hash (not Python's salted ``hash()``) so output is reproducible
    across processes, and varies per slot so adjacent slots don't move in lockstep.
    """
    seed = f"{service}|{city}|{slot}".encode("utf-8")
    idx = int.from_bytes(hashlib.sha256(seed).digest()[:4], "big") % len(pool)
    return pool[idx]


def _compose_body(
    business_name: str, service: str, city: str, differentiators: list[str]
) -> str:
    """Assemble a varied page body from deterministic pools + any differentiators.

    Two pages that share a service but differ by city draw different lines from
    most pools, so the bodies are materially different prose rather than a
    city-token find-replace. The near-duplicate guard in :func:`generate_matrix`
    enforces that this variation is actually sufficient.
    """
    ctx = {"biz": business_name, "svc_l": service.lower(), "city": city}
    parts = [
        _pick(_INTRO, service, city, 0).format(**ctx),
        _pick(_SCOPE, service, city, 1).format(**ctx),
        _pick(_DETAIL, service, city, 5).format(**ctx),
        _pick(_LOCAL, service, city, 2).format(**ctx),
        _pick(_TRUST, service, city, 3).format(**ctx),
    ]
    if differentiators:
        diff = ", ".join(d.lower() for d in differentiators[:3])
        parts.append(f"Clients choose {business_name} for {diff}.")
    parts.append(_pick(_CTA, service, city, 4).format(**ctx))
    return " ".join(parts)


def _shingles(text: str, n: int = 3) -> set[tuple[str, ...]]:
    """Word n-gram shingles of ``text`` (lowercased alnum tokens)."""
    tokens = re.findall(r"[a-z0-9]+", text.lower())
    if len(tokens) < n:
        return {tuple(tokens)} if tokens else set()
    return {tuple(tokens[i : i + n]) for i in range(len(tokens) - n + 1)}


def body_similarity(a: str, b: str) -> float:
    """Jaccard similarity of two bodies over word 3-gram shingles (0.0–1.0)."""
    sa, sb = _shingles(a), _shingles(b)
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / len(sa | sb)


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
    body = _compose_body(business_name, service, city, differentiators or [])
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
    max_similarity: float = MAX_BODY_SIMILARITY,
) -> list[SeoPage]:
    """Generate the full service x geo matrix, rejecting thin/duplicate pages.

    Three guards, escalating from cheap to real:

    * ``ThinContentError`` if any two pages collide on slug or title (duplicate
      inputs);
    * ``ThinContentError`` per page below ``min_words`` (thin);
    * ``ThinContentError`` if any two bodies exceed ``max_similarity`` word-3-gram
      Jaccard overlap — the near-duplicate / doorway-page guard. When this fires,
      the inputs are too samey to generate distinct pages safely; add real
      per-page differentiators or trim the matrix rather than ship clones.
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
            for kept in pages:
                sim = body_similarity(page.body, kept.body)
                if sim >= max_similarity:
                    raise ThinContentError(
                        f"near-duplicate body: {page.slug!r} vs {kept.slug!r} "
                        f"({sim:.0%} 3-gram overlap >= {max_similarity:.0%}) — add real "
                        "per-page content or differentiators before publishing"
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
