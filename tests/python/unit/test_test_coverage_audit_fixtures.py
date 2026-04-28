"""Contract-freeze test for test-coverage-audit (stage: deferred)."""

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
    / "test-coverage-audit"
    / "happy_path.yaml"
)


@pytest.mark.parametrize("case", load_fixture_cases(_FIXTURES), ids=lambda c: c["name"])
def test_test_coverage_audit_contract(case: dict) -> None:
    assert_contract_freeze(case)
