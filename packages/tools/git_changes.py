from __future__ import annotations

import subprocess
from pathlib import Path


class GitChangeCaptureError(RuntimeError):
    """Git could not produce the review evidence required for a worktree."""


def capture_git_status(repo_path: str | Path) -> tuple[list[str], list[str]]:
    """Return individual porcelain status records without Git's directory collapsing."""
    completed = _run_git(
        repo_path,
        ["status", "--porcelain=v1", "-z", "--untracked-files=all"],
    )
    records = completed.stdout.split(b"\0")
    status_lines: list[str] = []
    changed_files: list[str] = []
    index = 0

    while index < len(records):
        record = records[index]
        index += 1
        if not record:
            continue

        status = _decode(record[:2])
        path = _decode(record[3:])
        if "R" in status or "C" in status:
            if index >= len(records) or not records[index]:
                raise GitChangeCaptureError("Git returned an incomplete rename or copy status record.")
            previous_path = _decode(records[index])
            index += 1
            status_lines.append(f"{status}\t{previous_path}\t{path}")
            changed_files.append(f"{previous_path} -> {path}")
            continue

        status_lines.append(f"{status} {path}")
        changed_files.append(path)

    return status_lines, changed_files


def capture_review_diff(repo_path: str | Path) -> str:
    """Capture every uncommitted change without changing the worktree or index."""
    tracked = _run_git(
        repo_path,
        ["diff", "--binary", "--stat", "--patch", "HEAD", "--"],
    ).stdout
    chunks = [tracked] if tracked else []

    for path in _untracked_files(repo_path):
        completed = _run_git(
            repo_path,
            ["diff", "--no-index", "--binary", "--stat", "--patch", "--", "/dev/null", path],
            allowed_returncodes=(0, 1),
        )
        if completed.stdout:
            chunks.append(completed.stdout)

    return b"\n".join(chunks).decode("utf-8", errors="surrogateescape")


def _untracked_files(repo_path: str | Path) -> list[str]:
    completed = _run_git(repo_path, ["ls-files", "--others", "--exclude-standard", "-z"])
    return [_decode(path) for path in completed.stdout.split(b"\0") if path]


def _run_git(
    repo_path: str | Path,
    args: list[str],
    *,
    allowed_returncodes: tuple[int, ...] = (0,),
) -> subprocess.CompletedProcess[bytes]:
    completed = subprocess.run(
        ["git", "-c", "core.quotePath=false", "-C", str(repo_path), *args],
        capture_output=True,
    )
    if completed.returncode not in allowed_returncodes:
        raise GitChangeCaptureError(
            f"Git command failed with exit code {completed.returncode}: {' '.join(args)}"
        )
    return completed


def _decode(value: bytes) -> str:
    return value.decode("utf-8", errors="surrogateescape")
