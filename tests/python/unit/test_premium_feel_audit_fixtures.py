"""Contract-freeze tests for premium-feel-audit.

Locks the elevation-specific contract surface: observer rubric (premium-
bar.md), tier vocabulary, variety floors, premium-readiness criteria,
and the shared-spine dependency.
"""

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
    / "premium-feel-audit"
    / "fixtures"
    / "happy_path.yaml"
)


@pytest.mark.parametrize(
    "case", load_fixture_cases(_FIXTURES), ids=lambda c: c["name"]
)
def test_premium_feel_audit_contract(case: dict) -> None:
    assert_contract_freeze(case)
