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
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from packages.agency.prospect_site import (  # noqa: E402
    GENRE_PROFILES,
    PREVIEW_SITE_NAME,
    PreviewResult,
    ProspectBuildError,
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

    records = select_records(args)
    if not records:
        print("no matching records.")
        return

    target = account = None
    if args.deploy:
        target, account = make_target(args.account)
    connector = None if args.no_enrich else make_connector()

    mode = "LEGACY BUILD" if args.legacy_build else "DEPLOY"
    print(f"{mode}{' + NETLIFY' if args.deploy else ''} — {len(records)} prospect site(s)\n")
    if not args.legacy_build:
        print("Requires dist-v2/ from docs/demo-site-build-playbook.md\n")

    summary = []
    for i, rec in enumerate(records):
        place_id = str(rec.get("place_id", ""))
        name = rec.get("display_name", "?")
        out_dir = SITES_DIR / place_id
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
        except (ProspectBuildError, ValueError) as exc:
            print(f"  ✗ {name}: {exc}")
            summary.append((name, "error", str(exc)))
            continue
        except Exception as exc:  # noqa: BLE001
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

        if result.deployed and args.deploy_delay and i < len(records) - 1:
            time.sleep(args.deploy_delay)

    ok = sum(1 for _, s, _ in summary if s in ("ready", "deployed"))
    print(f"\nDone. {ok}/{len(records)} ok.")
    if not args.deploy and ok:
        print("Tip: review on localhost (preview_site.py), then re-run with --deploy.")


if __name__ == "__main__":
    main()
