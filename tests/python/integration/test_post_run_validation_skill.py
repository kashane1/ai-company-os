"""Phase 4.5 — post-run-validation validator skill tests.

These tests exercise the validator directly via its fixture files, plus
a few hand-rolled cases covering every failure code. They deliberately
do NOT import the ControlPlaneService (whose wiring is covered by a
separate control-plane integration test) so the validator can be
verified in pure Python.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from packages.tools.skills.loader import load_validator


SKILL_DIR = (
    Path(__file__).parent.parent.parent.parent
    / "skills"
    / "canonical"
    / "post-run-validation"
)
FIXTURE_DIR = SKILL_DIR / "fixtures"


def _run_fixture(name: str) -> tuple[dict, dict]:
    data = json.loads((FIXTURE_DIR / name).read_text())
    validator = load_validator("post-run-validation")
    return validator.run(data["input"]), data["expected"]


def test_happy_path_fixture():
    result, expected = _run_fixture("happy_path.json")
    assert result["verdict"] == expected["verdict"]
    assert result["failure_code"] == expected["failure_code"]
    assert result["lane"] == expected["lane"]


def test_boundary_no_artifacts_fixture():
    result, expected = _run_fixture("boundary_no_artifacts.json")
    assert result["verdict"] == "fail"
    assert result["failure_code"] == expected["failure_code"]


def test_adversarial_forbidden_code_fixture():
    result, expected = _run_fixture("adversarial_forbidden_code.json")
    assert result["verdict"] == "fail"
    assert result["failure_code"] == expected["failure_code"]


def test_unknown_lane_is_rejected():
    validator = load_validator("post-run-validation")
    out = validator.run(
        {
            "lane": "marketing",
            "task_type": "x",
            "task_id": "t1",
            "result": {"summary": "ok", "artifacts": [], "events": []},
            "repo_root": ".",
        }
    )
    assert out["verdict"] == "fail"
    assert out["failure_code"] == "lane_unknown"


def test_required_event_missing():
    validator = load_validator("post-run-validation")
    out = validator.run(
        {
            "lane": "ios",
            "task_type": "ios_build",
            "task_id": "t2",
            "result": {
                "task_id": "t2",
                "summary": "built",
                "artifacts": ["state/artifacts/ios/t2/build_summary.json"],
                "events": [],
            },
            "repo_root": ".",
        }
    )
    assert out["verdict"] == "fail"
    assert out["failure_code"] == "required_event_missing"


def test_fail_closed_on_exception_is_structured():
    validator = load_validator("post-run-validation")
    # Pass an int as result to trigger AttributeError inside run().
    out = validator.run(
        {
            "lane": "engineering",
            "task_type": "code",
            "task_id": "t3",
            "result": 42,
            "repo_root": ".",
        }
    )
    assert out["verdict"] == "fail"
    assert out["failure_code"].startswith("exception:") or out["failure_code"] in {
        "required_artifact_missing",
    }
