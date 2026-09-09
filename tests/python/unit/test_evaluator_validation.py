"""Regression coverage for employer-facing sample and link validation."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

import scripts.evaluator_validation as evaluator_validation
from scripts.evaluator_validation import validate_markdown_links, validate_sample_artifacts


REPO = Path(__file__).resolve().parents[3]


def test_sample_validation_rejects_schema_drift(tmp_path: Path) -> None:
    examples = tmp_path / "docs" / "examples"
    examples.parent.mkdir(parents=True)
    shutil.copytree(REPO / "docs" / "examples", examples)
    task_run = examples / "sample-task-run.json"
    payload = json.loads(task_run.read_text())
    payload["classification"] = "not-a-real-classification"
    task_run.write_text(json.dumps(payload))

    with pytest.raises(ValueError, match="sample-task-run.json"):
        validate_sample_artifacts(tmp_path)


def test_markdown_link_validation_rejects_missing_local_target(tmp_path: Path) -> None:
    page = tmp_path / "docs" / "FOR-EMPLOYERS.md"
    page.parent.mkdir(parents=True)
    page.write_text("[Broken walkthrough link](missing-walkthrough.md)\n")

    with pytest.raises(ValueError, match="missing-walkthrough.md"):
        validate_markdown_links(tmp_path, [page])


def test_employer_validation_includes_product_and_runtime_readmes(monkeypatch, tmp_path: Path) -> None:
    pages: list[Path] = []
    monkeypatch.setattr(evaluator_validation, "validate_sample_artifacts", lambda _root: [])
    monkeypatch.setattr(
        evaluator_validation,
        "validate_markdown_links",
        lambda _root, inputs: pages.extend(inputs) or [],
    )

    evaluator_validation.validate_employer_materials(tmp_path)

    assert {
        tmp_path / "products/life-clock-ios/README.md",
        tmp_path / "products/catchbook-ios/README.md",
        tmp_path / "products/after-plans-ios/README.md",
        tmp_path / "apps/runtime-supervisor/README.md",
    }.issubset(pages)
