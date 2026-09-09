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

from packages.tools.skills.loader import load_validator

SKILL_DIR = (
    Path(__file__).parent.parent.parent.parent
    / "skills"
    / "canonical"
    / "post-run-validation"
)
FIXTURE_DIR = SKILL_DIR / "fixtures"


def _run_fixture(name: str, tmp_path: Path | None = None) -> tuple[dict, dict]:
    data = json.loads((FIXTURE_DIR / name).read_text())
    if tmp_path is not None:
        for artifact in data["input"]["result"].get("artifacts", []):
            path = tmp_path / artifact
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("fixture evidence", encoding="utf-8")
        data["input"]["repo_root"] = str(tmp_path)
    validator = load_validator("post-run-validation")
    return validator.run(data["input"]), data["expected"]


def test_happy_path_fixture(tmp_path: Path):
    result, expected = _run_fixture("happy_path.json", tmp_path)
    assert result["verdict"] == expected["verdict"]
    assert result["failure_code"] == expected["failure_code"]
    assert result["lane"] == expected["lane"]


def test_boundary_no_artifacts_fixture():
    result, expected = _run_fixture("boundary_no_artifacts.json")
    assert result["verdict"] == "fail"
    assert result["failure_code"] == expected["failure_code"]


def test_adversarial_forbidden_code_fixture(tmp_path: Path):
    result, expected = _run_fixture("adversarial_forbidden_code.json", tmp_path)
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


def test_required_event_missing(tmp_path: Path):
    validator = load_validator("post-run-validation")
    artifact = tmp_path / "state/artifacts/ios/t2/build_summary.json"
    artifact.parent.mkdir(parents=True)
    artifact.write_text("build evidence", encoding="utf-8")
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
            "repo_root": str(tmp_path),
        }
    )
    assert out["verdict"] == "fail"
    assert out["failure_code"] == "required_event_missing"


def test_listed_but_missing_artifact_is_rejected(tmp_path: Path):
    validator = load_validator("post-run-validation")
    out = validator.run(
        {
            "lane": "engineering",
            "task_type": "code_patch",
            "task_id": "t-missing",
            "result": {
                "task_id": "t-missing",
                "summary": "claimed evidence",
                "artifacts": ["state/artifacts/engineering/t-missing/review_summary.json"],
                "events": ["task_claimed"],
            },
            "repo_root": str(tmp_path),
        }
    )
    assert out["verdict"] == "fail"
    assert out["failure_code"] == "required_artifact_missing"


def test_skill_evolution_contract_requires_applied_evidence(tmp_path: Path):
    validator = load_validator("post-run-validation")
    artifact = (
        tmp_path
        / "state"
        / "artifacts"
        / "skill-evolution"
        / "task-skill-1-abc123"
        / "applied.flag"
    )
    artifact.parent.mkdir(parents=True)
    artifact.write_text("{}", encoding="utf-8")

    out = validator.run(
        {
            "lane": "skill_evolution",
            "task_type": "skill_evolution",
            "task_id": "task-skill-1",
            "result": {
                "task_id": "task-skill-1",
                "summary": "approved proposal",
                "artifacts": [str(artifact)],
                "events": ["task_claimed"],
            },
            "repo_root": str(tmp_path),
        }
    )

    assert out["verdict"] == "ok"


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
