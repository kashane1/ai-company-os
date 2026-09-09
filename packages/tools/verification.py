"""Execute operator-configured checks; agent prose is never execution evidence."""

from __future__ import annotations

import hashlib
import json
import os
import signal
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

from packages.schemas.repo import VerificationCommand
from packages.schemas.task_run import ValidationCheck, VerificationResult
from packages.tools.git_changes import capture_review_diff
from packages.tools.observability.redaction import redact


def verification_check(results: list[VerificationResult]) -> ValidationCheck:
    passed = bool(results) and all(result.passed for result in results)
    return ValidationCheck(
        name="verification_commands_passed",
        passed=passed,
        details=(f"Executed {len(results)} configured verification command(s)."
                 if results else "No configured verification command was executed."),
        code=None if passed else ("verification_failed" if results else "verification_missing"),
    )


def _ios_destination() -> str:
    completed = subprocess.run(
        ["xcrun", "simctl", "list", "devices", "available", "-j"],
        capture_output=True, text=True, check=True, timeout=30,
    )
    devices = json.loads(completed.stdout)["devices"]
    for runtime in sorted(devices, reverse=True):
        if "iOS" in runtime:
            for device in devices[runtime]:
                if device.get("isAvailable") and device["name"].startswith("iPhone"):
                    return f"platform=iOS Simulator,id={device['udid']}"
    raise ValueError("No available iPhone simulator for verification")


def run_verification(
    commands: list[VerificationCommand], worktree_path: str, artifact_dir: Path,
) -> list[VerificationResult]:
    """Run argv without a shell, stop at first failure, retain redacted diagnostics.

    The registry is loaded by the worker before Codex runs. Commands execute in
    the task worktree with a restricted environment and their own process group.
    Missing tools, invalid directories, and timeouts are failed evidence.
    """
    results: list[VerificationResult] = []
    root = Path(worktree_path).resolve()
    if not commands:
        return results
    artifact_dir.mkdir(parents=True, exist_ok=True)
    # Do not forward credentials or the worker's operational database/queue.
    env = {key: value for key, value in os.environ.items() if key in {
        "PATH", "HOME", "TMPDIR", "LANG", "LC_ALL", "DEVELOPER_DIR", "SDKROOT",
    }}
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["PYTEST_ADDOPTS"] = "-p no:cacheprovider"
    env["AI_COMPANY_OS_REPO_ROOT"] = str(root)
    env["AI_COMPANY_OS_QUEUE_BACKEND"] = "database"
    for index, spec in enumerate(commands):
        started = datetime.now(UTC).isoformat()
        stdout_path = artifact_dir / f"{index + 1:02d}.stdout.log"
        stderr_path = artifact_dir / f"{index + 1:02d}.stderr.log"
        argv = [arg.replace("{python}", sys.executable).replace("{worktree}", str(root)).replace("{artifacts}", str(artifact_dir.resolve()))
                for arg in spec.argv]
        cwd = (root / spec.cwd).resolve()
        revision = "unavailable"
        diff_sha256 = ""
        timed_out = False
        stdout, stderr = "", ""
        exit_code = 127
        try:
            if not cwd.is_relative_to(root):
                raise ValueError("Verification cwd must remain inside the task worktree")
            revision = subprocess.run(
                ["git", "-C", str(root), "rev-parse", "HEAD"],
                capture_output=True, text=True, check=True, timeout=30,
            ).stdout.strip()
            if any("{ios_destination}" in arg for arg in argv):
                destination = _ios_destination()
                argv = [arg.replace("{ios_destination}", destination) for arg in argv]
            before_diff = capture_review_diff(root)
            diff_sha256 = hashlib.sha256(before_diff.encode("utf-8", errors="surrogateescape")).hexdigest()
            process = subprocess.Popen(
                argv, cwd=cwd, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                text=True, errors="replace", start_new_session=True,
            )
            try:
                stdout, stderr = process.communicate(timeout=spec.timeout_seconds)
            except subprocess.TimeoutExpired:
                timed_out = True
                os.killpg(process.pid, signal.SIGKILL)
                stdout, stderr = process.communicate()
                stderr += "\nVerification command timed out."
            exit_code = process.returncode
            if capture_review_diff(root) != before_diff:
                exit_code = exit_code or 1
                stderr += "\nVerification changed the reviewed worktree; review and verify the new changes."
        except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as exc:
            exit_code = 127
            stderr = f"Verification could not run: {type(exc).__name__}: {exc}"
        stdout_path.write_text(redact(stdout).text)
        stderr_path.write_text(redact(stderr).text)
        results.append(VerificationResult(
            command=[redact(arg).text for arg in argv], cwd=str(cwd), revision=revision,
            exit_code=exit_code, timed_out=timed_out, diff_sha256=diff_sha256,
            stdout_path=str(stdout_path), stderr_path=str(stderr_path),
            started_at=started, finished_at=datetime.now(UTC).isoformat(),
        ))
        if not results[-1].passed:
            break
    return results
