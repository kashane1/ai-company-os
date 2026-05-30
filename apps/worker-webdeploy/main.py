"""WEBDEPLOY worker entrypoint (F5).

Publishes a built web product behind the deploy-readiness gate. Separate from the
WEB build worker on purpose: building a site and putting it in front of the
public are different actions with different blast radius. Production deploys,
custom domains/DNS, and hosting spend are all approval-gated
(``packages/policies/deploy_readiness.py``).

Defaults to a Netlify target (its free tier permits commercial use). The
orchestration core (``webdeploy/runner.py``) is pure and unit-tested.
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

from webdeploy.runner import WebDeployOutcome, run_webdeploy  # noqa: E402


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="WEBDEPLOY worker — publish a built web product")
    parser.add_argument("project_dir", help="path to the web product (contains dist/)")
    parser.add_argument("site_name", help="deploy target site name")
    parser.add_argument("--production", action="store_true", help="promote to production (gated)")
    parser.add_argument("--preview-reviewed", action="store_true")
    parser.add_argument("--approved", action="store_true", help="a human approval was granted")
    args = parser.parse_args()

    from packages.web.deploy import NetlifyDeployTarget

    outcome: WebDeployOutcome = run_webdeploy(
        Path(args.project_dir),
        args.site_name,
        target=NetlifyDeployTarget(),
        production=args.production,
        preview_reviewed=args.preview_reviewed,
        approval_granted=args.approved,
    )
    kind = "production" if outcome.result.production else "preview"
    print(f"Deployed ({kind}) → {outcome.result.url}  [{outcome.result.state}]")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
