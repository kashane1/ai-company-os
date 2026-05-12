"""Contract-freeze tests for simulator-polish-recon.

Locks the recon-specific contract surface: depth ceilings, tier vocabulary,
variety floor numbers, submission-readiness criteria, and observer step order.

Closes the v1.1 follow-up flagged in commit b70b1a6 (2026-05-10).
See docs/plans/2026-05-12-feat-premium-and-pro-value-audit-skills-plan.md §8.
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
    / "simulator-polish-recon"
    / "fixtures"
    / "happy_path.yaml"
)


@pytest.mark.parametrize(
    "case", load_fixture_cases(_FIXTURES), ids=lambda c: c["name"]
)
def test_simulator_polish_recon_contract(case: dict) -> None:
    assert_contract_freeze(case)
