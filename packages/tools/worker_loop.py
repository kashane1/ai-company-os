"""Shared failure handling for long-running worker lanes."""

from __future__ import annotations

import json
import logging
from collections.abc import Callable
from dataclasses import dataclass
from threading import Event
from typing import Any

from packages.tools.observability.redaction import redact

MAX_CONSECUTIVE_INFRASTRUCTURE_FAILURES = 3
MAX_INFRASTRUCTURE_BACKOFF_SECONDS = 30.0
MIN_INFRASTRUCTURE_BACKOFF_SECONDS = 0.1
_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class WorkerLoopStats:
    worker_id: str
    processed_count: int
    idle_cycles: int
    stop_reason: str
    infrastructure_failure_count: int = 0


def redacted_error_message(error: Exception) -> str:
    """Return an error message suitable for runtime state and diagnostics."""
    return redact(str(error)).text


def _backoff_seconds(*, poll_interval_seconds: float, consecutive_failures: int) -> float:
    return min(
        max(poll_interval_seconds, MIN_INFRASTRUCTURE_BACKOFF_SECONDS)
        * (2 ** (consecutive_failures - 1)),
        MAX_INFRASTRUCTURE_BACKOFF_SECONDS,
    )


def _log_infrastructure_failure(
    *,
    worker_id: str,
    error: Exception,
    failure_count: int,
) -> None:
    _LOGGER.error(
        json.dumps(
            {
                "event": "worker_infrastructure_failure",
                "worker_id": worker_id,
                "failure_count": failure_count,
                "exception_type": type(error).__name__,
                "message": redacted_error_message(error),
            },
            sort_keys=True,
        )
    )


def run_worker_loop(
    *,
    worker_id: str,
    work_once: Callable[[], Any | None],
    poll_interval_seconds: float,
    stop_event: Event | None = None,
    sleep_fn: Callable[[float], None],
    max_iterations: int | None = None,
    sleep_after_result: bool = False,
) -> WorkerLoopStats:
    """Run worker polling with bounded recovery for control-plane failures.

    ``work_once`` returns a task result when a task was handled and ``None``
    when the queue is empty. Exceptions are infrastructure failures because a
    claimed task's execution failures must already be persisted as results by
    the caller before this loop is reached.
    """
    stop_signal = stop_event or Event()
    processed_count = 0
    idle_cycles = 0
    infrastructure_failure_count = 0
    consecutive_failures = 0
    iterations = 0
    stop_reason = "stopped"

    while not stop_signal.is_set():
        try:
            result = work_once()
        except KeyboardInterrupt:
            stop_reason = "interrupted"
            break
        except Exception as error:
            iterations += 1
            infrastructure_failure_count += 1
            consecutive_failures += 1
            stop_reason = "failed"
            _log_infrastructure_failure(
                worker_id=worker_id,
                error=error,
                failure_count=consecutive_failures,
            )
            if consecutive_failures >= MAX_CONSECUTIVE_INFRASTRUCTURE_FAILURES:
                stop_reason = "failed"
                break
            if max_iterations is not None and iterations >= max_iterations:
                break
            try:
                sleep_fn(
                    _backoff_seconds(
                        poll_interval_seconds=poll_interval_seconds,
                        consecutive_failures=consecutive_failures,
                    )
                )
            except KeyboardInterrupt:
                stop_reason = "interrupted"
                break
            continue

        iterations += 1
        consecutive_failures = 0
        if result is None:
            idle_cycles += 1
            stop_reason = "idle"
            try:
                sleep_fn(poll_interval_seconds)
            except KeyboardInterrupt:
                stop_reason = "interrupted"
                break
        else:
            processed_count += 1
            stop_reason = "processed"
            if sleep_after_result:
                try:
                    sleep_fn(poll_interval_seconds)
                except KeyboardInterrupt:
                    stop_reason = "interrupted"
                    break

        if max_iterations is not None and iterations >= max_iterations:
            break

    if stop_signal.is_set():
        stop_reason = "stop_requested"

    return WorkerLoopStats(
        worker_id=worker_id,
        processed_count=processed_count,
        idle_cycles=idle_cycles,
        stop_reason=stop_reason,
        infrastructure_failure_count=infrastructure_failure_count,
    )


def worker_exit_code(stats: WorkerLoopStats) -> int:
    return 1 if stats.stop_reason == "failed" else 0
