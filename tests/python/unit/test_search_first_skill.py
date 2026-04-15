"""Phase 1 structural contract test — search-first.

Parses each fixture under skills/canonical/search-first/fixtures/ and
asserts the shape of the canonical skill.md + contract.yaml against
the fixture's expected clauses. This freezes the CONTRACT, not any
particular LLM verdict.

Template: skills/canonical/handoffs/codex-claude-handoff.fixtures.yaml
and tests/python/unit/test_codex_claude_handoff_fixtures.py.
"""
from __future__ import annotations

from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[3]
SKILLS_ROOT = REPO_ROOT / "skills"
FIXTURES_DIR = SKILLS_ROOT / "canonical" / "search-first" / "fixtures"


def _load_cases() -> list[dict]:
    cases: list[dict] = []
    for fixture_path in sorted(FIXTURES_DIR.glob("*.yaml")):
        with fixture_path.open() as f:
            raw = yaml.safe_load(f)
        assert isinstance(raw, list), f"{fixture_path.name} must be a list of cases"
        for case in raw:
            case["_fixture_file"] = fixture_path.name
            cases.append(case)
    return cases


def _case_id(case: dict) -> str:
    return f"{case['_fixture_file']}::{case['name']}"


def _read(rel: str) -> str:
    return (SKILLS_ROOT / rel).read_text()


def _parse_frontmatter(text: str) -> dict:
    if not text.startswith("---"):
        return {}
    end = text.find("---", 3)
    if end == -1:
        return {}
    return yaml.safe_load(text[3:end]) or {}


@pytest.mark.parametrize("case", _load_cases(), ids=_case_id)
def test_search_first_contract(case: dict) -> None:
    expected = case["expected"]
    skill_text = _read(case["input"]["skill_file"])

    contract: dict = {}
    if "contract_file" in case["input"]:
        contract = yaml.safe_load(_read(case["input"]["contract_file"])) or {}

    for required in expected.get("required_strings_in_skill", []):
        assert required in skill_text, (
            f"{case['name']}: required string {required!r} missing from "
            f"{case['input']['skill_file']}. This is a contract "
            "weakening — restore the string or file a PR explaining why."
        )

    for section in expected.get("required_sections", []):
        assert section in skill_text, (
            f"{case['name']}: required section {section!r} missing from "
            f"{case['input']['skill_file']}."
        )

    for step in expected.get("required_procedure_steps_contain", []):
        assert step in skill_text, (
            f"{case['name']}: procedure step {step!r} missing from "
            f"{case['input']['skill_file']}."
        )

    if "required_contract_inputs" in expected:
        input_names = {inp["name"] for inp in contract.get("inputs", [])}
        for name in expected["required_contract_inputs"]:
            assert name in input_names, (
                f"{case['name']}: contract input {name!r} missing; "
                f"have {sorted(input_names)}"
            )

    if "required_contract_outputs" in expected:
        output_names = {out["name"] for out in contract.get("outputs", [])}
        for name in expected["required_contract_outputs"]:
            assert name in output_names, (
                f"{case['name']}: contract output {name!r} missing; "
                f"have {sorted(output_names)}"
            )

    if "required_contract_violations" in expected:
        violation_codes = {v["code"] for v in contract.get("violations", [])}
        for code in expected["required_contract_violations"]:
            assert code in violation_codes, (
                f"{case['name']}: contract must declare violation {code!r}; "
                f"have {sorted(violation_codes)}"
            )
