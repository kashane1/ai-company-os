"""Shared helper for contract-freeze tests on agentic skills.

Agentic skills have no replay loader (the work is LLM-driven). Their
fixtures are structural assertions on the canonical body: required
input fields, output fields, section headings, helper dependencies,
forbidden-area declarations.

Each per-skill test file calls ``assert_contract_freeze(fixtures_path)``
and pytest reports per-fixture-case results.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


REPO_ROOT = Path(__file__).resolve().parents[3]
SKILLS_ROOT = REPO_ROOT / "skills"


def load_fixture_cases(fixtures_path: Path) -> list[dict]:
    """Load fixture YAML; return the list of cases."""
    with fixtures_path.open() as handle:
        cases = yaml.safe_load(handle)
    assert isinstance(cases, list), f"{fixtures_path}: expected list at top level"
    return cases


def read_skill_text(rel_path: str) -> str:
    """Read a skill markdown file relative to skills/."""
    return (SKILLS_ROOT / rel_path).read_text()


_GROUP_LABELS: dict[str, str] = {
    "required_input_fields": "input field",
    "required_output_fields": "output field",
    "required_section_headings": "section heading",
    "required_phase_headings": "phase heading",
    "required_forbidden_areas": "forbidden-area declaration",
    "required_allowed_edit_paths": "allowed-edit path",
    "required_helper_dependencies": "helper dependency",
    "required_hard_gate_references": "hard-gate reference",
    # Additional groups used by skills with stricter contract surfaces.
    # Without entries here the shared helper would silently no-op on them.
    "required_preconditions": "precondition",
    "required_checklist_items": "checklist item",
    "required_failure_modes": "failure mode",
    "required_handoff_channel": "handoff channel",
    "required_output_sections": "output section",
    "required_validation_steps": "validation step",
    "required_record_fields": "record field",
    "required_status_values": "status value",
    "required_severity_labels": "severity label",
    "required_verdict_values": "verdict value",
    "required_safety_clauses": "safety clause",
    "required_pack_sections": "pack section",
    "required_lane_coverage_keys": "lane coverage key",
    "required_character_limits": "character limit",
    "required_modes": "mode",
    "required_decision_tiers": "decision tier",
    "required_strong_v1_capabilities": "strong-v1 capability",
    "required_vision_sections": "vision section",
    "required_stop_conditions": "stop condition",
    # Audit-skill family: introduced 2026-05-12 for the recon-sibling
    # split (premium-feel-audit, pro-value-audit). The tier vocabulary
    # is the per-sibling differentiator and must be locked verbatim;
    # the variety floors lock the minimum prompt-mode distribution
    # each audit emits. See docs/plans/2026-05-12-feat-premium-and-pro-
    # value-audit-skills-plan.md deepening §1.
    "required_tier_vocabulary": "tier-vocabulary entry",
    "required_variety_floors": "variety-floor entry",
}


def assert_contract_freeze(case: dict[str, Any]) -> None:
    """Run all assertion groups in a fixture case against the skill body.

    Any failure carries a contract-weakening message naming the missing
    string and which group it was supposed to satisfy.
    """
    skill_text = read_skill_text(case["input"]["skill_file"])
    expected = case["expected"]
    case_name = case["name"]

    for group, label in _GROUP_LABELS.items():
        if group not in expected:
            continue
        for required in expected[group]:
            assert required in skill_text, (
                f"{case_name}: required {label} {required!r} missing from "
                f"{case['input']['skill_file']}. This is a contract weakening — "
                "restore the string or document why the invariant changed."
            )
