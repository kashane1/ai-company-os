from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from packages.agency.conversion_personas import PersonaPackError, load_persona_pack


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
