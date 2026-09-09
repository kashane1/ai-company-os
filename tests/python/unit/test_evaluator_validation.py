"""Regression coverage for employer-facing sample and link validation."""

from __future__ import annotations

import json
import shutil
from dataclasses import replace
from pathlib import Path

import pytest

import scripts.evaluator_validation as evaluator_validation
from packages.schemas.task_run import GitStateSnapshot
from scripts.demo.run_demo import build_demo_run
from scripts.evaluator_validation import (
    validate_markdown_links,
    validate_sample_artifacts,
    validate_task_run_semantics,
)

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


def test_task_run_semantics_reject_ios_source_change_without_matching_test() -> None:
    task_run = build_demo_run(succeeded=True).task_run
    assert task_run.testing_policy is not None
    assert "products/catchbook-ios/Tests/LogEntryTests.swift" in task_run.post_run_git_state.changed_files

    source_only = replace(
        task_run,
        post_run_git_state=GitStateSnapshot(
            status_lines=["M\tproducts/catchbook-ios/Sources/LogEntry.swift"],
            changed_files=["products/catchbook-ios/Sources/LogEntry.swift"],
            diff_summary="1 file changed, 12 insertions(+), 3 deletions(-)",
        ),
    )

    with pytest.raises(ValueError, match="lane-matching iOS test"):
        validate_task_run_semantics(source_only)


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


@pytest.mark.parametrize("content", [
    "![Missing evidence](missing.png)",
    "[Section](#missing-section)",
    "[Elsewhere](other.md#missing-section)",
    "[Evidence][capture]\n\n[capture]: missing.webp",
    '<img src="missing.png" alt="evidence">',
])
def test_link_validation_catches_images_fragments_and_references(tmp_path, content):
    page = tmp_path / "README.md"
    page.write_text(content)
    (tmp_path / "other.md").write_text("# Existing section")
    with pytest.raises(ValueError):
        validate_markdown_links(tmp_path, [page])


def test_heading_links_support_duplicates_unicode_and_inline_markup(tmp_path):
    page = tmp_path / "README.md"
    page.write_text("""# Review `this` & café
## Repeated
## Repeated
[first](#review-this--café)
[second](#repeated-1)
![proof][image]
[image]: <proof image.webp> "A screenshot"
```markdown
[example](not-a-real-file.md)
```
""")
    (tmp_path / "proof image.webp").touch()
    assert len(validate_markdown_links(tmp_path, [page])) == 3
