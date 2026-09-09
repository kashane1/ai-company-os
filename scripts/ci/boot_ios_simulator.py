#!/usr/bin/env python3
"""Boot one iOS Simulator and wait for its services to become ready."""

from __future__ import annotations

import argparse
import math
import subprocess
import sys


class SimulatorBootError(RuntimeError):
    """Raised when the selected simulator cannot be made ready."""


def ensure_simulator_ready(udid: str, timeout_seconds: float) -> None:
    if not math.isfinite(timeout_seconds) or timeout_seconds <= 0:
        raise SimulatorBootError("boot timeout must be a finite number greater than zero")

    try:
        # `bootstatus -b` is safe for an already-booted device and boots a
        # shutdown device before waiting for SpringBoard and migrations.
        subprocess.run(
            ["xcrun", "simctl", "bootstatus", udid, "-b"],
            check=True,
            timeout=timeout_seconds,
        )
    except subprocess.TimeoutExpired as exc:
        raise SimulatorBootError(
            f"simulator {udid} did not become ready within {timeout_seconds:g} seconds"
        ) from exc
    except subprocess.CalledProcessError as exc:
        raise SimulatorBootError(
            f"simctl bootstatus failed for simulator {udid} with exit code {exc.returncode}"
        ) from exc
    except OSError as exc:
        raise SimulatorBootError(f"unable to execute xcrun for simulator {udid}: {exc}") from exc


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("udid")
    parser.add_argument("--timeout-seconds", type=float, default=420)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv if argv is not None else sys.argv[1:])
    try:
        ensure_simulator_ready(args.udid, args.timeout_seconds)
    except SimulatorBootError as exc:
        print(f"Unable to prepare iOS Simulator: {exc}", file=sys.stderr)
        return 1
    print(f"iOS Simulator ready: {args.udid}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
