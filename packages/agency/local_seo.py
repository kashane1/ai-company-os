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

import re
from dataclasses import dataclass

# A page whose body has fewer than this many words is "thin" and rejected.
MIN_BODY_WORDS = 60


class ThinContentError(ValueError):
    """Raised when a generated page would be thin / near-duplicate."""


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
