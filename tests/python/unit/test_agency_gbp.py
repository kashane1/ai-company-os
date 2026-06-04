"""Tests for the GBP changeset draft (G7)."""

from __future__ import annotations

from pathlib import Path

import pytest

from packages.agency.gbp import (
    draft_gbp_changeset,
    emit_gbp_changeset,
    suggest_primary_category,
)
from packages.agency.intake import ClientIntake


def _intake(**kw) -> ClientIntake:
    base = dict(
        business_name="Joe's Plumbing",
        service_category="plumbing",
        city="Austin, TX",
        services=["Drain cleaning", "Water heaters"],
        hours="Mon-Fri 8-6",
        phone="512-555-0100",
        service_area_cities=["Austin", "Round Rock"],
    )
    base.update(kw)
    return ClientIntake(**base)


@pytest.mark.parametrize(
    "category,expected",
    [
        ("plumbing", "Plumber"),
        ("dog grooming", "Pet groomer"),
        ("nail salon", "Nail salon"),
        ("artisanal cheese shop", "Artisanal Cheese Shop"),  # fallback: title-cased
    ],
)
def test_suggest_primary_category(category: str, expected: str) -> None:
    assert suggest_primary_category(category) == expected


def test_draft_pulls_from_intake() -> None:
    cs = draft_gbp_changeset(_intake(), booking_url="https://book.example.com")
    assert cs.primary_category == "Plumber"
    assert cs.services == ("Drain cleaning", "Water heaters")
    assert cs.hours == "Mon-Fri 8-6"
    assert cs.booking_url == "https://book.example.com"
    assert cs.service_area == ("Austin", "Round Rock")
    assert "Joe's Plumbing provides plumbing for Austin, TX" in cs.description
    assert len(cs.description) <= 750


def test_markdown_has_all_sections() -> None:
    md = draft_gbp_changeset(_intake(), booking_url="https://book.x").to_markdown()
    for heading in ("Primary category", "Services", "Hours", "Description", "Photos to add"):
        assert f"## {heading}" in md or heading in md
    assert "Plumber" in md
    assert "Drain cleaning" in md
    assert "https://book.x" in md
    assert "[D6]" in md  # advisory note present


def test_service_area_falls_back_to_city() -> None:
    cs = draft_gbp_changeset(_intake(service_area_cities=[]))
    assert cs.service_area == ("Austin, TX",)


def test_draft_requires_valid_intake() -> None:
    with pytest.raises(ValueError):
        draft_gbp_changeset(ClientIntake(business_name="", service_category="x", city="y"))


def test_emit_writes_changeset(tmp_path: Path) -> None:
    path = emit_gbp_changeset(_intake(), tmp_path / "joes-site")
    assert path == tmp_path / "joes-site" / "GBP_CHANGESET.md"
    assert "GBP Changeset — Joe's Plumbing" in path.read_text(encoding="utf-8")
