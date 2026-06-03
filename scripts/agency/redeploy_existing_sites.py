#!/usr/bin/env python3
"""Redeploy the current themed build onto ALREADY-EXISTING prospect sites.

Some prospect previews were published earlier as one Netlify *site per prospect*
(``preview-<business>-<city>.netlify.app``). Rather than delete them and
recreate under the new shared-draft model, this updates each existing site
**in place**: it redeploys the current (re-themed) ``dist/index.html`` to the
site we already have (by ``mockup_site_id``), so the live URL shows the new look.

This reuses existing sites — it does **not** create new ones. New/future
previews should still use the shared-draft model in ``prospect_site.py``.

Needs ``$NETLIFY_AUTH_TOKEN`` (loaded from ``.env``).

    python scripts/agency/redeploy_existing_sites.py                 # list (dry run)
    python scripts/agency/redeploy_existing_sites.py --place-id <id> # redeploy ONE
    python scripts/agency/redeploy_existing_sites.py --all           # redeploy all
"""

from __future__ import annotations

import argparse
import glob
import json
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from packages.web.deploy import NetlifyDeployTarget, SiteRef  # noqa: E402

RECORDS_DIR = REPO / "state" / "prospects" / "records"
SITES_DIR = REPO / "state" / "prospects" / "sites"


def deployed_records(
    *, cohort: str | None = None, exclude_verdict: str | None = None, verdict: str | None = None
) -> list[dict]:
    out = []
    for f in glob.glob(str(RECORDS_DIR / "*.json")):
        d = json.loads(Path(f).read_text(encoding="utf-8"))
        if not d.get("mockup_site_id"):
            continue
        if cohort and str(d.get("composite_cohort", "")) != cohort:
            continue
        if exclude_verdict and str(d.get("web_verify_verdict", "")) == exclude_verdict:
            continue
        if verdict and str(d.get("web_verify_verdict", "")) != verdict:
            continue
        out.append(d)
    out.sort(key=lambda d: str(d.get("display_name", "")))
    return out


def _update_record(place_id: str, deploy_id: str, url: str) -> None:
    path = RECORDS_DIR / f"{place_id}.json"
    d = json.loads(path.read_text(encoding="utf-8"))
    d["mockup_deploy_id"] = deploy_id
    if url:
        d["mockup_url"] = url
    path.write_text(json.dumps(d, indent=2), encoding="utf-8")


def redeploy_one(target: NetlifyDeployTarget, record: dict) -> str:
    place_id = str(record["place_id"])
    dist = SITES_DIR / place_id / "dist"
    if not (dist / "index.html").is_file():
        raise FileNotFoundError(f"no themed build at {dist}/index.html (run retheme_sites.py first)")
    site = SiteRef(
        site_id=str(record["mockup_site_id"]),
        name=str(record.get("site_name", "")),
        url=str(record.get("mockup_url", "")),
    )
    # production=True updates the EXISTING live site URL in place.
    result = target.deploy(site, dist, production=True)
    _update_record(place_id, result.deploy_id, result.url)
    return result.url


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--place-id", help="redeploy exactly one record by place_id")
    ap.add_argument("--all", action="store_true", help="redeploy every already-deployed site")
    ap.add_argument("--cohort", help="only records in this composite_cohort (e.g. A_gold)")
    ap.add_argument("--exclude-verdict", help="skip records with this web_verify_verdict (e.g. marketplace_only)")
    ap.add_argument("--verdict", help="only records with this web_verify_verdict (e.g. none_found)")
    ap.add_argument("--delay", type=float, default=20.0, help="seconds between deploys (rate limit)")
    args = ap.parse_args()

    records = deployed_records(
        cohort=args.cohort, exclude_verdict=args.exclude_verdict, verdict=args.verdict
    )
    scope = []
    if args.cohort:
        scope.append(f"cohort={args.cohort}")
    if args.exclude_verdict:
        scope.append(f"exclude verdict={args.exclude_verdict}")
    if args.verdict:
        scope.append(f"verdict={args.verdict}")
    print(f"{len(records)} site(s) in scope" + (f" ({', '.join(scope)})" if scope else "") + ".\n")

    if not args.place_id and not args.all:
        for d in records:
            print(f"  {d.get('genre_id',''):14s} {d.get('web_verify_verdict',''):16s} {d.get('display_name','')[:30]:30s} {d.get('mockup_url','')}")
        print("\nDry run. Re-run with --place-id <id> to test one, or --all.")
        return

    target = NetlifyDeployTarget()  # token from .env

    if args.place_id:
        record = next((d for d in records if d.get("place_id") == args.place_id), None)
        if record is None:
            sys.exit(f"no deployed record with place_id={args.place_id}")
        url = redeploy_one(target, record)
        print(f"  ✓ {record.get('display_name')}  →  {url}")
        return

    ok = failed = 0
    for i, record in enumerate(records):
        try:
            url = redeploy_one(target, record)
            print(f"  ✓ {record.get('display_name')}  →  {url}")
            ok += 1
        except Exception as exc:  # noqa: BLE001
            print(f"  ✗ {record.get('display_name')}: {exc}")
            failed += 1
        if args.delay and i < len(records) - 1:
            time.sleep(args.delay)
    print(f"\nDone. {ok} ok, {failed} failed.")


if __name__ == "__main__":
    main()
