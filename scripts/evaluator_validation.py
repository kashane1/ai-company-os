"""Validate the samples and local links used by the employer walkthrough."""

from __future__ import annotations

import json
import os
import re
import sys
from collections.abc import Callable, Iterable
from html import unescape
from pathlib import Path
from typing import TYPE_CHECKING
from urllib.parse import unquote, urlsplit

_MARKDOWN_LINK_RE = re.compile(r"!?\[[^]]*\]\((<[^>]+>|(?:[^()]|\([^)]*\))*)\)")

if TYPE_CHECKING:
    from packages.schemas.task_run import TaskRun


def _without_fences(text: str) -> str:
    lines = []
    fence = ""
    for line in text.splitlines():
        match = re.match(r"^\s{0,3}(`{3,}|~{3,})", line)
        if match:
            marker = match.group(1)
            if not fence:
                fence = marker
            elif marker[0] == fence[0] and len(marker) >= len(fence):
                fence = ""
            continue
        if not fence:
            lines.append(line)
    return "\n".join(lines)


def _link_destination(raw: str) -> str:
    raw = raw.strip()
    if raw.startswith("<"):
        return raw[1:raw.index(">")]
    return raw.split(maxsplit=1)[0] if raw else ""


def _markdown_targets(text: str) -> list[str]:
    text = _without_fences(text)
    definitions = {
        " ".join(label.lower().split()): _link_destination(target)
        for label, target in re.findall(r"^\s{0,3}\[([^]]+)\]:\s*(.+)$", text, re.MULTILINE)
    }
    targets = [_link_destination(match.group(1)) for match in _MARKDOWN_LINK_RE.finditer(text)]
    # Explicit and collapsed reference links, including images.
    for label, reference in re.findall(r"!?\[([^]]+)\]\[([^]]*)\]", text):
        key = " ".join((reference or label).lower().split())
        if key in definitions:
            targets.append(definitions[key])
    # Shortcut references are links only when their definition exists.
    for label in re.findall(r"(?<![\][])\[([^]\n]+)\](?![(:\[])", text):
        key = " ".join(label.lower().split())
        if key in definitions:
            targets.append(definitions[key])
    targets.extend(re.findall(r'<(?:img|a)\b[^>]*\b(?:src|href)=["\']([^"\']+)["\']', text))
    return targets


def _heading_anchors(page: Path) -> set[str]:
    text = _without_fences(page.read_text())
    anchors: set[str] = set()
    for line in text.splitlines():
        match = re.match(r"^\s{0,3}#{1,6}\s+(.+?)\s*#*\s*$", line)
        if not match:
            continue
        heading = unescape(re.sub(r"<[^>]*>", "", match.group(1)))
        heading = re.sub(r"!?\[([^]]+)\]\([^)]*\)", r"\1", heading)
        slug = re.sub(r"[^\w\-\s]", "", heading.lower()).replace(" ", "-")
        anchor = slug
        suffix = 0
        while anchor in anchors:
            suffix += 1
            anchor = f"{slug}-{suffix}"
        anchors.add(anchor)
    anchors.update(re.findall(r'<[^>]+\b(?:id|name)=["\']([^"\']+)["\']', text))
    return anchors


def validate_sample_artifacts(root: Path) -> list[str]:
    """Deserialize every checked-in sample and require a lossless round trip."""
    from packages.schemas.approval import ApprovalRecord
    from packages.schemas.postmortem import PostMortem
    from packages.schemas.task_run import TaskRun

    checks: dict[str, Callable[[dict[str, object]], object]] = {
        "sample-task-run.json": TaskRun.from_dict,
        "sample-approval.json": ApprovalRecord.from_dict,
        "sample-postmortem.json": PostMortem.from_dict,
    }
    examples = root / "docs" / "examples"
    passed: list[str] = []
    for name, deserialize in checks.items():
        path = examples / name
        try:
            payload = json.loads(path.read_text())
            if not isinstance(payload, dict):
                raise TypeError("top-level JSON value must be an object")
            restored = deserialize(payload)
            if restored.to_dict() != payload:  # type: ignore[attr-defined]
                raise ValueError("schema round trip changed the artifact")
            if isinstance(restored, TaskRun):
                validate_task_run_semantics(restored)
        except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
            raise ValueError(f"{name} does not match its schema: {exc}") from exc
        passed.append(f"docs/examples/{name}")
    return passed


