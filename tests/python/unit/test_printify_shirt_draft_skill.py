"""Structural contract tests for the hybrid Printify shirt-draft skill."""
from __future__ import annotations

from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[3]
SKILLS_ROOT = REPO_ROOT / "skills"
SKILL_ID = "printify-shirt-draft"
FIXTURES_DIR = SKILLS_ROOT / "canonical" / SKILL_ID / "fixtures"


def _load_cases() -> list[dict]:
    cases: list[dict] = []
    for fixture_path in sorted(FIXTURES_DIR.glob("*.yaml")):
        raw = yaml.safe_load(fixture_path.read_text())
        assert isinstance(raw, list), f"{fixture_path.name} must be a list of cases"
        for case in raw:
            case["_fixture_file"] = fixture_path.name
            cases.append(case)
    return cases


def _case_id(case: dict) -> str:
    return f"{case['_fixture_file']}::{case['name']}"


@pytest.mark.parametrize("case", _load_cases(), ids=_case_id)
def test_printify_shirt_draft_contract(case: dict) -> None:
    expected = case["expected"]
    skill_text = (SKILLS_ROOT / case["input"]["skill_file"]).read_text()
    adapter_text = (SKILLS_ROOT / case["input"]["adapter_file"]).read_text()
    contract = yaml.safe_load(
        (SKILLS_ROOT / case["input"]["contract_file"]).read_text()
    ) or {}

    for required in expected.get("required_strings_in_skill", []):
        assert required in skill_text, (
            f"{case['name']}: skill must retain {required!r}"
        )

    for required in expected.get("required_strings_in_adapter", []):
        assert required in adapter_text, (
            f"{case['name']}: adapter must retain {required!r}"
        )

    for section in expected.get("required_sections", []):
        assert section in skill_text, f"{case['name']}: missing {section!r}"

    input_names = {item["name"] for item in contract.get("inputs", [])}
    output_names = {item["name"] for item in contract.get("outputs", [])}
    violation_codes = {item["code"] for item in contract.get("violations", [])}
    assert input_names.issuperset(expected.get("required_contract_inputs", []))
    assert output_names.issuperset(expected.get("required_contract_outputs", []))
    assert violation_codes.issuperset(expected.get("required_contract_violations", []))


def test_printify_shirt_draft_registry_wiring() -> None:
    registry = yaml.safe_load((SKILLS_ROOT / "registry.yaml").read_text())
    entries = {entry["id"]: entry for entry in registry["skills"]}
    assert entries[SKILL_ID] == {
        "id": SKILL_ID,
        "name": "Printify Shirt Draft",
        "path": "canonical/printify-shirt-draft/skill.md",
        "owner_agent": "engineering",
        "target_runtimes": ["codex"],
        "stage": "active",
        "kind": "agentic",
        "fixture_status": "passing",
        "source": "internal",
        "adapters": {"codex": "adapters/codex/printify-shirt-draft.md"},
    }
