#!/usr/bin/env python3
"""Move finished plans out of docs/plans/ into docs/plans/archive/.

Token-efficiency tooling + the "real-time archival" mechanism: the moment a
plan's frontmatter `status:` becomes a finished state, it should leave the
working set so agents globbing docs/plans/ see only live plans.

A plan is "finished" when its frontmatter status is one of:
    completed, complete, done, shipped, superseded, archived, abandoned

Modes:
    python3 scripts/docs/archive_plans.py            # move finished plans now
    python3 scripts/docs/archive_plans.py --dry-run  # show what would move
    python3 scripts/docs/archive_plans.py --check     # exit 1 if any finished
                                                       # plan is still in the
                                                       # working set (CI gate)

How "real-time" is enforced (three layers, defence in depth):
  1. Claude Code hook (.claude/settings.json) runs this script after any
     Write/Edit under docs/plans/ — so flipping a status archives immediately.
  2. The --check mode runs in CI (.github/workflows/token-efficiency.yml), so a
     finished-but-unarchived plan cannot merge even from a non-Claude runtime.
  3. The plan skill documents the convention for humans/agents.
"""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from gen_doc_index import render  # noqa: E402

PLANS_DIR = Path("docs/plans")
ARCHIVE_DIR = PLANS_DIR / "archive"
FINISHED = {
    "completed",
    "complete",
    "done",
    "shipped",
    "superseded",
    "archived",
    "abandoned",
}


def plan_status(path: Path) -> str | None:
    text = path.read_text(encoding="utf-8", errors="replace")
    if not text.startswith("---"):
        return None
    end = text.find("\n---", 3)
    if end == -1:
        return None
    for line in text[3:end].splitlines():
        stripped = line.strip()
        if stripped.lower().startswith("status:"):
            return stripped.split(":", 1)[1].strip().strip("'\"").lower()
    return None


def finished_plans() -> list[Path]:
    if not PLANS_DIR.is_dir():
        return []
    out = []
    for p in sorted(PLANS_DIR.glob("*.md")):
        if p.name == "INDEX.md":
            continue
        if (plan_status(p) or "") in FINISHED:
            out.append(p)
    return out


def regenerate_archive_index() -> None:
    if ARCHIVE_DIR.is_dir() and any(ARCHIVE_DIR.glob("*.md")):
        (ARCHIVE_DIR / "INDEX.md").write_text(render(ARCHIVE_DIR), encoding="utf-8")


def main(argv: list[str]) -> int:
    dry = "--dry-run" in argv
    check = "--check" in argv

    finished = finished_plans()

    if check:
        if finished:
            print(
                "Finished plans still in the working set (run archive_plans.py):",
                file=sys.stderr,
            )
            for p in finished:
                print(f"  {p}  (status: {plan_status(p)})", file=sys.stderr)
            return 1
        return 0

    if not finished:
        print("No finished plans to archive.")
        return 0

    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
    for p in finished:
        dest = ARCHIVE_DIR / p.name
        status = plan_status(p)  # capture before the move
        if dry:
            print(f"would move {p} -> {dest}  (status: {status})")
        else:
            shutil.move(str(p), str(dest))
            print(f"archived {p.name}  (status: {status})")

    if not dry:
        regenerate_archive_index()
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
