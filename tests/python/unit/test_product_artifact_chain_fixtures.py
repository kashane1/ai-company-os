"""Phase 1 PR-1c — fixture replay for product-artifact-chain.

Loads the sibling fixture file at
`skills/canonical/shared/product-artifact-chain.fixtures.yaml`, builds
a synthetic product directory from each case's `input.files` map, and
runs `packages.tools.product_artifacts.validator.validate_chain`
against it. Asserts the shape of the returned ChainReport matches
`expected`.

The skill is `kind: agentic` in the registry — an LLM-assisted
decomposition of founder-to-App-Store artifact state — but the
underlying chain validation is deterministic Python, so the Phase 1
fixtures exercise that deterministic layer directly.
"""
from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from packages.tools.product_artifacts.validator import validate_chain

REPO_ROOT = Path(__file__).resolve().parents[3]
FIXTURES_PATH = (
    REPO_ROOT
    / "skills"
    / "canonical"
    / "shared"
    / "product-artifact-chain.fixtures.yaml"
)


def _load_cases() -> list[dict]:
    with FIXTURES_PATH.open() as f:
        raw = yaml.safe_load(f)
    assert isinstance(raw, list)
    return raw


def _case_id(case: dict) -> str:
    return case["name"]


@pytest.mark.parametrize("case", _load_cases(), ids=_case_id)
def test_chain_validation_matches_fixture(case: dict, tmp_path: Path) -> None:
    product_dir = tmp_path / case["input"]["product_id"]
    product_dir.mkdir()
    for filename, content in case["input"]["files"].items():
        (product_dir / filename).write_text(content)

    report = validate_chain(
        product_id=case["input"]["product_id"],
        product_dir=product_dir,
        phase=case["input"]["phase"],
    )

    expected = case["expected"]

    if "is_ok" in expected:
        assert report.ok is expected["is_ok"], (
            f"{case['name']}: expected ok={expected['is_ok']}, "
            f"got {report.ok} (violations: {report.violations})"
        )

    for required_node in expected.get("present_nodes_contains", []):
        assert required_node in report.present_nodes, (
            f"{case['name']}: expected {required_node!r} in present_nodes, "
            f"got {report.present_nodes}"
        )

    expected_missing = expected.get("missing_nodes")
    if expected_missing is not None:
        assert list(report.missing_nodes) == expected_missing, (
            f"{case['name']}: expected missing_nodes={expected_missing}, "
            f"got {list(report.missing_nodes)}"
        )

    if "violation_count" in expected:
        assert len(report.violations) == expected["violation_count"], (
            f"{case['name']}: expected {expected['violation_count']} "
            f"violations, got {len(report.violations)}: {report.violations}"
        )

    if "violation_count_at_least" in expected:
        assert len(report.violations) >= expected["violation_count_at_least"], (
            f"{case['name']}: expected at least "
            f"{expected['violation_count_at_least']} violations, got "
            f"{len(report.violations)}"
        )

    if "has_violation_code" in expected:
        codes = {v.code for v in report.violations}
        assert expected["has_violation_code"] in codes, (
            f"{case['name']}: expected violation code "
            f"{expected['has_violation_code']!r}, got {codes}"
        )
