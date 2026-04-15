"""Phase 2b — context-budget validator tests.

Exercises `packages.tools.primitives.context_budget.run()` against
each fixture under `skills/canonical/context-budget/fixtures/`.
Each scenario materializes a synthetic skills root + registry;
verdict is always "pass" in v1, so tests assert shape (lane set,
top_largest presence, tokenizer path).
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import yaml

from packages.tools.primitives import context_budget

REPO_ROOT = Path(__file__).resolve().parents[3]
FIXTURES_DIR = (
    REPO_ROOT / "skills" / "canonical" / "context-budget" / "fixtures"
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


def _materialize_synthetic(
    tmp_path: Path, case_input: dict[str, Any]
) -> tuple[Path, Path]:
    skills_root = tmp_path / "skills"
    skills_root.mkdir()
    for entry in case_input.get("files") or []:
        relpath = entry["relpath"]
        content = entry.get("content", "")
        full = skills_root / relpath
        full.parent.mkdir(parents=True, exist_ok=True)
        full.write_text(content)

    registry_path = skills_root / "registry.yaml"
    registry_path.write_text(
        yaml.safe_dump(
            case_input.get("registry") or {"skills": []}, sort_keys=False
        )
    )
    (tmp_path / "CLAUDE.md").write_text("# empty\n")
    (tmp_path / ".claude" / "skills").mkdir(parents=True)
    return tmp_path, registry_path


@pytest.mark.parametrize("case", _load_cases(), ids=_case_id)
def test_context_budget_fixture(
    case: dict, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    expected = case["expected"]
    repo_root, registry_path = _materialize_synthetic(tmp_path, case["input"])

    monkeypatch.setattr(context_budget, "_repo_root", lambda: repo_root)
    monkeypatch.setattr(
        context_budget, "_skills_root", lambda: repo_root / "skills"
    )

    if case["input"].get("force_fallback_tokenizer"):
        # Clear the lru_cache, then stub _encoder() to return None so
        # count_tokens falls through to the char-count path.
        context_budget._encoder.cache_clear()
        monkeypatch.setattr(context_budget, "_encoder", lambda: None)

    result = context_budget.run({"registry_path": str(registry_path)})

    assert result["verdict"] == expected["verdict"]
    report = result["report"]

    if "tokenizer" in expected:
        assert report["tokenizer"] == expected["tokenizer"], (
            f"{case['name']}: tokenizer {report['tokenizer']!r} != "
            f"{expected['tokenizer']!r}"
        )

    if "lane_count" in expected:
        assert len(report["lanes"]) == expected["lane_count"], (
            f"{case['name']}: lanes {report['lanes']!r}"
        )

    if "lanes_contain" in expected:
        lane_names = {lb["lane"] for lb in report["lanes"]}
        for name in expected["lanes_contain"]:
            assert name in lane_names, (
                f"{case['name']}: lane {name!r} missing; have {lane_names}"
            )

    if "top_largest_min_count" in expected:
        assert len(report["top_largest"]) >= expected["top_largest_min_count"]

    if "notes_contain" in expected:
        assert any(
            expected["notes_contain"] in note for note in report["notes"]
        ), f"{case['name']}: notes {report['notes']!r}"
