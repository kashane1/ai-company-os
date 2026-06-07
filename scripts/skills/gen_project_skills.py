#!/usr/bin/env python3
"""Generate the .claude/skills/<id>.md project-skill pointers from adapters.

Token-efficiency + drift elimination: a project-skill pointer is 100% derivable
from its Claude adapter (description + canonical_source) plus the fixed WIRING
template. Hand-maintaining 35 of them means the `description:` is copy-pasted in
three places and drifts. This script makes the adapter the single source and
regenerates the pointers, so the duplication can never go stale.

The set of pointers is fixed by what already exists in .claude/skills/ — this
script refreshes their content from the adapter; it does NOT invent pointers for
skills that were deliberately left without one.

Usage:
    python3 scripts/skills/gen_project_skills.py            # regenerate
    python3 scripts/skills/gen_project_skills.py --check     # CI: nonzero if drift

See skills/WIRING.md for the convention this implements.
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
POINTERS = REPO / ".claude" / "skills"
ADAPTERS = REPO / "skills" / "adapters" / "claude"


def frontmatter(path: Path) -> dict[str, str]:
    text = path.read_text(encoding="utf-8", errors="replace")
    if not text.startswith("---"):
        return {}
    end = text.find("\n---", 3)
    if end == -1:
        return {}
    fm: dict[str, str] = {}
    for line in text[3:end].splitlines():
        if ":" in line and not line.lstrip().startswith("#"):
            key, _, val = line.partition(":")
            fm[key.strip().lower()] = val.strip()
    return fm


def render_pointer(skill_id: str, description: str, canonical_source: str) -> str:
    adapter_rel = f"skills/adapters/claude/{skill_id}.md"
    return (
        "---\n"
        f"description: {description}\n"
        f"canonical_source: {canonical_source}\n"
        f"adapter_source: {adapter_rel}\n"
        "---\n\n"
        "<!-- This is a Claude Code project skill. It routes to the canonical skill via its adapter. -->\n"
        "<!-- Do not add skill logic here. Edit the adapter or canonical source instead. -->\n\n"
        f"Read and follow the skill instructions at `{adapter_rel}`.\n\n"
        f"That adapter implements `{canonical_source}` — the canonical source of truth for this skill.\n"
    )


def main(argv: list[str]) -> int:
    check = "--check" in argv
    problems: list[str] = []
    drift: list[str] = []
    wrote = 0

    for pointer in sorted(POINTERS.glob("*.md")):
        skill_id = pointer.stem
        adapter = ADAPTERS / f"{skill_id}.md"
        if not adapter.exists():
            problems.append(f"{pointer.name}: no adapter at {adapter.relative_to(REPO)}")
            continue
        fm = frontmatter(adapter)
        description = fm.get("description", "").strip()
        canonical_source = fm.get("canonical_source", "").strip()
        if not description or not canonical_source:
            problems.append(
                f"{adapter.relative_to(REPO)}: adapter frontmatter missing "
                "description/canonical_source (source of truth for the pointer)"
            )
            continue
        expected = render_pointer(skill_id, description, canonical_source)
        current = pointer.read_text(encoding="utf-8")
        if current == expected:
            continue
        if check:
            drift.append(pointer.relative_to(REPO).as_posix())
        else:
            pointer.write_text(expected, encoding="utf-8")
            wrote += 1

    if problems:
        # Legacy adapters without YAML frontmatter can't be the generated source
        # yet. Warn (don't fail CI) — these are tracked for normalization in
        # todos/. Their pointers are left untouched.
        print(
            f"warning: {len(problems)} legacy adapter(s) lack frontmatter "
            "(description/canonical_source) — pointers left as-is:",
            file=sys.stderr,
        )
        for p in problems:
            print(f"  ! {p}", file=sys.stderr)

    if check:
        if drift:
            print("Project-skill pointers out of sync with adapters:", file=sys.stderr)
            for d in drift:
                print(f"  {d}  (run gen_project_skills.py)", file=sys.stderr)
            return 1
        print("All conforming project-skill pointers match their adapters.")
        return 0

    print(f"regenerated {wrote} project-skill pointer(s); {len(problems)} problem(s)")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