def validate_task_run_semantics(task_run: "TaskRun") -> None:
    """Require the checked-in iOS fixture to contain the evidence it claims.

    This deliberately validates fixture relationships without importing worker
    policy modules, so `scripts/evaluator_validation.py` remains runnable with
    the repository's standard Python dependencies only.
    """
    from packages.schemas.task_packet import WorkerLane
    from packages.schemas.testing import TestLane

    changed_files = task_run.post_run_git_state.changed_files
    source_roots = {
        path.split("/Sources/", maxsplit=1)[0]
        for path in changed_files
        if "/Sources/" in path
    }
    if not source_roots:
        return

    if task_run.worker_lane is not WorkerLane.IOS:
        raise ValueError("iOS source change must use the iOS worker lane")
    if task_run.testing_policy is None:
        raise ValueError("iOS source change is missing testing-policy evidence")
    if task_run.testing_policy.test_lane is not TestLane.IOS:
        raise ValueError("iOS source change must declare the iOS test lane")
    if not task_run.testing_policy.tests_required:
        raise ValueError("iOS source change must require lane-matching tests")
    has_matching_test = any(
        path.startswith(f"{source_root}/Tests/")
        or path.startswith(f"{source_root}/UITests/")
        for source_root in source_roots
        for path in changed_files
    )
    if not has_matching_test or not task_run.testing_policy.relevant_tests_changed:
        raise ValueError("iOS source change is missing a lane-matching iOS test")


def validate_markdown_links(root: Path, pages: Iterable[Path]) -> list[str]:
    """Ensure local Markdown links in evaluator pages still resolve in the repo."""
    checked: list[str] = []
    for page in pages:
        for target in _markdown_targets(page.read_text()):
            parsed = urlsplit(target)
            if parsed.scheme or parsed.netloc:
                continue
            target_path = unquote(parsed.path)
            # Resolve ``..`` lexically without following a repository's local
            # symlinks; evaluator fixtures may intentionally use symlinked
            # source trees.
            resolved = Path(os.path.abspath(page.parent / target_path)) if target_path else page
            try:
                resolved.relative_to(Path(os.path.abspath(root)))
            except ValueError as exc:
                raise ValueError(f"{page.relative_to(root)} links outside the repo: {target}") from exc
            if not resolved.exists():
                raise ValueError(f"{page.relative_to(root)} has a missing local link: {target}")
            if parsed.fragment and resolved.suffix.lower() == ".md":
                if unquote(parsed.fragment) not in _heading_anchors(resolved):
                    raise ValueError(f"{page.relative_to(root)} has a missing heading anchor: {target}")
            checked.append(f"{page.relative_to(root)} -> {target}")
    return checked


def validate_employer_materials(root: Path) -> tuple[list[str], list[str]]:
    pages = [
        root / "README.md",
        root / "CONTRIBUTING.md",
        root / "REPO_MAP.md",
        root / "docs" / "README.md",
        root / "docs" / "FOR-EMPLOYERS.md",
        root / "docs" / "EVALUATOR-WALKTHROUGH.md",
        root / "docs" / "examples" / "README.md",
        root / "docs" / "flagship-simulator-driven-polish.md",
        root / "docs" / "reliability-lessons.md",
        root / "docs" / "recurring-approval-sweep.md",
        root / "products" / "life-clock-ios" / "README.md",
        root / "products" / "catchbook-ios" / "README.md",
        root / "products" / "after-plans-ios" / "README.md",
        root / "apps" / "runtime-supervisor" / "README.md",
        root / "docs" / "architecture.md",
        root / "docs" / "agent-model.md",
        root / "docs" / "products" / "after-plans" / "PHASE_STATUS.md",
        root / "docs" / "products" / "life-clock" / "PHASE_STATUS.md",
        root / "docs" / "products" / "catchbook" / "submission-checklist.md",
    ]
    return validate_sample_artifacts(root), validate_markdown_links(root, pages)


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        raise SystemExit("usage: evaluator_validation.py <repository-root>")
    root = Path(argv[1]).resolve()
    sys.path.insert(0, str(root))
    samples, links = validate_employer_materials(root)
    for sample in samples:
        print(f"  ok  {sample} (schema round trip)")
    print(f"  ok  {len(links)} local Markdown link(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
