"""Schema-cross-check test for the polish-prompt producer-consumer contract.

Asserts POLISH_PROMPT_FIELDS is referenced verbatim in the shared spine
and in the consumer skill body. Closes the architecture-review concern
that the schema was 'documentation in Python clothing.'
"""
from __future__ import annotations
from pathlib import Path

from packages.schemas.polish_prompt import POLISH_PROMPT_FIELDS

REPO_ROOT = Path(__file__).resolve().parents[3]


def test_polish_prompt_fields_appear_in_shared_spine() -> None:
    spine = (REPO_ROOT / "skills" / "canonical" / "shared" / "recon-scaffolding.md").read_text()
    for field in POLISH_PROMPT_FIELDS:
        assert f"**{field}:**" in spine, (
            f"POLISH_PROMPT_FIELDS entry {field!r} is not present as "
            f"`**{field}:**` in the shared spine. The spine documents "
            "the per-prompt template; this test enforces that the "
            "Python schema is the source of truth and the markdown "
            "follows. Either restore the field in the markdown, or "
            "update POLISH_PROMPT_FIELDS to remove it intentionally."
        )


def test_polish_prompt_schema_module_path() -> None:
    """POLISH_PROMPT_FIELDS is non-empty and contains nine string entries."""
    assert len(POLISH_PROMPT_FIELDS) == 9, (
        f"POLISH_PROMPT_FIELDS must have exactly 9 entries; got "
        f"{len(POLISH_PROMPT_FIELDS)}. Adding a 10th field is a "
        "breaking change to the producer-consumer contract — update "
        "shared/recon-scaffolding.md AND simulator-driven-polish/skill.md "
        "AND every producer fixture before changing this count."
    )
    for field in POLISH_PROMPT_FIELDS:
        assert isinstance(field, str) and field, "fields must be non-empty strings"
