import subprocess
from pathlib import Path

from packages.schemas.task_run import GitStateSnapshot


def run_git_command(repo_path: str, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", repo_path, *args],
        text=True,
        capture_output=True,
    )


def initialize_git_snapshot(repo_path: Path) -> None:
    run_git_command(str(repo_path), "init")
    run_git_command(str(repo_path), "config", "user.name", "AI Company OS")
    run_git_command(str(repo_path), "config", "user.email", "ai-company-os@example.local")
    run_git_command(str(repo_path), "add", "-A")
    run_git_command(str(repo_path), "commit", "--allow-empty", "-m", "Managed snapshot baseline")


def capture_git_state(repo_path: str) -> GitStateSnapshot:
    status = run_git_command(repo_path, "status", "--short")
    diff_stat = run_git_command(repo_path, "diff", "--stat")
    status_lines = [line for line in status.stdout.splitlines() if line.strip()]
    changed_files: list[str] = []
    for line in status_lines:
        parts = line.split(maxsplit=1)
        if len(parts) == 2:
            changed_files.append(parts[1])
    return GitStateSnapshot(
        status_lines=status_lines,
        changed_files=changed_files,
        diff_summary=diff_stat.stdout.strip(),
    )
