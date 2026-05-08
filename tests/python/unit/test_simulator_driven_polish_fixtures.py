"""Contract-freeze test for simulator-driven-polish."""

from __future__ import annotations

import pytest

from packages.tools.skills.loader import load_registry
from tests.python.unit._skill_contract_freeze import (
    SKILLS_ROOT,
    assert_contract_freeze,
    load_fixture_cases,
)


_FIXTURES = (
    SKILLS_ROOT
    / "canonical"
    / "simulator-driven-polish"
    / "fixtures"
    / "happy_path.yaml"
)

_CODEX_ADAPTER = SKILLS_ROOT / "adapters" / "codex" / "simulator-driven-polish.md"


@pytest.mark.parametrize("case", load_fixture_cases(_FIXTURES), ids=lambda c: c["name"])
def test_simulator_driven_polish_contract(case: dict) -> None:
    assert_contract_freeze(case)


def test_simulator_driven_polish_registry_supports_codex() -> None:
    spec = next(
        skill for skill in load_registry() if skill.id == "simulator-driven-polish"
    )

    assert spec.fixture_status == "passing"
    assert spec.target_runtimes == ("claude", "codex")
    assert spec.adapters["claude"] == "adapters/claude/simulator-driven-polish.md"
    assert spec.adapters["codex"] == "adapters/codex/simulator-driven-polish.md"
    assert _CODEX_ADAPTER.exists()


def test_simulator_driven_polish_codex_adapter_pins_runtime_translation() -> None:
    adapter = _CODEX_ADAPTER.read_text()

    required_runtime_terms = [
        "xcodebuild",
        "xcrun simctl",
        "accessibility tree",
        "XCUIApplication().debugDescription",
        "xcrun simctl io <device> screenshot <path>",
        "products/<product-id>-ios/.polish/goldens/",
        "apply_patch",
        "numbered list",
        "one commit per logical fix",
        "accessibilityIdentifier",
        "Computer Use",
        "frontmost app/window",
        "session log",
        "assistant-memory",
        "## Decided constraints",
    ]

    for term in required_runtime_terms:
        assert term in adapter
