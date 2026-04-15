"""Phase 1 structural contract test — documentation-lookup.

Parses each fixture under
skills/canonical/documentation-lookup/fixtures/ and asserts the shape
of the canonical skill.md + contract.yaml against the fixture's
expected clauses.
"""
from __future__ import annotations

from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[3]
SKILLS_ROOT = REPO_ROOT / "skills"
FIXTURES_DIR = (
    SKILLS_ROOT / "canonical" / "documentation-lookup" / "fixtures"
)


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


@pytest.mark.parametrize("case", _load_cases(), ids=_case_id)
def test_documentation_lookup_contract(case: dict) -> None:
    expected = case["expected"]
    skill_text = _read(case["input"]["skill_file"])

    contract: dict = {}
    if "contract_file" in case["input"]:
        contract = yaml.safe_load(_read(case["input"]["contract_file"])) or {}

    for required in expected.get("required_strings_in_skill", []):
        assert required in skill_text, (
            f"{case['name']}: required string {required!r} missing from "
            f"{case['input']['skill_file']}"
        )

    for section in expected.get("required_sections", []):
        assert section in skill_text, (
            f"{case['name']}: required section {section!r} missing"
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

    if "required_contract_input_validations" in expected:
        inputs_by_name = {
            inp["name"]: inp for inp in contract.get("inputs", [])
        }
        for name, regex in expected[
            "required_contract_input_validations"
        ].items():
            assert name in inputs_by_name, (
                f"{case['name']}: input {name!r} missing from contract"
            )
            assert inputs_by_name[name].get("validation") == regex, (
                f"{case['name']}: input {name!r} validation must be "
                f"{regex!r}; got {inputs_by_name[name].get('validation')!r}"
            )
