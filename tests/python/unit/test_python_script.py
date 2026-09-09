"""The public test command must run both independent gates and preserve failures."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest


@pytest.mark.parametrize("failed_stage", [None, "latency", "coverage"])
def test_python_script_preserves_each_gate_failure(
    tmp_path: Path, failed_stage: str | None
) -> None:
    checkout = tmp_path / "checkout with spaces"
    scripts = checkout / "scripts"
    scripts.mkdir(parents=True)
    source = Path(__file__).resolve().parents[3] / "scripts" / "test_python.sh"
    shutil.copyfile(source, scripts / source.name)
    calls = tmp_path / "calls.jsonl"
    interpreter = tmp_path / "fake python"
    interpreter.write_text(
        f"#!{sys.executable}\n"
        "import json, os, sys\n"
        "if sys.argv[1:3] == ['-m', 'pytest']:\n"
        "    with open(os.environ['TEST_SCRIPT_CALLS'], 'a') as log:\n"
        "        log.write(json.dumps(sys.argv[1:]) + '\\n')\n"
        "    stage = 'latency' if '--no-cov' in sys.argv else 'coverage'\n"
        "    if os.environ.get('TEST_SCRIPT_FAIL') == stage:\n"
        "        sys.exit(7)\n",
        encoding="utf-8",
    )
    interpreter.chmod(0o755)
    env = {
        **os.environ,
        "PYTHON_BIN": str(interpreter),
        "TEST_SCRIPT_CALLS": str(calls),
        "TEST_SCRIPT_FAIL": failed_stage or "",
        "PYTHON_COVERAGE_MIN": "85",
    }
    result = subprocess.run(
        ["bash", str(scripts / source.name)],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == (7 if failed_stage else 0), result.stderr
    invocations = [json.loads(line) for line in calls.read_text().splitlines()]
    assert len(invocations) == (1 if failed_stage == "latency" else 2)
    latency = invocations[0]
    assert str(checkout / "tests/python/perf") in latency
    assert "--no-cov" in latency
    assert not any(arg.startswith("--cov=") for arg in latency)
    assert f"--junitxml={checkout}/build/test-results/python-latency-junit.xml" in latency
    if failed_stage != "latency":
        coverage = invocations[1]
        assert f"--ignore={checkout}/tests/python/perf" in coverage
        assert "--cov=apps" in coverage and "--cov=packages" in coverage
        assert coverage[coverage.index("--cov-fail-under") + 1] == "85"
