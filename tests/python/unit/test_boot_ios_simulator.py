from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).parents[3]
HELPER = REPO_ROOT / "scripts" / "ci" / "boot_ios_simulator.py"
UDID = "AAAAAAAA-BBBB-CCCC-DDDD-EEEEEEEEEEEE"


def _write_fake_xcrun(tmp_path: Path) -> tuple[Path, Path, Path]:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    state_file = tmp_path / "state"
    log_file = tmp_path / "calls.log"
    fake_xcrun = bin_dir / "xcrun"
    fake_xcrun.write_text(
        """#!/bin/sh
set -eu
printf '%s\\n' "$*" >> "$FAKE_SIMCTL_LOG"
case "$*" in
  "simctl bootstatus "*)
    if [ "${FAKE_SIMCTL_TIMEOUT:-0}" = 1 ]; then
      exec sleep 2
    fi
    if [ "${FAKE_SIMCTL_FAILURE:-0}" = 1 ]; then
      exit 72
    fi
    printf 'Booted' > "$FAKE_SIMCTL_STATE"
    ;;
  *)
    exit 64
    ;;
esac
"""
    )
    fake_xcrun.chmod(0o755)
    return bin_dir, state_file, log_file


def _run_helper(
    tmp_path: Path,
    initial_state: str,
    *,
    timeout: bool = False,
    failure: bool = False,
    timeout_seconds: str | None = None,
) -> subprocess.CompletedProcess[str]:
    bin_dir, state_file, log_file = _write_fake_xcrun(tmp_path)
    state_file.write_text(initial_state)
    env = os.environ.copy()
    env.update(
        {
            "PATH": f"{bin_dir}:{env['PATH']}",
            "FAKE_SIMCTL_LOG": str(log_file),
            "FAKE_SIMCTL_STATE": str(state_file),
            "FAKE_SIMCTL_TIMEOUT": "1" if timeout else "0",
            "FAKE_SIMCTL_FAILURE": "1" if failure else "0",
        }
    )
    return subprocess.run(
        [
            sys.executable,
            str(HELPER),
            UDID,
            "--timeout-seconds",
            timeout_seconds or ("0.05" if timeout else "5"),
        ],
        capture_output=True,
        text=True,
        env=env,
    )


def test_boots_cold_simulator_before_waiting_for_readiness(tmp_path: Path) -> None:
    result = _run_helper(tmp_path, "Shutdown")

    assert result.returncode == 0, result.stderr
    assert (tmp_path / "state").read_text() == "Booted"
    assert (tmp_path / "calls.log").read_text().splitlines() == [
        f"simctl bootstatus {UDID} -b",
    ]


def test_booted_simulator_only_waits_for_readiness(tmp_path: Path) -> None:
    result = _run_helper(tmp_path, "Booted")

    assert result.returncode == 0, result.stderr
    assert (tmp_path / "state").read_text() == "Booted"
    assert (tmp_path / "calls.log").read_text().splitlines() == [
        f"simctl bootstatus {UDID} -b",
    ]


def test_bootstrap_failure_reports_simctl_exit_code(tmp_path: Path) -> None:
    result = _run_helper(tmp_path, "Shutdown", failure=True)

    assert result.returncode == 1
    assert UDID in result.stderr
    assert "exit code 72" in result.stderr


def test_readiness_timeout_fails_with_selected_simulator_diagnostic(tmp_path: Path) -> None:
    result = _run_helper(tmp_path, "Booted", timeout=True)

    assert result.returncode == 1
    assert UDID in result.stderr
    assert "did not become ready within 0.05 seconds" in result.stderr


def test_non_finite_timeout_is_rejected_before_calling_simctl(tmp_path: Path) -> None:
    result = _run_helper(tmp_path, "Shutdown", timeout_seconds="nan")

    assert result.returncode == 1
    assert "finite number greater than zero" in result.stderr
    assert not (tmp_path / "calls.log").exists()


def test_missing_xcrun_has_clear_diagnostic(tmp_path: Path) -> None:
    empty_path = tmp_path / "empty-bin"
    empty_path.mkdir()
    env = os.environ.copy()
    env["PATH"] = str(empty_path)

    result = subprocess.run(
        [sys.executable, str(HELPER), UDID, "--timeout-seconds", "5"],
        capture_output=True,
        text=True,
        env=env,
    )

    assert result.returncode == 1
    assert UDID in result.stderr
    assert "unable to execute xcrun" in result.stderr
