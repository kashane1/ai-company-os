#!/usr/bin/env python3
"""Deploy bespoke prospect preview sites (dist-v2) to Netlify.

Customer-facing mockups are built with ``docs/demo-site-build-playbook.md``
(``state/prospects/sites/<place_id>/dist-v2/index.html``). This script only
packages and (optionally) draft-deploys that output — it does **not** generate
token-fill pages unless you pass ``--legacy-build`` (deprecated bulk path).

USAGE
-----
Deploy after a playbook build (needs ``dist-v2/index.html``):

    python scripts/agency/build_prospect_site.py --place-id ChIJ...
    python scripts/agency/build_prospect_site.py --confirmed --limit 5

Draft-deploy to YOUR Netlify account (needs ``$NETLIFY_AUTH_TOKEN``):

    NETLIFY_AUTH_TOKEN=... python scripts/agency/build_prospect_site.py \
        --place-id ChIJ... --deploy --account <your-netlify-team-slug>

Batch draft-deploy + URL backfill (idempotent; --force to re-deploy):

    NETLIFY_AUTH_TOKEN=... python scripts/agency/build_prospect_site.py \
        --batch '*'                          # every built dist-v2 site
    ... --batch state/prospects/audited/cohortA-audited-2026-06-02.csv

Retire lost/suppressed prospects' draft deploys (lists, then confirms):

    NETLIFY_AUTH_TOKEN=... python scripts/agency/build_prospect_site.py --cleanup-drafts

Legacy token-fill build (deprecated — bulk/internal only):

    python scripts/agency/build_prospect_site.py --place-id ChIJ... --legacy-build

Outputs per lead under ``state/prospects/sites/<place_id>/``:
  - dist-v2/index.html         bespoke build (from the playbook)
  - preview.json               deploy metadata
  - outreach-with-mockup.md    personalized draft (never auto-sent)

On deploy, the warehouse record gains ``mockup_url``, ``mockup_site_id``, etc.

Preview/draft deploys are ungated; this script NEVER does a production deploy.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from packages.agency.prospect_site import (  # noqa: E402
    GENRE_PROFILES,
    PREVIEW_SITE_NAME,
    PreviewResult,
    ProspectBuildError,
    ScaffoldCopyError,
    build_preview_for_record,
    city_label,
    deploy_preview_dist,
    intake_from_record,
    profile_fields_used,
    resolve_prospect_dist_dir,
)

RECORDS_DIR = REPO / "state" / "prospects" / "records"
SITES_DIR = REPO / "state" / "prospects" / "sites"
OUTREACH_TEMPLATE = REPO / "state" / "prospects" / "outreach" / "email" / "with-mockup.md"

_FIXTURE_PREFIX = "Fixture Local"


def _load_records() -> list[dict]:
    out = []
    for f in sorted(RECORDS_DIR.glob("*.json")):
        try:
            out.append(json.loads(f.read_text()))
        except (ValueError, OSError):
            continue
    return out


def _is_fixture(rec: dict) -> bool:
    return str(rec.get("display_name", "")).startswith(_FIXTURE_PREFIX)


def select_records(args: argparse.Namespace) -> list[dict]:
    records = _load_records()
    if args.place_id:
        chosen = [r for r in records if r.get("place_id") == args.place_id]
        if not chosen:
            sys.exit(f"no record with place_id={args.place_id}")
        return chosen

    if args.confirmed:
        pool = [
            r
            for r in records
            if r.get("web_verify_verdict") == "none_found" and not _is_fixture(r)
        ]
    elif args.verdict:
        pool = [
            r
            for r in records
            if r.get("web_verify_verdict") == args.verdict and not _is_fixture(r)
        ]
    else:
        sys.exit("specify --place-id, --confirmed, or --verdict <verdict>")

    if args.city:
        pool = [r for r in pool if r.get("city_id") == args.city]
    if args.order == "reviews":
        pool.sort(key=lambda r: -(r.get("user_ratings_total") or 0))
    else:
        pool.sort(key=lambda r: (r.get("city_id", ""), r.get("display_name", "")))
    if args.limit:
        pool = pool[: args.limit]
    return pool


def render_outreach_draft(record: dict, mockup_url: str) -> str:
    if not OUTREACH_TEMPLATE.exists():
        return ""
    # Fail-closed: never draft outreach for a suppressed prospect.
    from packages.agency.suppression import is_suppressed

    if is_suppressed(record):
        return ""
    profile = GENRE_PROFILES.get(str(record.get("genre_id", "")))
    genre_noun = profile.category if profile else "local business"
    reviews = record.get("user_ratings_total")
    repl = {
        "{business_name}": str(record.get("display_name", "")),
        "{owner_name}": "there",
        "{neighborhood}": city_label(str(record.get("city_id", ""))),
        "{city}": city_label(str(record.get("city_id", ""))),
        "{genre_noun}": genre_noun,
        "{observed_gap}": (
            "I couldn't find an owned website for you, just a phone number / directory listings."
        ),
        "{review_count}": f"{reviews}+" if reviews else "your",
        "{mockup_url}": mockup_url or "[preview URL after deploy]",
        "{sender_name}": "Kashane Sakhakorn",
        "{sender_company}": "https://better-business-web.netlify.app/",
    }
    body = OUTREACH_TEMPLATE.read_text()
    for k, v in repl.items():
        body = body.replace(k, v)
    return body


def write_record_mockup_fields(place_id: str, result) -> None:
    path = RECORDS_DIR / f"{place_id}.json"
    if not path.exists():
        return
    rec = json.loads(path.read_text())
    rec["mockup_url"] = result.mockup_url
    rec["mockup_site_id"] = result.site_id
    rec["mockup_deploy_id"] = result.deploy_id
    rec["mockup_built_at"] = datetime.now(timezone.utc).isoformat()
    path.write_text(json.dumps(rec, indent=2))


def clear_record_mockup_fields(place_id: str) -> None:
    """Drop the live-preview fields from a record (used by --cleanup-drafts).

    Clearing ``mockup_url`` is what stops the funnel from counting the prospect
    as deployed and the dashboard from surfacing a dead demo link."""
    path = RECORDS_DIR / f"{place_id}.json"
    if not path.exists():
        return
    rec = json.loads(path.read_text())
    for key in ("mockup_url", "mockup_site_id", "mockup_deploy_id"):
        rec.pop(key, None)
    rec["mockup_cleaned_at"] = datetime.now(timezone.utc).isoformat()
    path.write_text(json.dumps(rec, indent=2))


def _batch_place_ids(value: str) -> list[str]:
    """Resolve a --batch argument to an ordered, de-duplicated list of place_ids.

    A path ending in ``.csv`` is read for its ``place_id`` column; anything else
    is treated as a glob matched against site directories under
    ``state/prospects/sites/`` (e.g. ``'*'`` for all built, ``'ChIJ*'``)."""
    path = Path(value)
    if path.suffix.lower() == ".csv":
        if not path.exists():
            sys.exit(f"--batch: CSV not found: {value}")
        ids: list[str] = []
        with path.open(newline="") as handle:
            reader = csv.DictReader(handle)
            if "place_id" not in (reader.fieldnames or []):
                sys.exit(f"--batch: {value} has no place_id column")
            for row in reader:
                pid = (row.get("place_id") or "").strip()
                if pid:
                    ids.append(pid)
        return list(dict.fromkeys(ids))
    matches = sorted(d.name for d in SITES_DIR.glob(value) if d.is_dir())
    if not matches:
        sys.exit(f"--batch: not a .csv and no site dirs matched {value!r} under {SITES_DIR}")
    return matches


def select_batch_records(value: str) -> list[dict]:
    place_ids = _batch_place_ids(value)
    by_id = {str(r.get("place_id", "")): r for r in _load_records()}
    chosen, missing = [], []
    for pid in place_ids:
        rec = by_id.get(pid)
        (chosen if rec is not None else missing).append(rec if rec is not None else pid)
    if missing:
        print(f"  ({len(missing)} place_id(s) in batch have no warehouse record; skipped)")
    return chosen


def select_cleanup_targets(records: list[dict]) -> list[tuple[dict, str, str]]:
    """Records that are lost or suppressed AND carry a draft deploy to retire.

    Returns ``(record, deploy_id, reason)`` tuples. Pure (no I/O beyond the
    suppression registry) so it is unit-testable."""
    from packages.agency.suppression import is_suppressed

    targets: list[tuple[dict, str, str]] = []
    for rec in records:
        deploy_id = str(rec.get("mockup_deploy_id", "")).strip()
        if not deploy_id:
            continue
        lost = str(rec.get("engagement_status", "")).lower() == "lost"
        suppressed = is_suppressed(rec)
        if lost or suppressed:
            targets.append((rec, deploy_id, "lost" if lost else "suppressed"))
    return targets


def _confirm(prompt: str) -> bool:
    try:
        answer = input(f"{prompt} [y/N] ").strip().lower()
    except EOFError:
        return False
    return answer in ("y", "yes")


def cleanup_drafts(args: argparse.Namespace) -> None:
    """List, confirm, then delete draft deploys for lost/suppressed prospects and
    clear their record URLs. Lists before deleting; requires explicit y/N."""
    targets = select_cleanup_targets(_load_records())
    if not targets:
        print("No lost/suppressed prospects with a draft deploy to clean up.")
        return
    print(f"{len(targets)} draft deploy(s) eligible for cleanup:\n")
    for rec, _deploy_id, reason in targets:
        print(f"  - {rec.get('display_name', '?')}  [{reason}]  {rec.get('mockup_url', '')}")
    print()
    if not _confirm(f"Delete these {len(targets)} draft deploy(s) and clear their record URLs?"):
        print("Aborted; nothing deleted.")
        return
    target, _account = make_target(args.account)
    deleted = failed = 0
    for rec, deploy_id, _reason in targets:
        name = rec.get("display_name", "?")
        try:
            target.delete_deploy(deploy_id)
        except Exception as exc:  # noqa: BLE001
            print(f"  ✗ {name}: delete failed ({exc}); record left intact")
            failed += 1
            continue
        clear_record_mockup_fields(str(rec.get("place_id", "")))
        print(f"  ✓ {name}: draft deploy deleted, record URL cleared")
        deleted += 1
    print(f"\nDone. {deleted} cleaned, {failed} failed.")


def make_target(account_slug: str | None):
    from packages.web.deploy import DeployAccount, NetlifyDeployTarget

    account = DeployAccount(id=account_slug) if account_slug else None
    return NetlifyDeployTarget(account=account), account


def get_profile(record: dict, connector, *, refresh: bool = False) -> dict | None:
    place_id = str(record.get("place_id", ""))
    cache = SITES_DIR / place_id / "places-profile.json"
    if cache.exists() and not refresh:
        try:
            return json.loads(cache.read_text())
        except ValueError:
            pass
    if connector is None:
        return None
    try:
        profile = connector.fetch_profile(place_id)
    except Exception as exc:  # noqa: BLE001
        print(f"    (enrich failed for {record.get('display_name')}: {exc})")
        return None
    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_text(json.dumps(profile, indent=2))
    return profile


def make_connector():
    from packages.config.settings import get_api_key
    from packages.prospecting.connectors.google_places import (
        GOOGLE_PLACES_API_KEY_ENV_VAR,
        GooglePlacesConnector,
    )

    if not get_api_key(GOOGLE_PLACES_API_KEY_ENV_VAR):
        return None
    return GooglePlacesConnector()


def _legacy_build(
    record: dict, out_dir: Path, target, account, profile
) -> tuple[object, str, list[str], dict | None]:
    from packages.agency.demo_theme import theme_for_record

    theme = theme_for_record(record)
    used = profile_fields_used(profile) if profile else []
    result = build_preview_for_record(
        record, out_dir, target=target, account=account, profile=profile
    )
    return result, "legacy-token-fill", used, theme.to_dict()


def _bespoke_deploy(
    record: dict, out_dir: Path, target, account
) -> tuple[PreviewResult, str, list[str], None]:
    dist_dir = resolve_prospect_dist_dir(out_dir)
    intake_from_record(record)  # validate early
    place_id = str(record.get("place_id", ""))
    if target is None:
        return (
            PreviewResult(
                place_id=place_id,
                site_name=PREVIEW_SITE_NAME,
                dist_dir=dist_dir,
                deployed=False,
            ),
            "bespoke",
            [],
            None,
        )
    result = deploy_preview_dist(record, dist_dir, target=target, account=account)
    return result, "bespoke", [], None


def main() -> None:
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sel = ap.add_argument_group("selection")
    sel.add_argument("--place-id", help="deploy for one specific record")
    sel.add_argument("--confirmed", action="store_true", help="all none_found leads")
    sel.add_argument("--verdict", help="all leads with this web_verify_verdict")
    sel.add_argument("--city", help="restrict to one city_id")
    sel.add_argument("--limit", type=int, default=0, help="cap the number of sites")
    sel.add_argument(
        "--order",
        choices=["city", "reviews"],
        default="city",
        help="selection order: 'city' (default) or 'reviews' (most Google reviews first)",
    )
    dep = ap.add_argument_group("deploy")
    dep.add_argument(
        "--deploy",
        action="store_true",
        help="publish to Netlify (needs $NETLIFY_AUTH_TOKEN)",
    )
    dep.add_argument("--account", help="your Netlify team/account slug to own the sites")
    dep.add_argument(
        "--deploy-delay",
        type=float,
        default=0.0,
        help="seconds to wait between deploys (Netlify rate-limits ~3/min; use 30 for big batches)",
    )
    batch = ap.add_argument_group("batch")
    batch.add_argument(
        "--batch",
        metavar="CSV_OR_GLOB",
        help=(
            "draft-deploy every place_id in a CSV (place_id column) or matching a "
            "sites/* glob (e.g. '*', 'ChIJ*'). Implies --deploy; idempotent — skips "
            "records that already have a mockup_url unless --force; continues past "
            "per-site failures and prints a summary. Default delay 20s between deploys."
        ),
    )
    batch.add_argument(
        "--force",
        action="store_true",
        help="with --batch, re-deploy place_ids that already have a mockup_url",
    )
    batch.add_argument(
        "--cleanup-drafts",
        action="store_true",
        help=(
            "list, confirm, then delete draft deploys for lost/suppressed prospects "
            "and clear their record URLs (lists before deleting; needs confirmation)"
        ),
    )
    leg = ap.add_argument_group("legacy (deprecated)")
    leg.add_argument(
        "--legacy-build",
        action="store_true",
        help=(
            "DEPRECATED (web build path A): generate token-fill dist/ via "
            "render_landing_html. Bulk regeneration only — NOT for client-facing "
            "mockups. Use the bespoke playbook (docs/demo-site-build-playbook.md "
            "→ dist-v2/); deployed prospect sites require dist-v2/."
        ),
    )
    enr = ap.add_argument_group("enrichment (legacy-build only)")
    enr.add_argument(
        "--no-enrich",
        action="store_true",
        help="skip Google Places Details when using --legacy-build",
    )
    args = ap.parse_args()

    if args.cleanup_drafts:
        cleanup_drafts(args)
        return

    # --batch is a deploy command over a resolved place_id list; it implies
    # --deploy and skips already-deployed records unless --force.
    if args.batch:
        args.deploy = True
        records = select_batch_records(args.batch)
    else:
        records = select_records(args)
    if not records:
        print("no matching records.")
        return

    target = account = None
    if args.deploy:
        target, account = make_target(args.account)
    connector = None if args.no_enrich else make_connector()
    # Netlify rate-limits ~3 deploys/min; default a batch to a 20s spacing.
    deploy_delay = args.deploy_delay or (20.0 if args.batch else 0.0)

    mode = "LEGACY BUILD" if args.legacy_build else "DEPLOY"
    label = "BATCH " + mode if args.batch else mode
    print(f"{label}{' + NETLIFY' if args.deploy else ''} — {len(records)} prospect site(s)\n")
    if not args.legacy_build:
        print("Requires dist-v2/ from docs/demo-site-build-playbook.md\n")

    summary = []
    for i, rec in enumerate(records):
        place_id = str(rec.get("place_id", ""))
        name = rec.get("display_name", "?")
        out_dir = SITES_DIR / place_id

        # Idempotent resume: a batch re-run is a no-op over already-deployed
        # records unless --force. (Single/verdict selections deploy as before.)
        if args.batch and not args.force and str(rec.get("mockup_url", "")).strip():
            print(f"  ⤳ {name}: already deployed (skip; --force to redeploy)")
            summary.append((name, "skipped", str(rec.get("mockup_url", ""))))
            continue

        try:
            if args.legacy_build:
                profile = None if args.no_enrich else get_profile(rec, connector)
                result, build_kind, used, theme_dict = _legacy_build(
                    rec, out_dir, target, account, profile
                )
            else:
                result, build_kind, used, theme_dict = _bespoke_deploy(
                    rec, out_dir, target, account
                )
        except ScaffoldCopyError as exc:
            # Built, but still carries scaffold/placeholder copy — blocked at the
            # deploy gate. Distinct from no-build so the operator knows to rewrite.
            print(f"  ⚑ {name}: scaffold copy — not deployed (rewrite per playbook)")
            summary.append((name, "scaffold", str(exc)))
            continue
        except ProspectBuildError as exc:
            # No dist-v2 build yet — distinct from a hard failure so the batch
            # summary can separate "not built yet" from "deploy errored".
            print(f"  ⊘ {name}: {exc}")
            summary.append((name, "no-build", str(exc)))
            continue
        except Exception as exc:  # noqa: BLE001  (ValueError + transport/API errors)
            print(f"  ✗ {name}: {exc}")
            summary.append((name, "error", str(exc)))
            continue

        mockup_url = getattr(result, "mockup_url", "") or ""
        draft = render_outreach_draft(rec, mockup_url)
        if draft:
            (out_dir / "outreach-with-mockup.md").write_text(draft)

        preview_payload: dict = {
            "place_id": place_id,
            "business": name,
            "build_kind": build_kind,
            "deployed": result.deployed,
            "mockup_url": mockup_url,
            "dist": str(result.dist_dir),
            "enriched": bool(used),
            "places_fields_used": used,
        }
        if theme_dict:
            preview_payload["theme"] = theme_dict
        if build_kind == "bespoke":
            try:
                intake = intake_from_record(rec)
                preview_payload["city"] = intake.city
                preview_payload["category"] = intake.service_category
            except ValueError:
                pass
        (out_dir / "preview.json").write_text(json.dumps(preview_payload, indent=2))

        tag = f"  [{build_kind}]"
        if used:
            tag += f"  [places: {', '.join(used)}]"
        if result.deployed:
            write_record_mockup_fields(place_id, result)
            print(f"  ✓ {name}  →  {mockup_url}{tag}")
            summary.append((name, "deployed", mockup_url))
        else:
            index = result.dist_dir / "index.html"
            print(f"  ✓ {name}  →  {index}{tag}")
            summary.append((name, "ready", str(index)))

        if result.deployed and deploy_delay and i < len(records) - 1:
            time.sleep(deploy_delay)

    counts = Counter(status for _, status, _ in summary)
    print("\nSummary:")
    for status in ("deployed", "ready", "skipped", "no-build", "scaffold", "error"):
        if counts.get(status):
            print(f"  {status:<9} {counts[status]}")
    failures = [(n, d) for n, s, d in summary if s in ("error", "no-build", "scaffold")]
    if failures:
        print("\nNeeds attention:")
        for name, detail in failures:
            print(f"  - {name}: {detail}")
    if not args.deploy and counts.get("ready"):
        print("\nTip: review on localhost (preview_site.py), then re-run with --deploy.")


if __name__ == "__main__":
    main()
