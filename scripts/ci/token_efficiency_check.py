#!/usr/bin/env python3
"""Token-efficiency gate.

Catches regressions that make the repo more expensive for AI agents to operate
in. Designed to *ratchet*: existing legacy offenders are grandfathered via a
baseline file, so the bar only applies to new/changed content and never blocks
the build on pre-existing debt.

Checks
------
A. Plans archived         — no finished plan (status: completed/shipped/...) is
                            still in the docs/plans/ working set.
B. No tracked runtime data — only the state contract and empty directory markers
                             belong in git; even small receipts stay private.
C. Large-doc TL;DR        — every tracked doc over TLDR_THRESHOLD lines opens
                            with a TL;DR (frontmatter summary/tldr, a blockquote,
                            or a Summary/TL;DR heading near the top). Existing
                            offenders are grandfathered in BASELINE.

Usage
-----
    python3 scripts/ci/token_efficiency_check.py              # enforce (CI + make)
    python3 scripts/ci/token_efficiency_check.py --update-baseline
        # re-record the current large-doc offenders as grandfathered. Run this
        # only when intentionally accepting an existing doc; new docs should add
        # a TL;DR instead.

Exit code is nonzero if any check fails.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
BASELINE = Path(__file__).resolve().parent / "token_efficiency_baseline.txt"

TLDR_THRESHOLD = 400          # lines; docs longer than this need a TL;DR
STATE_README_MAX_BYTES = 64 * 1024
FILE_MAX_BYTES = 8 * 1024 * 1024
DOCS_MAX_BYTES = 150 * 1024 * 1024
TREE_MAX_BYTES = 250 * 1024 * 1024


def tracked(*globs: str) -> list[Path]:
    # Committed files PLUS untracked-but-not-gitignored files, so the gate also
    # catches a new doc before it is committed (local `make tokens-check`,
    # pre-commit). --exclude-standard drops gitignored runtime junk.
    out = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard", *globs],
        cwd=REPO,
        capture_output=True,
        text=True,
        check=True,
    )
    seen = []
    for line in out.stdout.splitlines():
        if line.strip() and (REPO / line) not in seen:
            seen.append(REPO / line)
    return seen


def line_count(path: Path) -> int:
    try:
        with path.open("rb") as fh:
            return sum(1 for _ in fh)
    except OSError:
        return 0


# --- Check A: plans archived -------------------------------------------------

def check_plans_archived() -> list[str]:
    sys.path.insert(0, str(REPO / "scripts" / "docs"))
    try:
        import archive_plans  # noqa: WPS433
    except Exception as exc:  # pragma: no cover
        return [f"could not import archive_plans: {exc}"]
    cwd = Path.cwd()
    import os

    os.chdir(REPO)
    try:
        finished = archive_plans.finished_plans()
    finally:
        os.chdir(cwd)
    return [
        f"{p.relative_to(REPO)} is finished but not in docs/plans/archive/"
        for p in finished
    ]


# --- Check B: no heavy tracked state ----------------------------------------

def check_state_weight() -> list[str]:
    """Enforce the public state boundary by path and bytes, never binary lines."""
    problems = []
    for path in tracked("state"):
        relative = path.relative_to(REPO).as_posix()
        if not path.exists() and not path.is_symlink():
            # A deletion already made in the working tree is not new content.
            continue
        if not path.is_symlink() and path.is_file():
            size = path.stat().st_size
            if relative == "state/README.md" and size <= STATE_README_MAX_BYTES:
                continue
            if path.name == ".gitkeep" and size == 0:
                continue
        problems.append(
            f"{relative} is tracked runtime content; keep it local and publish "
            "reviewed, sanitized examples under docs/examples/ instead"
        )
    return problems


def check_asset_budgets() -> list[str]:
    """Keep the current public tree reviewable without scanning binary lines.

    Includes new, unignored files. These budgets apply to the checkout, not Git
    history; historical blobs remain available and are not rewritten by this gate.
    """
    problems = []
    total = docs_total = 0
    for path in tracked():
        if path.is_symlink() or not path.is_file():
            continue
        size = path.stat().st_size
        relative = path.relative_to(REPO).as_posix()
        total += size
        if relative.startswith("docs/"):
            docs_total += size
        if size > FILE_MAX_BYTES:
            problems.append(f"{relative} exceeds file budget ({size} > {FILE_MAX_BYTES} bytes)")
    if docs_total > DOCS_MAX_BYTES:
        problems.append(f"docs budget exceeded ({docs_total} > {DOCS_MAX_BYTES} bytes)")
    if total > TREE_MAX_BYTES:
        problems.append(f"public tree budget exceeded ({total} > {TREE_MAX_BYTES} bytes)")
    return problems


# --- Check C: large-doc TL;DR ------------------------------------------------

def has_tldr(path: Path) -> bool:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return True
    lines = text.splitlines()

    # Generated index files are their own summary.
    if lines and "GENERATED by scripts/docs/gen_doc_index.py" in lines[0]:
        return True

    idx = 0
    # Frontmatter: accept an explicit summary/tldr field.
    if lines and lines[0].strip() == "---":
        for i in range(1, len(lines)):
            if lines[i].strip() == "---":
                idx = i + 1
                break
            key = lines[i].split(":", 1)[0].strip().lower()
            if key in {"summary", "tldr"} and lines[i].split(":", 1)[1].strip():
                return True

    # Scan the first ~15 non-empty body lines for a TL;DR signal.
    seen = 0
    for line in lines[idx:]:
        s = line.strip()
        if not s:
            continue
        low = s.lower()
        if s.startswith(">"):
            return True
        if low.startswith("#") and ("tl;dr" in low or "tldr" in low or "summary" in low):
            return True
        if s.startswith(("**tl;dr", "**summary")) or low.startswith("tl;dr"):
            return True
        seen += 1
        if seen >= 15:
            break
    return False


def load_baseline() -> set[str]:
    if not BASELINE.exists():
        return set()
    return {
        line.strip()
        for line in BASELINE.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.startswith("#")
    }


def large_doc_offenders() -> list[str]:
    offenders = []
    for path in tracked("docs", "*.md", "todos"):
        if path.suffix != ".md" or path.name == "INDEX.md":
            continue
        if line_count(path) <= TLDR_THRESHOLD:
            continue
        if not has_tldr(path):
            offenders.append(path.relative_to(REPO).as_posix())
    return sorted(offenders)


def check_large_doc_tldr() -> list[str]:
    baseline = load_baseline()
    return [
        f"{rel} is over {TLDR_THRESHOLD} lines without a TL;DR "
        "(add a frontmatter `summary:`/`tldr:`, a `> ` blockquote, or a "
        "`## TL;DR` near the top — see docs/large-doc-standard.md)"
        for rel in large_doc_offenders()
        if rel not in baseline
    ]


def update_baseline() -> int:
    offenders = large_doc_offenders()
    header = (
        "# Grandfathered large docs without a TL;DR. New docs must NOT be added\n"
        "# here — give them a TL;DR instead (see docs/large-doc-standard.md).\n"
        "# Regenerate intentionally with: token_efficiency_check.py --update-baseline\n"
    )
    BASELINE.write_text(header + "\n".join(offenders) + "\n", encoding="utf-8")
    print(f"baseline updated: {len(offenders)} grandfathered docs -> {BASELINE.name}")
    return 0


def main(argv: list[str]) -> int:
    if "--update-baseline" in argv:
        return update_baseline()

    checks = [
        ("Plans archived", check_plans_archived),
        ("No tracked runtime data", check_state_weight),
        ("Public asset budgets", check_asset_budgets),
        ("Large-doc TL;DR", check_large_doc_tldr),
    ]
    failed = False
    for name, fn in checks:
        problems = fn()
        if problems:
            failed = True
            print(f"✗ {name}: {len(problems)} issue(s)")
            for p in problems:
                print(f"    - {p}")
        else:
            print(f"✓ {name}")
    if failed:
        print("\nToken-efficiency gate FAILED.", file=sys.stderr)
        return 1
    print("\nToken-efficiency gate passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
