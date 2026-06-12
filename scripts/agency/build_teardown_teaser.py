#!/usr/bin/env python3
"""Teardown-teaser lane (item 7) — the owned-site flip.

Turns ``owned_site`` prospects (the 61% majority dropped for already having a
website) into a one-page Conversion-Audit teaser: a light persona-panel pass over
their *existing* homepage, distilled to the top-3 conversion blockers, rendered as
a teaser + annotated card + a ``variant=teaser`` outreach draft that pitches the
paid Conversion Audit (not a rebuild).

Conversion Lab has no autonomous LLM client (it's prepare -> fill reviews ->
render), so this mirrors that contract with two subcommands and an agent in the
middle:

    # 1. select cohort, capture homepages, write the persona prompts
    python scripts/agency/build_teardown_teaser.py prepare --limit 50

    # 2. (agent) read each teaser/PROMPTS.md, write teaser/reviews.json +
    #    teaser/findings.json for that prospect

    # 3. validate findings, render teaser.md + card + draft, flag into the lane
    python scripts/agency/build_teardown_teaser.py finish --all

    # 4. surface in the dashboard
    python scripts/agency/outreach_lane.py refresh

Guardrail: ``finish`` runs the no-invented-findings gate — every finding's
evidence quote must appear verbatim in the persona it cites, or the teaser is
skipped (never shipped).
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from packages.agency.teardown_teaser import (  # noqa: E402
    FindingValidationError,
    TeaserFinding,
    TeaserProspect,
    build_teaser_data,
    load_offer,
    prepare_prompts,
    render_teaser_card_html,
    render_teaser_markdown,
    render_teaser_outreach_markdown,
    select_cohort,
    validate_findings,
)
from packages.schemas.conversion_lab import PersonaReview  # noqa: E402

RECORDS_DIR = REPO / "state" / "prospects" / "records"
SITES_DIR = REPO / "state" / "prospects" / "sites"
SHOOT_URL = REPO / "scripts" / "web" / "shoot_url.mjs"
CARD_TO_PNG = REPO / "scripts" / "web" / "card_to_png.mjs"
MIN_PAGE_COPY_CHARS = 120


# --------------------------------------------------------------------- records
def _load_record_paths() -> list[tuple[Path, dict]]:
    out: list[tuple[Path, dict]] = []
    for path in sorted(RECORDS_DIR.glob("*.json")):
        try:
            record = json.loads(path.read_text())
        except (OSError, ValueError):
            continue
        if isinstance(record, dict):
            out.append((path, record))
    return out


def _path_by_place_id(records: list[tuple[Path, dict]]) -> dict[str, Path]:
    return {str(rec.get("place_id", "")): path for path, rec in records if rec.get("place_id")}


def _site_dir(place_id: str) -> Path:
    return SITES_DIR / place_id


def _teaser_dir(place_id: str) -> Path:
    return _site_dir(place_id) / "teaser"


# --------------------------------------------------------------------- prepare
def _capture_homepage(prospect: TeaserProspect, teaser_dir: Path) -> str | None:
    """Screenshot + extract the live homepage; returns page_copy or None on fail."""
    teaser_dir.mkdir(parents=True, exist_ok=True)
    result = subprocess.run(
        ["node", str(SHOOT_URL), prospect.site_url, str(teaser_dir), "--name", "homepage"],
        capture_output=True,
        text=True,
    )
    txt = teaser_dir / "homepage.txt"
    if result.returncode != 0 or not txt.exists():
        print(f"  ! capture failed: {result.stderr.strip().splitlines()[-1:] or ''}")
        return None
    page_copy = txt.read_text(encoding="utf-8").strip()
    if len(page_copy) < MIN_PAGE_COPY_CHARS:
        print(f"  ! homepage text too thin ({len(page_copy)} chars), skipping")
        return None
    return page_copy


def _scaffold(teaser_dir: Path, persona_ids: list[str]) -> None:
    """Write empty reviews/findings templates for the agent to fill."""
    reviews_tpl = [
        {
            "persona_id": pid,
            "likely_action": "",
            "clarity_notes": [],
            "objections": [],
            "trust_gaps": [],
            "useful_rewrites": [],
            "confidence": "medium",
        }
        for pid in persona_ids
    ]
    findings_tpl = {
        "findings": [
            {"title": "", "evidence_quote": "", "persona_id": pid, "recommendation": ""}
            for pid in persona_ids[:3]
        ]
    }
    (teaser_dir / "reviews.template.json").write_text(json.dumps(reviews_tpl, indent=2) + "\n")
    (teaser_dir / "findings.template.json").write_text(json.dumps(findings_tpl, indent=2) + "\n")


def cmd_prepare(args: argparse.Namespace) -> int:
    records = _load_record_paths()
    cohort = select_cohort(
        [rec for _path, rec in records],
        limit=args.limit,
        min_reviews=args.min_reviews,
    )
    if args.place_id:
        cohort = [p for p in cohort if p.place_id == args.place_id]
    if not cohort:
        print("no eligible owned_site prospects matched.")
        return 1

    prepared: list[dict] = []
    for prospect in cohort:
        print(f"• {prospect.business_name}  ({prospect.review_count} reviews)")
        print(f"  {prospect.site_url}")
        teaser_dir = _teaser_dir(prospect.place_id)
        page_copy = ""
        if args.no_capture:
            txt = teaser_dir / "homepage.txt"
            page_copy = txt.read_text(encoding="utf-8").strip() if txt.exists() else ""
            if len(page_copy) < MIN_PAGE_COPY_CHARS:
                print("  ! --no-capture but no saved homepage.txt, skipping")
                continue
        else:
            captured = _capture_homepage(prospect, teaser_dir)
            if captured is None:
                continue
            page_copy = captured

        payload, prompts_md, persona_ids = prepare_prompts(
            prospect, page_copy, panel_size=args.panel_size
        )
        teaser_dir.mkdir(parents=True, exist_ok=True)
        (teaser_dir / "INPUT.json").write_text(json.dumps(payload.to_dict(), indent=2) + "\n")
        (teaser_dir / "PROMPTS.md").write_text(prompts_md)
        _scaffold(teaser_dir, persona_ids)
        prepared.append(
            {
                "place_id": prospect.place_id,
                "business_name": prospect.business_name,
                "site_url": prospect.site_url,
                "prompts": str((teaser_dir / "PROMPTS.md").relative_to(REPO)),
                "reviews": str((teaser_dir / "reviews.json").relative_to(REPO)),
                "findings": str((teaser_dir / "findings.json").relative_to(REPO)),
            }
        )
        print(f"  ✓ prompts → {teaser_dir.relative_to(REPO)}/PROMPTS.md")

    manifest = SITES_DIR.parent / "teaser-lane" / "teaser-cohort.json"
    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_text(json.dumps({"prepared": prepared}, indent=2) + "\n")
    print(f"\nprepared {len(prepared)} teaser(s). Manifest: {manifest.relative_to(REPO)}")
    print("Next: fill each teaser/reviews.json + teaser/findings.json, then run `finish`.")
    return 0


# --------------------------------------------------------------------- finish
def _load_reviews(teaser_dir: Path) -> list[PersonaReview]:
    payload = json.loads((teaser_dir / "reviews.json").read_text())
    return [PersonaReview.from_dict(item) for item in payload]


def _load_findings(teaser_dir: Path) -> list[TeaserFinding]:
    payload = json.loads((teaser_dir / "findings.json").read_text())
    items = payload.get("findings", payload) if isinstance(payload, dict) else payload
    return [TeaserFinding.from_dict(item) for item in items]


def _render_card_png(
    site_dir: Path, prospect: TeaserProspect, findings: list[TeaserFinding]
) -> bool:
    """Write the annotated card HTML and rasterize it via card_to_png.mjs."""
    homepage_png = site_dir / "teaser" / "homepage.png"
    if not homepage_png.exists():
        print("  ! no homepage.png; skipping card image")
        return False
    card_html = site_dir / "teaser-card.html"
    card_html.write_text(
        render_teaser_card_html(prospect, findings, homepage_image="teaser/homepage.png")
    )
    result = subprocess.run(
        ["node", str(CARD_TO_PNG), str(card_html), str(site_dir / "teaser-card.png")],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(f"  ! card render failed: {result.stderr.strip().splitlines()[-1:] or ''}")
        return False
    return True


def _flag_record(record_path: Path) -> None:
    record = json.loads(record_path.read_text())
    if not record.get("teaser_lane"):
        record["teaser_lane"] = True
        record_path.write_text(json.dumps(record, indent=2) + "\n")


def _finish_one(prospect: TeaserProspect, record_path: Path, offer) -> bool:
    site_dir = _site_dir(prospect.place_id)
    teaser_dir = _teaser_dir(prospect.place_id)
    if not (teaser_dir / "reviews.json").exists() or not (teaser_dir / "findings.json").exists():
        print("  ! missing reviews.json or findings.json; fill them first")
        return False
    reviews = _load_reviews(teaser_dir)
    findings = _load_findings(teaser_dir)
    try:
        validate_findings(findings, reviews)
    except FindingValidationError as exc:
        print(f"  ✗ guardrail: {exc}")
        return False

    persona_ids = [r.persona_id for r in reviews]
    site_dir.mkdir(parents=True, exist_ok=True)
    (site_dir / "teaser.json").write_text(
        json.dumps(build_teaser_data(prospect, findings, offer, persona_ids=persona_ids), indent=2)
        + "\n"
    )
    (site_dir / "teaser.md").write_text(render_teaser_markdown(prospect, findings, offer))
    (site_dir / "outreach-teaser.md").write_text(
        render_teaser_outreach_markdown(prospect, findings, offer)
    )
    _render_card_png(site_dir, prospect, findings)
    _flag_record(record_path)
    print(f"  ✓ teaser.md + card + draft → {site_dir.relative_to(REPO)}")
    return True


def cmd_finish(args: argparse.Namespace) -> int:
    records = _load_record_paths()
    by_id = _path_by_place_id(records)
    cohort = select_cohort([rec for _path, rec in records], min_reviews=0)
    by_place = {p.place_id: p for p in cohort}

    if args.place_id:
        targets = [args.place_id]
    else:
        # Every prepared prospect that now has filled reviews + findings.
        targets = [
            pid
            for pid in by_place
            if (_teaser_dir(pid) / "reviews.json").exists()
            and (_teaser_dir(pid) / "findings.json").exists()
        ]
    if not targets:
        print("nothing to finish — no prospect has both reviews.json and findings.json yet.")
        return 1

    offer = load_offer()
    ok = 0
    for pid in targets:
        prospect = by_place.get(pid)
        record_path = by_id.get(pid)
        if prospect is None or record_path is None:
            print(f"• {pid}\n  ! not an eligible owned_site record; skipping")
            continue
        print(f"• {prospect.business_name}")
        if _finish_one(prospect, record_path, offer):
            ok += 1
    print(f"\nfinished {ok}/{len(targets)} teaser(s).")
    print("Next: `python scripts/agency/outreach_lane.py refresh` to surface them.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("prepare", help="select cohort, capture homepages, write persona prompts")
    p.add_argument("--limit", type=int, default=50, help="max prospects (by review count)")
    p.add_argument("--min-reviews", type=int, default=1, help="skip below this review count")
    p.add_argument("--place-id", help="restrict to one prospect (must be in the cohort)")
    p.add_argument("--panel-size", type=int, default=3, help="personas in the light panel")
    p.add_argument("--no-capture", action="store_true", help="reuse saved homepage.txt")
    p.set_defaults(func=cmd_prepare)

    f = sub.add_parser("finish", help="validate findings, render teaser + card + draft")
    f.add_argument("--all", action="store_true", help="finish every prepared+filled prospect")
    f.add_argument("--place-id", help="finish one prospect")
    f.set_defaults(func=cmd_finish)

    args = parser.parse_args()
    if args.command == "finish" and not args.all and not args.place_id:
        parser.error("finish: pass --all or --place-id <PID>")
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
