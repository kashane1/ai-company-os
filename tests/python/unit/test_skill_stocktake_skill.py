"""Phase 2a — skill-stocktake validator tests.

Exercises `packages.tools.primitives.registry_drift.run()` against
each fixture under `skills/canonical/skill-stocktake/fixtures/`.
Each fixture scenario materializes a synthetic skills tree (tmp_path)
that matches the fixture's `input.canonical_dirs` + `input.registry`
+ optional `input.claude_md`, runs the validator, and asserts the
expected verdict + drift types.

Unlike the LLM-verdict skills, this is a validator with a fully
deterministic surface, so the test REPLAYS the validator against
each fixture rather than freezing the canonical markdown shape. The
structural markdown check is separately covered by
`test_skill_reconciliation.py`.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import yaml

from packages.tools.primitives import registry_drift
from packages.tools.primitives.registry_drift import run

REPO_ROOT = Path(__file__).resolve().parents[3]
FIXTURES_DIR = (
    REPO_ROOT / "skills" / "canonical" / "skill-stocktake" / "fixtures"
)


def _load_cases() -> list[dict]:
    cases: list[dict] = []
    for fixture_path in sorted(FIXTURES_DIR.glob("*.yaml")):
        with fixture_path.open() as f:
            raw = yaml.safe_load(f)
        assert isinstance(raw, list), f"{fixture_path.name} must be a list"
        for case in raw:
            case["_fixture_file"] = fixture_path.name
            cases.append(case)
    return cases


def _case_id(case: dict) -> str:
    return f"{case['_fixture_file']}::{case['name']}"


def _materialize_synthetic_repo(
    tmp_path: Path, case_input: dict[str, Any]
) -> tuple[Path, Path]:
    """Build a synthetic repo root + registry file from the case input.

    Returns (synthetic_repo_root, registry_path). The caller
    monkeypatches `_repo_root` / `_skills_root` / `_claude_md_path`
    on the module under test so the validator sees this tmp tree.
    """
    skills_root = tmp_path / "skills"
    canonical = skills_root / "canonical"
    canonical.mkdir(parents=True)
    for skill_dir_name in case_input.get("canonical_dirs", []):
        d = canonical / skill_dir_name
        d.mkdir(parents=True)
        (d / "skill.md").write_text(f"# {skill_dir_name} stub\n")

    registry_path = skills_root / "registry.yaml"
    registry_data = case_input.get("registry") or {"skills": []}
    registry_path.write_text(yaml.safe_dump(registry_data, sort_keys=False))

    claude_md_text = case_input.get("claude_md")
    claude_md_path = tmp_path / "CLAUDE.md"
    if claude_md_text is not None:
        claude_md_path.write_text(claude_md_text)
    else:
        claude_md_path.write_text("# empty\n")

    return tmp_path, registry_path


@pytest.mark.parametrize("case", _load_cases(), ids=_case_id)
def test_skill_stocktake_fixture(
    case: dict, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    expected = case["expected"]
    repo_root, registry_path = _materialize_synthetic_repo(
        tmp_path, case["input"]
    )

    monkeypatch.setattr(registry_drift, "_repo_root", lambda: repo_root)
    monkeypatch.setattr(
        registry_drift, "_skills_root", lambda: repo_root / "skills"
    )
    monkeypatch.setattr(
        registry_drift, "_claude_md_path", lambda: repo_root / "CLAUDE.md"
    )

    result = run({"registry_path": str(registry_path)})

    assert result["verdict"] == expected["verdict"], (
        f"{case['name']}: verdict {result['verdict']!r}; expected "
        f"{expected['verdict']!r}. drift={result['report']['drift_items']}"
    )
    assert result["drift_count"] == expected["drift_count"], (
        f"{case['name']}: drift_count {result['drift_count']}; expected "
        f"{expected['drift_count']}"
    )
    if "drift_types" in expected:
        actual_types = sorted(
            item["drift_type"] for item in result["report"]["drift_items"]
        )
        assert actual_types == sorted(expected["drift_types"]), (
            f"{case['name']}: drift types {actual_types}; expected "
            f"{sorted(expected['drift_types'])}"
        )
