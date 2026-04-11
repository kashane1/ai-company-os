"""Phase 2.5 — fixture-backed tests for social-post-safety validator skill."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest
import yaml

REPO = Path(__file__).resolve().parents[3]
SKILL_DIR = REPO / "skills" / "canonical" / "social-post-safety"


def _load_validator():
    spec = importlib.util.spec_from_file_location(
        "social_post_safety_validator", SKILL_DIR / "validator.py"
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.run


def _load_fixture(name: str) -> dict:
    return yaml.safe_load((SKILL_DIR / "fixtures" / name).read_text())


@pytest.mark.parametrize(
    "fixture_name",
    ["happy_path.yaml", "boundary.yaml", "adversarial.yaml"],
)
def test_social_post_safety_fixtures(fixture_name):
    run = _load_validator()
    fixture = _load_fixture(fixture_name)
    result = run(fixture["input"])
    exp = fixture["expected"]
    assert result["verdict"] == exp["verdict"], result
    if "reasons" in exp:
        assert result["reasons"] == exp["reasons"]
    if "reasons_contains" in exp:
        for marker in exp["reasons_contains"]:
            assert any(marker in r for r in result["reasons"]), (marker, result)
