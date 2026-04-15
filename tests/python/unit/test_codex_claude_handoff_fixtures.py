"""Phase 1 PR-1d — structural contract test for codex-claude-handoff.

The skill is currently `stage: deferred` per its own top comment —
the full enqueue → supervisor → worktree → apply loop is paused in
favor of a paste-based flow with a solo operator. But the skill's
CONSTRAINT CONTRACT (the list of strings every task packet must
carry) is a load-bearing boundary invariant that we want frozen even
while the skill itself is paused.

This test reads the skill file and asserts the contract strings are
present. Any future edit that weakens the constraints (drops a
string, removes a phase heading, strips an entry from forbidden_areas)
fails CI so the contract is a reviewable change, not a silent drift.
"""
from __future__ import annotations

from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[3]
SKILLS_ROOT = REPO_ROOT / "skills"
FIXTURES_PATH = (
    SKILLS_ROOT
    / "canonical"
    / "handoffs"
    / "codex-claude-handoff.fixtures.yaml"
)


def _load_cases() -> list[dict]:
    with FIXTURES_PATH.open() as f:
        raw = yaml.safe_load(f)
    assert isinstance(raw, list)
    return raw


def _case_id(case: dict) -> str:
    return case["name"]


def _read_skill_file(rel: str) -> str:
    return (SKILLS_ROOT / rel).read_text()


@pytest.mark.parametrize("case", _load_cases(), ids=_case_id)
def test_codex_claude_handoff_contract(case: dict) -> None:
    skill_text = _read_skill_file(case["input"]["skill_file"])
    expected = case["expected"]

    if "constraint_strings" in expected:
        # The required strings must appear inside the "Constraints every
        # packet must include" subsection.
        section_start = skill_text.find("Constraints every packet must include")
        assert section_start != -1, (
            "Skill file is missing the "
            "'Constraints every packet must include' section entirely"
        )
        # Slice from the section header to the next section divider.
        section_body = skill_text[section_start:]
        next_section = section_body.find("\n**", 10)
        if next_section == -1:
            next_section = section_body.find("\n###", 10)
        section_body = section_body[: next_section if next_section != -1 else None]

        for required in expected["constraint_strings"]:
            assert required in section_body, (
                f"{case['name']}: required constraint string "
                f"{required!r} missing from the Constraints section. "
                "This is a contract weakening — restore the string or "
                "file a PR explaining why the invariant changed."
            )

    if "phase_headings_contains" in expected:
        for heading in expected["phase_headings_contains"]:
            assert heading in skill_text, (
                f"{case['name']}: phase heading {heading!r} missing — "
                "the operating protocol must enumerate all five phases."
            )

    if "forbidden_areas_must_include" in expected:
        # Parse the YAML frontmatter and check forbidden_areas.
        # Frontmatter lives between the first two '---' markers.
        if not skill_text.startswith("---"):
            # Flat skills may have a leading comment block — strip it.
            fm_start = skill_text.find("---")
            assert fm_start != -1
        else:
            fm_start = 0
        body_after_first = skill_text[fm_start + 3 :]
        fm_end = body_after_first.find("---")
        assert fm_end != -1, "Skill file missing closing '---' on frontmatter"
        frontmatter = yaml.safe_load(body_after_first[:fm_end])
        forbidden = set(frontmatter.get("forbidden_areas", []))
        for required_forbidden in expected["forbidden_areas_must_include"]:
            assert required_forbidden in forbidden, (
                f"{case['name']}: forbidden_areas must contain "
                f"{required_forbidden!r}; got {forbidden}. "
                "Removing a protected directory from forbidden_areas is a "
                "security regression."
            )
