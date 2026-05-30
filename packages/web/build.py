"""Web build orchestration — run the framework build, then the gate (F2).

A web project (Astro static-first; see ``packages/web/scaffold``) builds into a
``dist/`` directory with ``npm ci && npm run build``. This module runs that build
behind an **injectable command runner** so the orchestration is unit-testable
without Node installed: tests pass a fake runner and a pre-populated ``dist``.

The worker (``apps/worker-web``) calls :func:`build_and_validate` after Codex has
written/edited the site, and hands the resulting :class:`WebValidationReport`
into the same review/approval surface the other lanes use.
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Sequence

from packages.web.validation import WebValidationReport, validate_web_dist

# A command runner takes (args, cwd) and returns (exit_code, stdout, stderr).
CommandRunner = Callable[[Sequence[str], Path], "tuple[int, str, str]"]

# Static-first default: install exactly from the lockfile, then build.
DEFAULT_BUILD_STEPS: tuple[tuple[str, ...], ...] = (
    ("npm", "ci"),
    ("npm", "run", "build"),
)
DEFAULT_DIST = "dist"


def subprocess_runner(timeout: float = 600.0) -> CommandRunner:
    """A real runner that shells out. Kept behind a factory so the timeout is
    explicit and the default orchestration stays free of subprocess in tests."""

    def run(args: Sequence[str], cwd: Path) -> tuple[int, str, str]:
        try:
            proc = subprocess.run(
                list(args),
                cwd=str(cwd),
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False,
            )
        except FileNotFoundError as exc:
            return (127, "", f"command not found: {args[0]} ({exc})")
        except subprocess.TimeoutExpired:
            return (124, "", f"timed out after {timeout}s: {' '.join(args)}")
        return (proc.returncode, proc.stdout, proc.stderr)

    return run


@dataclass(frozen=True)
class BuildResult:
    exit_code: int
    stdout: str
    stderr: str
    dist_dir: Path

    @property
    def succeeded(self) -> bool:
        return self.exit_code == 0


def build_site(
    project_dir: Path,
    *,
    runner: CommandRunner,
    steps: Sequence[Sequence[str]] = DEFAULT_BUILD_STEPS,
    dist: str = DEFAULT_DIST,
) -> BuildResult:
    """Run each build step in order, stopping at the first failure. The exit
    code/stdout/stderr returned are from the last step that ran."""
    exit_code, stdout, stderr = 0, "", ""
    for step in steps:
        exit_code, stdout, stderr = runner(step, project_dir)
        if exit_code != 0:
            break
    return BuildResult(
        exit_code=exit_code,
        stdout=stdout,
        stderr=stderr,
        dist_dir=project_dir / dist,
    )


def build_and_validate(
    project_dir: Path,
    *,
    runner: CommandRunner,
    steps: Sequence[Sequence[str]] = DEFAULT_BUILD_STEPS,
    dist: str = DEFAULT_DIST,
) -> tuple[BuildResult, WebValidationReport]:
    """Build the site, then run the full web gate over the output.

    If the build fails we skip the dist checks (there's nothing valid to check)
    and return a report containing just the failed build check, so the caller
    sees a single fail-closed result either way.
    """
    build = build_site(project_dir, runner=runner, steps=steps, dist=dist)
    if not build.succeeded or not build.dist_dir.exists():
        report = validate_web_dist(
            build.dist_dir if build.dist_dir.exists() else project_dir,
            build_exit_code=build.exit_code,
            build_stdout=build.stdout,
            build_stderr=build.stderr,
        ) if build.dist_dir.exists() else _build_only_report(build)
        return build, report
    report = validate_web_dist(
        build.dist_dir,
        build_exit_code=build.exit_code,
        build_stdout=build.stdout,
        build_stderr=build.stderr,
    )
    return build, report


def _build_only_report(build: BuildResult) -> WebValidationReport:
    from packages.web.validation import check_build

    return WebValidationReport(
        checks=[check_build(build.exit_code, build.stdout, build.stderr)]
    )
