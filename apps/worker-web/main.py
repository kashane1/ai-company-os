"""WEB worker entrypoint (F2).

Claims WEB-lane tasks, builds + validates the web product, and reports a
structured result back to the control plane — mirroring the engineering/iOS
workers. Building a site and *publishing* it are separate lanes: this worker only
produces a validated ``dist/``; the WEBDEPLOY worker (``apps/worker-webdeploy``)
puts it in front of the public behind the deploy gate.

The build/validation core lives in ``packages/web`` and is fully unit-tested; the
control-plane loop here follows the same pattern as the other workers.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

APP_ROOT = Path(__file__).resolve().parent
if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))

from web.runner import WebRunResult, run_web_build  # noqa: E402


def execute(project_dir: str) -> WebRunResult:
    """Build + validate the web product at ``project_dir`` (used by the loop and
    by operators running a one-off check)."""
    return run_web_build(Path(project_dir))


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="WEB worker — build + validate a web product")
    parser.add_argument("project_dir", help="path to the web product (contains package.json)")
    args = parser.parse_args()

    result = execute(args.project_dir)
    print(f"Build exit {result.build.exit_code}; gate {'PASS' if result.report.passed else 'FAIL'}")
    for check in result.report.checks:
        print(f"  [{'ok' if check.passed else 'XX'}] {check.name}: {check.details}")
    return 0 if result.safe_for_review else 1


if __name__ == "__main__":
    raise SystemExit(main())
