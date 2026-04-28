"""Contract-freeze test for app-store-positioning-pack."""

from __future__ import annotations

import pytest

from tests.python.unit._skill_contract_freeze import (
    SKILLS_ROOT,
    assert_contract_freeze,
    load_fixture_cases,
)


_FIXTURES = (
    SKILLS_ROOT
    / "canonical"
    / "shared"
    / "fixtures"
    / "app-store-positioning-pack"
    / "happy_path.yaml"
)


@pytest.mark.parametrize("case", load_fixture_cases(_FIXTURES), ids=lambda c: c["name"])
def test_app_store_positioning_pack_contract(case: dict) -> None:
    assert_contract_freeze(case)
