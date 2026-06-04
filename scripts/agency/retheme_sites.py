#!/usr/bin/env python3
"""Re-generate legacy token-fill ``dist/`` previews (deprecated).

Customer-facing mockups use ``dist-v2/`` per ``docs/demo-site-build-playbook.md``.
This script only updates old ``dist/`` builds for bulk experiments.

Re-render already-built prospect demo sites with the current demo theme.

Offline + free: for every site under ``state/prospects/sites/<place_id>/`` that
already has a ``preview.json``, this reloads the warehouse record and the
*cached* Places profile (``places-profile.json``) and re-renders
``dist/index.html`` with the deterministic per-business theme (palette + font +
layout). It never calls the network, so no Places billing — re-run any time the
theming engine changes.

It does NOT re-deploy. Deploying refreshed demos stays a separate, gated step
(build -> preview -> approve -> production).

    python scripts/agency/retheme_sites.py            # all built sites
    python scripts/agency/retheme_sites.py --limit 5  # first 5 (spot-check)
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from packages.agency.demo_theme import theme_for_record  # noqa: E402
from packages.agency.prospect_site import render_preview_html  # noqa: E402

SITES_DIR = REPO / "state" / "prospects" / "sites"
RECORDS_DIR = REPO / "state" / "prospects" / "records"


def _load(path: Path) -> dict | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--limit", type=int, default=0, help="only re-render the first N sites")
    args = ap.parse_args()

    site_dirs = sorted(d for d in SITES_DIR.glob("*") if (d / "preview.json").is_file())
    if args.limit:
        site_dirs = site_dirs[: args.limit]

    ok = skipped = failed = 0
    for d in site_dirs:
        place_id = d.name
        record = _load(RECORDS_DIR / f"{place_id}.json")
        if record is None:
            print(f"  ⊘ {place_id}: no warehouse record")
            skipped += 1
            continue
        profile = _load(d / "places-profile.json")  # cached; may be None
        try:
            html = render_preview_html(record, profile)
        except Exception as exc:  # noqa: BLE001 — report per-site, keep going
            print(f"  ✗ {place_id}: {exc}")
            failed += 1
            continue

        (d / "dist").mkdir(exist_ok=True)
        (d / "dist" / "index.html").write_text(html, encoding="utf-8")

        preview = _load(d / "preview.json") or {}
        preview["theme"] = theme_for_record(record).to_dict()
        (d / "preview.json").write_text(json.dumps(preview, indent=2), encoding="utf-8")
        ok += 1

    print(f"\nRe-themed {ok} site(s). skipped={skipped} failed={failed}")
    print("Review a dist/index.html in a browser; deploy is a separate gated step.")


if __name__ == "__main__":
    main()
