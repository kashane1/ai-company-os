from __future__ import annotations

import json
import logging
from threading import Event

from packages.tools.worker_loop import WorkerLoopStats, run_worker_loop, worker_exit_code


def test_worker_loop_bounds_infrastructure_retries_and_redacts_diagnostic(caplog) -> None:
    attempts = 0
    sleep_calls: list[float] = []

    def fail_claim() -> None:
        nonlocal attempts
        attempts += 1
        raise RuntimeError("control plane unavailable: token=super-secret-token-value")

    with caplog.at_level(logging.ERROR, logger="packages.tools.worker_loop"):
        stats = run_worker_loop(
            worker_id="worker-engineering",
            work_once=fail_claim,
            poll_interval_seconds=0.25,
            sleep_fn=sleep_calls.append,
        )

    assert attempts == 3
    assert stats == WorkerLoopStats(
        worker_id="worker-engineering",
        processed_count=0,
        idle_cycles=0,
        stop_reason="failed",
        infrastructure_failure_count=3,
    )
    assert sleep_calls == [0.25, 0.5]
    assert worker_exit_code(stats) == 1
    diagnostic = json.loads(caplog.records[-1].message)
    assert diagnostic["event"] == "worker_infrastructure_failure"
    assert diagnostic["exception_type"] == "RuntimeError"
    assert diagnostic["message"] == "control plane unavailable: [REDACTED]"
    assert "super-secret-token-value" not in caplog.text


def test_worker_loop_resets_failure_streak_after_a_successful_cycle() -> None:
    outcomes = iter(
        [
            RuntimeError("temporary database outage"),
            object(),
            RuntimeError("temporary database outage"),
            None,
        ]
    )
    sleep_calls: list[float] = []

    def work_once() -> object | None:
        outcome = next(outcomes)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome

    stats = run_worker_loop(
        worker_id="worker-ios",
        work_once=work_once,
        poll_interval_seconds=0.25,
        sleep_fn=sleep_calls.append,
        max_iterations=4,
    )

    assert stats == WorkerLoopStats(
        worker_id="worker-ios",
        processed_count=1,
        idle_cycles=1,
        stop_reason="idle",
        infrastructure_failure_count=2,
    )
    assert sleep_calls == [0.25, 0.25, 0.25]
    assert worker_exit_code(stats) == 0


def test_worker_loop_honors_stop_request_after_backoff() -> None:
    stop_event = Event()

    def fail_claim() -> None:
        raise ConnectionError("database temporarily unavailable")

    def stop_after_backoff(_seconds: float) -> None:
        stop_event.set()

    stats = run_worker_loop(
        worker_id="worker-outreach",
        work_once=fail_claim,
        poll_interval_seconds=0.25,
        sleep_fn=stop_after_backoff,
        stop_event=stop_event,
    )

    assert stats.stop_reason == "stop_requested"
    assert stats.processed_count == 0
    assert stats.infrastructure_failure_count == 1


def test_worker_loop_reports_a_failure_when_iteration_limit_interrupts_recovery() -> None:
    def fail_claim() -> None:
        raise ConnectionError("database temporarily unavailable")

    stats = run_worker_loop(
        worker_id="worker-appstore",
        work_once=fail_claim,
        poll_interval_seconds=0.25,
        sleep_fn=lambda _seconds: None,
        max_iterations=1,
    )

    assert stats.stop_reason == "failed"
    assert stats.infrastructure_failure_count == 1
    assert worker_exit_code(stats) == 1


def test_worker_loop_floors_zero_poll_interval_for_infrastructure_backoff() -> None:
    stop_event = Event()
    sleep_calls: list[float] = []

    def fail_claim() -> None:
        raise ConnectionError("database temporarily unavailable")

    def stop_after_backoff(seconds: float) -> None:
        sleep_calls.append(seconds)
        stop_event.set()

    run_worker_loop(
        worker_id="worker-outreach",
        work_once=fail_claim,
        poll_interval_seconds=0,
        sleep_fn=stop_after_backoff,
        stop_event=stop_event,
    )

    assert sleep_calls == [0.1]
