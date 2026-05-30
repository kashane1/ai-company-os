"""Web worker runner — build + validate a web product (F2).

Mirrors the engineering/iOS runners' shape but for the WEB lane: Codex writes or
edits the site source in an isolated worktree (the platform owns the worktree
lifecycle), then this runner builds it and runs the web gate
(``packages/web/validation.py``). The heavy lifting — the build orchestration and
every check — lives in ``packages/web`` so it's pure and unit-testable; this
module is the thin lane wiring.

Kept deliberately small and dependency-light: the build is injectable (so the
worker can be exercised without Node), and results come back as
``ValidationCheck`` objects identical to the other lanes, so the existing review
+ approval surface applies unchanged.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from packages.web.build import BuildResult, CommandRunner, build_and_validate, subprocess_runner
from packages.web.validation import WebValidationReport


@dataclass(frozen=True)
class WebRunResult:
    project_dir: str
    build: BuildResult
    report: WebValidationReport

    @property
    def safe_for_review(self) -> bool:
        """A web change is safe to put in front of a human reviewer only when
        the build succeeded and every gate check passed."""
        return self.build.succeeded and self.report.passed


def run_web_build(
    project_dir: Path,
    *,
    runner: CommandRunner | None = None,
) -> WebRunResult:
    """Build the site at ``project_dir`` and run the web gate over the output.

    ``runner`` is injectable for tests; production uses a real subprocess runner.
    """
    command_runner = runner or subprocess_runner()
    build, report = build_and_validate(project_dir, runner=command_runner)
    return WebRunResult(project_dir=str(project_dir), build=build, report=report)
