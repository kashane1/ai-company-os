"""Agency layer Phase 6 — local SEO service x geo page generation."""

from __future__ import annotations

import pytest

from packages.agency.local_seo import (
    LocalSeoMatrixError,
    MIN_BODY_WORDS,
    ThinContentError,
    emit_seo_pages_to_site,
    generate_matrix,
    generate_page,
    parse_local_seo_matrix,
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


def test_parse_approved_yaml_matrix() -> None:
    matrix = parse_local_seo_matrix(
        """
```yaml
primary_city: "Tacoma"
service_area_cities: ["Tacoma", "Federal Way"]
services: ["Drain cleaning", "Leak repair"]
matrix_approved: true
```
"""
    )
    assert matrix.primary_city == "Tacoma"
    assert matrix.service_area_cities == ["Tacoma", "Federal Way"]
    assert matrix.services == ["Drain cleaning", "Leak repair"]


def test_parse_matrix_requires_approval() -> None:
    with pytest.raises(LocalSeoMatrixError):
        parse_local_seo_matrix(
            """
```yaml
primary_city: "Tacoma"
service_area_cities: ["Tacoma"]
services: ["Drain cleaning"]
matrix_approved: false
```
"""
        )


def test_parse_table_matrix_uses_yaml_approval() -> None:
    matrix = parse_local_seo_matrix(
        """
| Service | City / area | Notes |
|---|---|---|
| Drain cleaning | Tacoma | |
| Leak repair | Federal Way | |

```yaml
matrix_approved: true
```
"""
    )
    assert matrix.primary_city == "Federal Way"
    assert matrix.service_area_cities == ["Federal Way", "Tacoma"]
    assert matrix.services == ["Drain cleaning", "Leak repair"]


def test_emit_seo_pages_to_astro_site(tmp_path) -> None:
    site = tmp_path / "site"
    (site / "src" / "pages").mkdir(parents=True)
    (site / "src" / "styles").mkdir(parents=True)
    page = generate_page("Lone Star Roofing", "Roof Repair", "Dallas")

    written = emit_seo_pages_to_site(site, [page], site_url="https://example.com")

    page_path = site / "src" / "pages" / "roof-repair-dallas.astro"
    sitemap = site / "public" / "sitemap-local-seo.xml"
    assert page_path in written
    assert sitemap in written
    assert "Roof Repair in Dallas" in page_path.read_text(encoding="utf-8")
    assert "https://example.com/roof-repair-dallas" in sitemap.read_text(encoding="utf-8")
