"""Anti-drift batch 3 structural contract test — codex-cloud-dispatch.

Data-driven from the skill's own fixtures. Mirrors the batch 2.1
anti-drift skill tests (`test_agent_preflight_skill.py`, etc.).

Also asserts the chain pieces that the wider reconciliation tests
expect a registered skill to ship: canonical, contract, adapter,
project-skill pointer, registry entry with `fixture_status: passing`.
"""
from __future__ import annotations

from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[3]
SKILLS_ROOT = REPO_ROOT / "skills"
FIXTURES_DIR = SKILLS_ROOT / "canonical" / "codex-cloud-dispatch" / "fixtures"


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
def test_codex_cloud_dispatch_contract(case: dict) -> None:
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


def test_codex_cloud_dispatch_chain_pieces_exist() -> None:
    """Canonical, contract, fixture, adapter, project-skill pointer all on disk."""
    canonical_dir = SKILLS_ROOT / "canonical" / "codex-cloud-dispatch"
    assert (canonical_dir / "skill.md").is_file()
    assert (canonical_dir / "contract.yaml").is_file()
    assert (canonical_dir / "fixtures" / "happy_path.yaml").is_file()

    adapter = SKILLS_ROOT / "adapters" / "claude" / "codex-cloud-dispatch.md"
    assert adapter.is_file(), f"missing adapter: {adapter}"

    pointer = REPO_ROOT / ".claude" / "skills" / "codex-cloud-dispatch.md"
    assert pointer.is_file(), f"missing project-skill pointer: {pointer}"


def test_codex_cloud_dispatch_registry_entry_is_passing() -> None:
    """Registry entry exists and is marked fixture_status: passing."""
    registry_path = SKILLS_ROOT / "registry.yaml"
    data = yaml.safe_load(registry_path.read_text())
    entries = {s["id"]: s for s in data["skills"]}
    assert "codex-cloud-dispatch" in entries, (
        "codex-cloud-dispatch missing from skills/registry.yaml"
    )
    entry = entries["codex-cloud-dispatch"]
    assert entry["fixture_status"] == "passing", (
        f"expected fixture_status: passing, got {entry['fixture_status']!r}"
    )
    assert entry["kind"] == "agentic"
    assert entry["stage"] == "active"
    assert entry["adapters"]["claude"] == "adapters/claude/codex-cloud-dispatch.md"
    assert entry["project_skill"] == ".claude/skills/codex-cloud-dispatch.md"


def test_codex_cloud_dispatch_contract_invariants_listed() -> None:
    """The contract.yaml's invariant list names the staging/xfail-shim/no-merge rules."""
    contract_path = SKILLS_ROOT / "canonical" / "codex-cloud-dispatch" / "contract.yaml"
    contract = yaml.safe_load(contract_path.read_text())
    invariants = contract.get("invariants", [])
    invariant_blob = " | ".join(invariants).lower()
    for needle in (
        "staging",
        "xfail shim",
        "one task per dispatch",
        "human review before merge",
        "no direct merges",
        "open the pr against the staging base branch",
        "stop if codex cloud ui",
    ):
        assert needle in invariant_blob, (
            f"contract invariants missing {needle!r}; got: {invariants}"
        )
