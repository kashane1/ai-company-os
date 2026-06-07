#!/usr/bin/env python3
"""Lead-pipeline health across the agency's own funnel + every form-having client.

One entrypoint for the scheduled monitor. It checks:

* The agency's OWN landing-page funnel — drained review requests under
  state/prospects/inbound/ (the lead path that matters most for the business).
* Every client site that bought `contact_forms` and has a recorded netlify_site_id
  (registry.lead_drain_targets) — drained leads under state/clients/<id>/leads/.

Form-less clients are skipped entirely (they're not drain targets), so there are no
false "no leads" nags. Run the drains first (pull-inbound.mjs, pull-leads.mjs).

Exit code = worst verdict found: 0 ok, 1 warn, 2 alert — so a launchd/cron wrapper
pages on alerts.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from packages.agency.lead_health import (  # noqa: E402
    LeadHealthStatus,
    assess_lead_health,
    load_leads_from_dir,
)
from packages.agency.registry import lead_drain_targets  # noqa: E402

FUNNEL_PRODUCT_ID = "better-business-web"
_EXIT = {LeadHealthStatus.OK: 0, LeadHealthStatus.WARN: 1, LeadHealthStatus.ALERT: 2}


def _assess(leads_dir: Path, *, product_id: str, as_of: date, window_days: int):
    # Reachability is the drain's concern (pull-leads.mjs exits non-zero on store
    # failure); a missing local dir just means nothing's been drained yet → empty.
    return assess_lead_health(
        load_leads_from_dir(leads_dir),
        product_id=product_id,
        as_of=as_of,
        window_days=window_days,
        store_reachable=True,
        lead_capture_expected=True,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--as-of", required=True, help="reference date YYYY-MM-DD")
    parser.add_argument("--window-days", type=int, default=30)
    parser.add_argument("--state-root", type=Path, default=REPO / "state")
    parser.add_argument("--skip-funnel", action="store_true", help="skip the agency's own funnel")
    args = parser.parse_args()
    as_of = date.fromisoformat(args.as_of)

    results = []
    if not args.skip_funnel:
        funnel_dir = args.state_root / "prospects" / "inbound"
        results.append(
            _assess(
                funnel_dir,
                product_id=FUNNEL_PRODUCT_ID,
                as_of=as_of,
                window_days=args.window_days,
            )
        )

    for target in lead_drain_targets():
        leads_dir = args.state_root / "clients" / target["product_id"] / "leads"
        results.append(
            _assess(
                leads_dir,
                product_id=target["product_id"],
                as_of=as_of,
                window_days=args.window_days,
            )
        )

    worst = LeadHealthStatus.OK
    for health in results:
        if _EXIT[health.status] > _EXIT[worst]:
            worst = health.status

    print(
        json.dumps(
            {
                "as_of": args.as_of,
                "checked": len(results),
                "worst_status": worst.value,
                "results": [h.to_dict() for h in results],
            },
            indent=2,
        )
    )
    return _EXIT[worst]


if __name__ == "__main__":
    raise SystemExit(main())
