"""Contract-freeze tests for pro-value-audit.

Locks the monetization-specific contract surface: observer (pro-value-
rule.md + MONETIZATION.md), tier vocabulary, variety floors, pro-value-
readiness criteria, trust-gap and pro-rule-violation escalation rules,
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
    / "pro-value-audit"
    / "fixtures"
    / "happy_path.yaml"
)


@pytest.mark.parametrize(
    "case", load_fixture_cases(_FIXTURES), ids=lambda c: c["name"]
)
def test_pro_value_audit_contract(case: dict) -> None:
    assert_contract_freeze(case)
