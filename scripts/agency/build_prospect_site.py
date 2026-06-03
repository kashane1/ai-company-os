#!/usr/bin/env python3
"""Build (and optionally deploy) preview websites for prospect leads.

Turns verified prospect records into one-page preview sites — the private
``{mockup_url}`` the ``email/with-mockup.md`` outreach template references.

USAGE
-----
Local build only (safe default — no network, no token needed):

    python scripts/agency/build_prospect_site.py --place-id ChIJ...
    python scripts/agency/build_prospect_site.py --confirmed          # the none_found leads
    python scripts/agency/build_prospect_site.py --verdict marketplace_only --limit 10

Deploy a *draft* (preview) to YOUR Netlify account (needs $NETLIFY_AUTH_TOKEN):

    NETLIFY_AUTH_TOKEN=... python scripts/agency/build_prospect_site.py \
        --confirmed --deploy --account <your-netlify-team-slug>

Outputs per lead go to ``state/prospects/sites/<place_id>/``:
  - dist/index.html            the built preview page
  - preview.json               build/deploy metadata
  - outreach-with-mockup.md    a personalized draft (draft only — never sent)

On a successful deploy the record in ``state/prospects/records/<place_id>.json``
gets ``mockup_url``, ``mockup_site_id``, ``mockup_deploy_id``, ``mockup_built_at``.

Preview/draft deploys are ungated by ``deploy_readiness`` policy; this script
NEVER does a production deploy.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from packages.agency.demo_theme import theme_for_record  # noqa: E402
from packages.agency.prospect_site import (  # noqa: E402
    GENRE_PROFILES,
    build_preview_for_record,
    city_label,
    intake_from_record,
    profile_fields_used,
)

RECORDS_DIR = REPO / "state" / "prospects" / "records"
SITES_DIR = REPO / "state" / "prospects" / "sites"
OUTREACH_TEMPLATE = REPO / "state" / "prospects" / "outreach" / "email" / "with-mockup.md"

# Fixtures that must never be treated as real leads.
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
        pool = [r for r in records if r.get("web_verify_verdict") == args.verdict and not _is_fixture(r)]
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
    """Fill the with-mockup email template with what we know (draft only)."""
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
        "{observed_gap}": "I couldn't find an owned website for you — just a phone number / directory listings.",
        "{review_count}": f"{reviews}+" if reviews else "your",
        "{mockup_url}": mockup_url or "[preview URL after deploy]",
        "{sender_name}": "[your name]",
        "{sender_company}": "[your company]",
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
    rec["mockup_built_at"] = "2026-06-02T00:00:00+00:00"
    path.write_text(json.dumps(rec, indent=2))


def make_target(account_slug: str | None):
    from packages.web.deploy import DeployAccount, NetlifyDeployTarget

    account = DeployAccount(id=account_slug) if account_slug else None
    return NetlifyDeployTarget(account=account), account


def get_profile(record: dict, connector, *, refresh: bool = False) -> dict | None:
    """Fetch (and cache) the Places profile for a record. Returns None on failure.

    Cached at ``state/prospects/sites/<place_id>/places-profile.json`` so re-runs
    never re-bill the Places API.
    """
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
    except Exception as exc:  # noqa: BLE001 — enrichment is best-effort
        print(f"    (enrich failed for {record.get('display_name')}: {exc})")
        return None
    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_text(json.dumps(profile, indent=2))
    return profile


def make_connector():
    """Build a Places connector if the API key is available, else None."""
    from packages.config.settings import get_api_key
    from packages.prospecting.connectors.google_places import (
        GOOGLE_PLACES_API_KEY_ENV_VAR,
        GooglePlacesConnector,
    )

    if not get_api_key(GOOGLE_PLACES_API_KEY_ENV_VAR):
        print("  (no $GOOGLE_PLACES_API_KEY — building with genre-default copy)")
        return None
    return GooglePlacesConnector()


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sel = ap.add_argument_group("selection")
    sel.add_argument("--place-id", help="build for one specific record")
    sel.add_argument("--confirmed", action="store_true", help="build for all none_found leads")
    sel.add_argument("--verdict", help="build for all leads with this web_verify_verdict")
    sel.add_argument("--city", help="restrict to one city_id")
    sel.add_argument("--limit", type=int, default=0, help="cap the number of sites")
    sel.add_argument(
        "--order",
        choices=["city", "reviews"],
        default="city",
        help="selection order: 'city' (default) or 'reviews' (most Google reviews first)",
    )
    dep = ap.add_argument_group("deploy")
    dep.add_argument("--deploy", action="store_true", help="publish to Netlify (needs $NETLIFY_AUTH_TOKEN)")
    dep.add_argument("--account", help="your Netlify team/account slug to own the sites")
    dep.add_argument(
        "--deploy-delay",
        type=float,
        default=0.0,
        help="seconds to wait between deploys (Netlify rate-limits ~3/min; use 30 for big batches)",
    )
    enr = ap.add_argument_group("enrichment")
    enr.add_argument(
        "--no-enrich",
        action="store_true",
        help="skip the Google Places Details call (use genre-default copy only). "
        "By default real Places data (hours, summary, location, rating) is used.",
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

    print(f"{'DEPLOY' if args.deploy else 'BUILD'} — {len(records)} preview site(s)\n")
    summary = []
    for i, rec in enumerate(records):
        place_id = str(rec.get("place_id", ""))
        name = rec.get("display_name", "?")
        out_dir = SITES_DIR / place_id
        try:
            intake = intake_from_record(rec)  # validates early
            theme = theme_for_record(rec)
            profile = None if args.no_enrich else get_profile(rec, connector)
            used = profile_fields_used(profile) if profile else []
            result = build_preview_for_record(
                rec, out_dir, target=target, account=account, profile=profile
            )
        except Exception as exc:  # noqa: BLE001 — report per-lead, keep going
            print(f"  ✗ {name}: {exc}")
            summary.append((name, "error", str(exc)))
            continue

        draft = render_outreach_draft(rec, result.mockup_url)
        if draft:
            (out_dir / "outreach-with-mockup.md").write_text(draft)
        (out_dir / "preview.json").write_text(
            json.dumps(
                {
                    "place_id": place_id,
                    "business": name,
                    "city": intake.city,
                    "category": intake.service_category,
                    "site_name": result.site_name,
                    "deployed": result.deployed,
                    "mockup_url": result.mockup_url,
                    "dist": str(result.dist_dir),
                    "enriched": bool(used),
                    "places_fields_used": used,
                    "theme": theme.to_dict(),
                },
                indent=2,
            )
        )
        tag = f"  [real: {', '.join(used)}]" if used else "  [genre-default copy]"
        if result.deployed:
            write_record_mockup_fields(place_id, result)
            print(f"  ✓ {name}  →  {result.mockup_url}{tag}")
            summary.append((name, "deployed", result.mockup_url))
        else:
            print(f"  ✓ {name}  →  {result.dist_dir / 'index.html'}{tag}")
            summary.append((name, "built", str(result.dist_dir / "index.html")))

        # Space out deploys so we don't trip Netlify's ~3/min deploy rate limit.
        if result.deployed and args.deploy_delay and i < len(records) - 1:
            time.sleep(args.deploy_delay)

    print(f"\nDone. {sum(1 for _, s, _ in summary if s in ('built', 'deployed'))}/{len(records)} ok.")
    if not args.deploy:
        print("Tip: open a dist/index.html in a browser to review, then re-run with --deploy.")


if __name__ == "__main__":
    main()
