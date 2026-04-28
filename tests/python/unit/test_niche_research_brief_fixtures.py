"""Contract-freeze test for niche-research-brief.

Loads the fixture(s) at
``skills/canonical/niche-research-brief/fixtures/`` and asserts the
canonical body still carries the contract surface.
"""

from __future__ import annotations

import pytest

from tests.python.unit._skill_contract_freeze import (
    SKILLS_ROOT,
    assert_contract_freeze,
    load_fixture_cases,
)


_FIXTURES = SKILLS_ROOT / "canonical" / "niche-research-brief" / "fixtures" / "happy_path.yaml"


@pytest.mark.parametrize("case", load_fixture_cases(_FIXTURES), ids=lambda c: c["name"])
def test_niche_research_brief_contract(case: dict) -> None:
    assert_contract_freeze(case)
