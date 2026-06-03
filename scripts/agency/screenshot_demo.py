#!/usr/bin/env python3
"""Full-page screenshot of a demo build — the mandatory pre-Netlify review step.

Captures the LATEST LOCAL build (served on localhost by the capture engine) top to
bottom, in one full-page image. Keeps every iteration in the business's own
screenshots/ folder, and mirrors the newest into a single flat REVIEW GALLERY so a
whole batch of businesses can be eyeballed from one folder before anything ships.

Engine: scripts/web/shoot.mjs (Playwright/Chromium full-page, reduced-motion so
scroll-reveal content is fully visible). It serves the dist on localhost itself —
no Netlify needed.

USAGE
-----
  python scripts/agency/screenshot_demo.py --place-id <PID> [--label pre-deploy]
  python scripts/agency/screenshot_demo.py --all [--label nightly]   # all bespoke (dist-v2) demos

Outputs per business:
  state/prospects/sites/<PID>/screenshots/<slug>-<label>.png   (iteration history)
  state/prospects/sites/<PID>/screenshots/<slug>-latest.png    (newest)
Central review folder (one current PNG per business):
  state/prospects/review-gallery/<slug>.png
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SITES = REPO / "state" / "prospects" / "sites"
GALLERY = REPO / "state" / "prospects" / "review-gallery"
SHOOT = REPO / "scripts" / "web" / "shoot.mjs"


def slugify(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-") or "site"


def dist_for(pid_dir: Path, bespoke_only: bool = False) -> Path | None:
    if (pid_dir / "dist-v2" / "index.html").exists():
        return pid_dir / "dist-v2"
    if not bespoke_only and (pid_dir / "dist" / "index.html").exists():
        return pid_dir / "dist"
    return None


def record_name(pid: str) -> tuple[str, str]:
    f = REPO / "state" / "prospects" / "records" / f"{pid}.json"
    if f.exists():
        r = json.loads(f.read_text())
        return r.get("display_name", pid), r.get("city_id", "")
    return pid, ""


def targets(args) -> list[Path]:
    if args.place_id:
        d = SITES / args.place_id
        return [d] if dist_for(d) else []
    # --all: only bespoke (dist-v2) demos, so we don't re-shoot stale template builds
    return [p for p in sorted(SITES.iterdir())
            if p.is_dir() and not p.name.startswith("_") and dist_for(p, bespoke_only=True)]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--place-id", help="screenshot one business's build")
    ap.add_argument("--all", action="store_true", help="screenshot all bespoke (dist-v2) demos")
    ap.add_argument("--label", default="", help="iteration label (default: UTC timestamp)")
    args = ap.parse_args()
    if not args.place_id and not args.all:
        sys.exit("pass --place-id <PID> or --all")

    label = args.label or datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    GALLERY.mkdir(parents=True, exist_ok=True)
    chosen = targets(args)
    if not chosen:
        print("no built demos found.")
        return

    print(f"Full-page screenshots — {len(chosen)} demo(s)  ·  label '{label}'")
    print(f"Review gallery: {GALLERY.relative_to(REPO)}\n")
    ok = 0
    for pid_dir in chosen:
        pid = pid_dir.name
        dist = dist_for(pid_dir)
        name, city = record_name(pid)
        slug = slugify(name) + (f"-{city}" if city else "")
        shots = pid_dir / "screenshots"
        shots.mkdir(exist_ok=True)
        route = f"/:{slug}-{label}"
        r = subprocess.run(["node", str(SHOOT), str(dist), str(shots), route],
                           capture_output=True, text=True)
        produced = shots / f"{slug}-{label}.png"
        if r.returncode != 0 or not produced.exists():
            print(f"  ✗ {name[:34]:35} {(r.stderr or r.stdout).strip()[:100] or 'shoot failed'}")
            continue
        shutil.copy(produced, shots / f"{slug}-latest.png")
        shutil.copy(produced, GALLERY / f"{slug}.png")
        ok += 1
        print(f"  ✓ {name[:34]:35} {produced.stat().st_size // 1024:>5}KB  → review-gallery/{slug}.png")

    print(f"\n{ok}/{len(chosen)} captured. Review them all in one place:")
    print(f"  open {GALLERY.relative_to(REPO)}")
    print("Tip: to click through a build live, run preview_site.py and open localhost.")


if __name__ == "__main__":
    main()
