"""One-off: deploy the Better Business Web funnel site to Netlify (production).

Operator-approved production deploy of products/better-business-web/site/dist.
Runs the first-party launch checklist first, then publishes via the file-digest
Netlify target. Run from repo root: `python scripts/web/deploy_bbw.py`.
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from packages.agency.launch import run_launch_checklist  # noqa: E402
from packages.web.deploy import NetlifyDeployTarget  # noqa: E402

DIST = REPO / "products" / "better-business-web" / "site" / "dist"


def main() -> None:
    print("== launch checklist (first-party, operator-approved) ==")
    report = run_launch_checklist(DIST, first_party=True, deploy_approved=True)
    for it in report.items:
        print(f"  [{'PASS' if it.passed else 'FAIL'}] {it.name}: {it.detail}")
    print("  ready:", report.ready)

    print("\n== netlify deploy ==")
    target = NetlifyDeployTarget()
    site = target.ensure_site("better-business-web")
    print(f"  site: id={site.site_id} name={site.name!r} url={site.url}")
    result = target.deploy(site, DIST, production=True)
    print(f"  deploy: id={result.deploy_id} state={result.state}")
    print(f"\nLIVE URL: {result.url or site.url}")


if __name__ == "__main__":
    main()
