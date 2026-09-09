"""Validate the samples and local links used by the employer walkthrough."""

from __future__ import annotations

import json
import os
import re
import sys
from collections.abc import Callable, Iterable
from pathlib import Path
from urllib.parse import unquote, urlsplit


_MARKDOWN_LINK_RE = re.compile(r"(?<!!)\[[^]]*\]\(([^)]+)\)")


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
        except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
            raise ValueError(f"{name} does not match its schema: {exc}") from exc
        passed.append(f"docs/examples/{name}")
    return passed


def validate_markdown_links(root: Path, pages: Iterable[Path]) -> list[str]:
    """Ensure local Markdown links in evaluator pages still resolve in the repo."""
    checked: list[str] = []
    for page in pages:
        for match in _MARKDOWN_LINK_RE.finditer(page.read_text()):
            target = match.group(1).strip().strip("<>")
            parsed = urlsplit(target)
            if parsed.scheme or parsed.netloc or target.startswith("#"):
                continue
            target_path = unquote(parsed.path)
            if not target_path:
                continue
            # Resolve ``..`` lexically without following a repository's local
            # symlinks; evaluator fixtures may intentionally use symlinked
            # source trees.
            resolved = Path(os.path.abspath(page.parent / target_path))
            try:
                resolved.relative_to(Path(os.path.abspath(root)))
            except ValueError as exc:
                raise ValueError(f"{page.relative_to(root)} links outside the repo: {target}") from exc
            if not resolved.exists():
                raise ValueError(f"{page.relative_to(root)} has a missing local link: {target}")
            checked.append(f"{page.relative_to(root)} -> {target}")
    return checked


def validate_employer_materials(root: Path) -> tuple[list[str], list[str]]:
    pages = [
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
