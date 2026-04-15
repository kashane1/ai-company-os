"""Phase 0.5a — baseline benchmark for claim_task → submit_task_result.

Captures today's median and p99 latencies into
`state/benchmarks/2026-04-14-pre-phase-0.json` so every subsequent
Phase 0.5 sub-PR can compare against this file.

**D1 hardening rule:** this test MUST NOT import from
`packages/db/connection.py` (which doesn't exist yet). The benchmark
uses the existing stack — `ControlPlaneService`, `TaskQueue`,
`ControlPlaneDatabase` — against a test-isolated state root, so it
measures pre-Phase-0.5b behavior (default `busy_timeout=0`, no WAL,
implicit DELETE-mode journal).

Re-run this benchmark in Phase 0.5b's PR and compare — the "<100 ms
regression" NFR from the plan is enforced by asserting median and p99
are no worse than 1.2x of the pre-Phase-0 baseline.

Usage:
    # Capture baseline (first run, on main before Phase 0.5b lands):
    pytest tests/python/perf/test_dispatch_baseline.py -q --capture-baseline

    # Verify regression on subsequent runs:
    pytest tests/python/perf/test_dispatch_baseline.py -q
"""
from __future__ import annotations

import json
import os
import statistics
import time
from pathlib import Path

import pytest

from apps.api.control_plane import ControlPlaneService
from packages.config.settings import (
    TEST_REPO_ROOT_ENV_VAR,
    ensure_runtime_directories,
)
from packages.schemas.task_packet import RiskLevel, TaskStatus, WorkerLane


BASELINE_PATH = (
    Path(__file__).resolve().parents[3]
    / "state"
    / "benchmarks"
    / "2026-04-14-pre-phase-0.json"
)

ITERATIONS = 50
WARMUP = 5
REGRESSION_TOLERANCE = 1.2  # 20% headroom


@pytest.fixture
def isolated_platform(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Isolated repo root → isolated state root → isolated control plane DB.

    Mirrors the existing `isolated_repo_root` fixture in conftest.py but
    strips down to the minimum needed for a queue benchmark (no infra/
    or docs/ copy). Every test invocation starts with a fresh DB, so the
    benchmark measures steady-state claim/submit round-trip latency
    without cross-test state leakage.
    """
    test_root = tmp_path / "isolated"
    (test_root / "state" / "platform").mkdir(parents=True)
    monkeypatch.setenv(TEST_REPO_ROOT_ENV_VAR, str(test_root))
    ensure_runtime_directories()
    return test_root


def _round_trip_once(service: ControlPlaneService, goal_id: str, i: int) -> float:
    """One full claim_task → submit_task_result cycle. Returns elapsed seconds."""
    task = service.create_task_for_goal(
        goal_id=goal_id,
        repo_id="ai-company-os",
        lane=WorkerLane.ENGINEERING,
        title=f"bench task {i}",
        summary="benchmark task",
        task_type="bench",
        risk_level=RiskLevel.LOW,
    )
    start = time.perf_counter()
    claimed = service.claim_task(lane=WorkerLane.ENGINEERING, worker_id="bench-worker")
    assert claimed is not None and claimed.id == task.id
    service.submit_task_result(
        task_id=claimed.id,
        status=TaskStatus.COMPLETED,
        summary="bench complete",
        worker_id="bench-worker",
    )
    return time.perf_counter() - start


def _run_benchmark(isolated_platform: Path) -> dict[str, float]:
    service = ControlPlaneService()
    goal = service.create_goal(
        title="Benchmark Goal",
        summary="claim→submit baseline",
    )

    # Warmup — Python import cost + SQLite file creation + schema init.
    for i in range(WARMUP):
        _round_trip_once(service, goal.id, -i - 1)

    samples_ms: list[float] = []
    for i in range(ITERATIONS):
        samples_ms.append(_round_trip_once(service, goal.id, i) * 1000.0)

    samples_ms.sort()
    return {
        "iterations": ITERATIONS,
        "warmup": WARMUP,
        "median_ms": statistics.median(samples_ms),
        "mean_ms": statistics.mean(samples_ms),
        "p50_ms": samples_ms[int(len(samples_ms) * 0.50)],
        "p95_ms": samples_ms[int(len(samples_ms) * 0.95)],
        "p99_ms": samples_ms[min(int(len(samples_ms) * 0.99), len(samples_ms) - 1)],
        "min_ms": samples_ms[0],
        "max_ms": samples_ms[-1],
    }


def test_capture_or_verify_dispatch_baseline(isolated_platform: Path) -> None:
    """Capture baseline if --capture-baseline is passed, else verify regression."""
    results = _run_benchmark(isolated_platform)

    if os.environ.get("CAPTURE_BASELINE") == "1":
        BASELINE_PATH.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "captured_at": "2026-04-14",
            "phase": "pre-phase-0",
            "notes": (
                "Baseline captured before Phase 0.5b SQLite WAL bootstrap. "
                "D1 hardening: this benchmark MUST NOT import packages/db/connection.py."
            ),
            "metrics": results,
        }
        BASELINE_PATH.write_text(json.dumps(payload, indent=2) + "\n")
        print(f"\nBaseline captured at {BASELINE_PATH}")
        print(f"Median: {results['median_ms']:.3f} ms   p99: {results['p99_ms']:.3f} ms")
        return

    # Verification mode — require a baseline file to exist.
    if not BASELINE_PATH.exists():
        pytest.skip(
            f"No baseline at {BASELINE_PATH}. "
            "Run once with CAPTURE_BASELINE=1 to capture."
        )

    baseline = json.loads(BASELINE_PATH.read_text())["metrics"]
    tolerance = REGRESSION_TOLERANCE

    for metric in ("median_ms", "p95_ms", "p99_ms"):
        observed = results[metric]
        expected_max = baseline[metric] * tolerance
        assert observed <= expected_max, (
            f"{metric} regressed: observed {observed:.3f} ms, "
            f"baseline {baseline[metric]:.3f} ms, "
            f"allowed max {expected_max:.3f} ms "
            f"({int((tolerance - 1) * 100)}% headroom)"
        )
