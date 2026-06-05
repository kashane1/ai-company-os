"""Contract-freeze test for copy-review."""

from __future__ import annotations

import pytest

from tests.python.unit._skill_contract_freeze import (
    SKILLS_ROOT,
    assert_contract_freeze,
    load_fixture_cases,
)


_FIXTURES = SKILLS_ROOT / "canonical" / "copy-review" / "fixtures" / "happy_path.yaml"


@pytest.mark.parametrize("case", load_fixture_cases(_FIXTURES), ids=lambda c: c["name"])
def test_copy_review_contract(case: dict) -> None:
    assert_contract_freeze(case)
