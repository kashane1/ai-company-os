"""Agency layer Phase 6 — local SEO service x geo page generation."""

from __future__ import annotations

import pytest

from packages.agency.local_seo import (
    MIN_BODY_WORDS,
    ThinContentError,
    generate_matrix,
    generate_page,
)


def test_matrix_produces_distinct_pages() -> None:
    services = ["Roof Repair", "Roof Replacement", "Emergency Roof Repair", "Commercial Roofing"]
    cities = ["Dallas", "Plano", "Frisco"]
    pages = generate_matrix("Lone Star Roofing", services, cities)
    assert len(pages) == len(services) * len(cities)  # 12
    # All slugs and titles unique.
    assert len({p.slug for p in pages}) == len(pages)
    assert len({p.title for p in pages}) == len(pages)


def test_page_metadata_is_localized() -> None:
    page = generate_page("Lone Star Roofing", "Emergency Roof Repair", "Dallas")
    assert page.slug == "emergency-roof-repair-dallas"
    assert "Dallas" in page.title
    assert "Dallas" in page.meta_description
    assert page.h1 == "Emergency Roof Repair in Dallas"


def test_pages_are_not_thin() -> None:
    pages = generate_matrix("Lone Star Roofing", ["Roof Repair"], ["Dallas", "Plano"])
    for page in pages:
        assert page.word_count() >= MIN_BODY_WORDS


def test_duplicate_inputs_rejected() -> None:
    with pytest.raises(ThinContentError):
        generate_matrix("Lone Star Roofing", ["Roof Repair", "Roof Repair"], ["Dallas"])


def test_thin_content_guard_fires() -> None:
    # Raising the bar above the template's word count must trip the guard.
    with pytest.raises(ThinContentError):
        generate_page("Lone Star Roofing", "Roof Repair", "Dallas", min_words=10_000)
    with pytest.raises(ThinContentError):
        generate_matrix("Lone Star Roofing", ["Roof Repair"], ["Dallas"], min_words=10_000)


def test_page_round_trips() -> None:
    page = generate_page("Lone Star Roofing", "Roof Repair", "Dallas")
    assert page.to_dict()["slug"] == page.slug
