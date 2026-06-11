from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from packages.agency.conversion_personas import (
    PersonaPackError,
    load_audience_panel,
    load_persona_pack,
)


def test_load_med_spa_persona_pack() -> None:
    pack = load_persona_pack("med_spa")

    assert pack.vertical == "med_spa"
    assert len(pack.personas) >= 7
    for persona in pack.personas:
        assert persona.persona_id
        assert persona.vertical == "med_spa"
        assert persona.dossier
        assert persona.trust_signals
        assert persona.objections
        assert persona.review_prompt


def test_duplicate_persona_ids_fail_validation(tmp_path: Path) -> None:
    root = tmp_path / "packs"
    root.mkdir()
    (root / "med_spa.yaml").write_text(
        textwrap.dedent(
            """
            vertical: med_spa
            personas:
              - persona_id: same
                dossier: One
                trust_signals: [Credentials]
                objections: [Price]
                review_prompt: Review this page.
              - persona_id: same
                dossier: Two
                trust_signals: [Reviews]
                objections: [Safety]
                review_prompt: Review this page.
            """
        ),
        encoding="utf-8",
    )

    with pytest.raises(PersonaPackError, match="duplicate"):
        load_persona_pack("med_spa", root=root)


def test_missing_persona_pack_fails_clearly(tmp_path: Path) -> None:
    with pytest.raises(PersonaPackError, match="missing persona pack"):
        load_persona_pack("roofing", root=tmp_path)


def test_load_audience_panel_composes_core_personas_with_modifier() -> None:
    panel = load_audience_panel("plumber")

    assert panel.vertical == "plumber"
    assert panel.modifier.modifier_id == "home_services"
    assert len(panel.personas) >= 12
    assert any(p.persona_id == "urgent-problem-solver" for p in panel.personas)
    assert any("emergency" in item.lower() for item in panel.modifier.decision_triggers)


def test_common_small_business_aliases_resolve_to_modifiers() -> None:
    assert load_audience_panel("barber_shop").modifier.modifier_id == "personal_care"
    assert load_audience_panel("dentist").modifier.modifier_id == "health_wellness"
    assert load_audience_panel("auto_repair").modifier.modifier_id == "auto_services"
    assert load_audience_panel("restaurant").modifier.modifier_id == "food_hospitality"
    assert load_audience_panel("notary").modifier.modifier_id == "professional_services"


def test_existing_full_vertical_pack_is_included_in_audience_panel() -> None:
    panel = load_audience_panel("med_spa")

    assert panel.modifier.modifier_id == "health_wellness"
    assert any(p.persona_id == "nervous-first-time-buyer" for p in panel.personas)
    assert any(p.persona_id == "urgent-problem-solver" for p in panel.personas)
