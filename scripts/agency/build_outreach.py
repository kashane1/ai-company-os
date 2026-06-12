#!/usr/bin/env python3
"""Generate per-prospect outreach copy for every lead that has a live preview site.

For each warehouse record with a ``mockup_url`` (i.e. we built them a website),
this fills the channel templates under ``state/prospects/outreach/`` with that
lead's real data + the right genre/verdict snippet, and writes:

  - ``state/prospects/sites/<place_id>/outreach.md``: all channels, ready to send
  - ``state/prospects/audited/outreach-index-<date>.csv``: one row per prospect

Channels rendered: SMS/text (primary because phone is the only contact we store), a
phone-call opener, the with-mockup email, and an IG/FB DM (for when a handle is
found). Nothing sends; these are drafts the operator personalizes by hand.

USAGE
-----
    python scripts/agency/build_outreach.py                 # all leads with a site
    python scripts/agency/build_outreach.py --verdict marketplace_only
    python scripts/agency/build_outreach.py --verdict none_found
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from packages.agency.outreach import (  # noqa: E402
    context_for,
    gap_ref_for,
    parse_snippets,
    recommended_channel,
    render_template,
    sanitize_outreach_copy,
    unfilled_placeholders,
)
from packages.agency.outreach_messages import build_messages_from_context  # noqa: E402
from packages.agency.outreach_sequencer import MAX_TOUCHES, observation_for_step  # noqa: E402

RECORDS_DIR = REPO / "state" / "prospects" / "records"
SITES_DIR = REPO / "state" / "prospects" / "sites"
OUTREACH_DIR = REPO / "state" / "prospects" / "outreach"
AUDITED_DIR = REPO / "state" / "prospects" / "audited"

TEMPLATES = {
    "sms": OUTREACH_DIR / "sms" / "base.md",
    "email_with_mockup": OUTREACH_DIR / "email" / "with-mockup.md",
    "instagram_dm": OUTREACH_DIR / "instagram_dm" / "base.md",
    "facebook_dm": OUTREACH_DIR / "facebook_dm" / "base.md",
}
DATE = "2026-06-02"


def load_records(args) -> list[dict]:
    recs = []
    for f in sorted(RECORDS_DIR.glob("*.json")):
        try:
            r = json.loads(f.read_text())
        except (ValueError, OSError):
            continue
        if not r.get("mockup_url"):
            continue
        if args.verdict and r.get("web_verify_verdict") != args.verdict:
            continue
        recs.append(r)
    recs.sort(key=lambda r: -(r.get("user_ratings_total") or 0))
    return recs


def _strip_template_header(body: str) -> str:
    """Drop the leading explanatory section above the first '---' divider."""
    return body.split("\n---\n", 1)[-1].strip() if "\n---\n" in body else body.strip()


def render_prospect(record: dict, snippets, templates: dict[str, str]) -> str:
    ctx = context_for(record, snippets)
    phone = record.get("phone", "")
    channels = []
    if phone:
        channels.append(f"phone {phone}")
    if ctx.email:
        channels.append(f"email {ctx.email}")
    if ctx.instagram:
        channels.append(f"IG {ctx.instagram}")
    if ctx.facebook:
        channels.append(f"FB {ctx.facebook}")
    if ctx.booking_url:
        channels.append(f"booking {ctx.booking_url}")
    parts = [
        f"# Outreach: {ctx.business_name}",
        "",
        f"- **City:** {ctx.city}  |  **Type:** {ctx.genre_noun}  "
        f"|  **Reviews:** {record.get('user_ratings_total') or 'n/a'}",
        f"- **Verdict:** {record.get('web_verify_verdict')}  "
        f"(gap angle: `{gap_ref_for(record)}`)",
        f"- **Contacts found:** {'  |  '.join(channels) if channels else 'none yet'}",
        f"- **Recommended first touch:** **{recommended_channel(record)}**",
        f"- **Preview site:** {ctx.mockup_url}",
        "",
    ]
    if ctx.owned_website:
        parts += [
            f"> ⚠️ **RECHECK before contacting:** this business appears to already have an "
            f"owned website ({ctx.owned_website}). The no-website pitch may not apply. "
            f"Verify, and consider dropping or re-angling.",
            "",
        ]
    parts += [
        "> Draft only. Personalize at least one line, then send by hand. "
        "Do not claim the site is published. It is a private preview built for them.",
        "",
        "## Text / SMS",
        _strip_template_header(templates["sms"]),
        "",
        "## Phone call opener",
        _phone_script(ctx),
        "",
        "## Email with mockup",
        _strip_template_header(templates["email_with_mockup"]),
        "",
        "## DM, Instagram / Facebook",
        "**Instagram:**",
        _strip_template_header(templates["instagram_dm"]),
        "",
        "**Facebook:**",
        _strip_template_header(templates["facebook_dm"]),
        "",
    ]
    parts += _follow_up_sequence(record, ctx)
    body = "\n".join(parts)
    return sanitize_outreach_copy(render_template(body, ctx))


def _follow_up_sequence(record: dict, ctx) -> list[str]:
    """Touch-2/touch-3 follow-up drafts, matching what the dashboard surfaces.

    Same per-step cadence story as ``outreach_sequencer``: send these only if the
    earlier touch got no reply (a reply/suppression retires the sequence)."""
    place_id = str(record.get("place_id", ""))
    lines = [
        "## Follow-up sequence (only if no reply)",
        "",
        "_Touch 2 is due ~4 days after touch 1, touch 3 ~8 days after touch 2. "
        "Stop after 3. A reply or suppression cancels these._",
        "",
    ]
    for step in range(2, MAX_TOUCHES + 1):
        observation = observation_for_step(place_id, step, ctx, sites_root=SITES_DIR)
        messages = build_messages_from_context(ctx, step=step, observation=observation)
        lines += [
            f"### Touch {step}",
            "",
            f"**Email subject:** {messages.email_subject}",
            "",
            messages.email_body,
            "",
            "**SMS:**",
            "",
            messages.sms_body,
            "",
        ]
    return lines


def _phone_script(ctx) -> str:
    return (
        f"\"Hi, is this the owner? My name is {{sender_name}}. "
        f"I found {ctx.business_name} while looking up {ctx.search_phrase} in {ctx.city}. "
        f"I made a website preview for you. "
        f"Can I text you the link? No obligation, I just thought it might be useful.\""
    )


def main() -> None:
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument(
        "--verdict",
        help="restrict to one web_verify_verdict (e.g. marketplace_only, none_found)",
    )
    args = ap.parse_args()

    missing = [k for k, p in TEMPLATES.items() if not p.exists()]
    if missing:
        sys.exit(f"missing templates: {missing}")
    templates = {k: p.read_text() for k, p in TEMPLATES.items()}
    snippets = parse_snippets((OUTREACH_DIR / "genre-snippets.md").read_text())

    records = load_records(args)
    if not records:
        print("no records with a mockup_url match.")
        return

    AUDITED_DIR.mkdir(parents=True, exist_ok=True)
    index_path = AUDITED_DIR / f"outreach-index-{DATE}.csv"
    cols = ["display_name", "city_id", "genre_id", "web_verify_verdict",
            "user_ratings_total", "recommended_channel", "phone", "contact_email",
            "contact_instagram", "contact_facebook", "contact_booking_url",
            "contact_owned_website", "mockup_url", "outreach_file"]

    print(f"Outreach copy: {len(records)} prospect(s) with a live site\n")
    rows = []
    flagged = 0
    for r in records:
        place_id = str(r.get("place_id", ""))
        doc = render_prospect(r, snippets, templates)
        leftover = unfilled_placeholders(doc)
        if leftover:
            flagged += 1
            print(f"  ! {r.get('display_name')}: unfilled {leftover}")
        out_file = SITES_DIR / place_id / "outreach.md"
        out_file.parent.mkdir(parents=True, exist_ok=True)
        out_file.write_text(doc)
        rows.append({
            "display_name": r.get("display_name", ""),
            "city_id": r.get("city_id", ""),
            "genre_id": r.get("genre_id", ""),
            "web_verify_verdict": r.get("web_verify_verdict", ""),
            "user_ratings_total": r.get("user_ratings_total", ""),
            "recommended_channel": recommended_channel(r),
            "phone": r.get("phone", ""),
            "contact_email": r.get("contact_email", ""),
            "contact_instagram": r.get("contact_instagram", ""),
            "contact_facebook": r.get("contact_facebook", ""),
            "contact_booking_url": r.get("contact_booking_url", ""),
            "contact_owned_website": r.get("contact_owned_website", ""),
            "mockup_url": r.get("mockup_url", ""),
            "outreach_file": str(out_file.relative_to(REPO)),
        })
        print(f"  ✓ {r.get('display_name')[:38]:39} → {out_file.relative_to(REPO)}")

    with index_path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(rows)

    print(f"\nWrote {len(rows)} outreach docs + index: {index_path.relative_to(REPO)}")
    if flagged:
        print(f"WARNING: {flagged} docs had unfilled placeholders. Check above.")


if __name__ == "__main__":
    main()
