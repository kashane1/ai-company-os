#!/usr/bin/env python3
"""Mood-board generator — the one-page brand artifact (brief + sales asset).

Assembles a genre kit's palette + type + 6–9 on-brief images into a single self-
contained HTML page. Two jobs at once: the internal build brief, and a client-facing
artifact you can send to a prospect to **sell the vision before building the site**.

  build --slug <kit> [--place-id PID] [--build-hub DIR] [--business-name NAME]
        [--concept TEXT] [--want N] [--out DIR] [--shoot] [--deploy --account SLUG]

Images are layered **business-first**: a real build's imagery (``--build-hub`` or, with
``--place-id``, the prospect site hub) takes priority, and the kit's exemplars fill the
grid. A recipe-only kit with no exemplars still renders (palette + type + direction) —
imagery arrives once it's harvested.

Preview locally (never auto-deployed):
    python scripts/agency/preview_site.py --dir <out>
Screenshot to a sales PNG: pass ``--shoot`` (Playwright via scripts/web/shoot.mjs).
Deploy a private draft (needs ``$NETLIFY_AUTH_TOKEN``): pass ``--deploy``; the draft
permalink is written back to the record as ``moodboard_url`` (mirrors ``mockup_url``).
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from dataclasses import asdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from packages.web.art_direction import list_kits, load_kit  # noqa: E402
from packages.web.imagery import ImageryManifest  # noqa: E402
from packages.web.moodboard import (  # noqa: E402
    collect_images,
    moodboard_from_kit,
    render_moodboard_html,
)

SITES = REPO / "state" / "prospects" / "sites"
RECORDS = REPO / "state" / "prospects" / "records"
SHOOT = REPO / "scripts" / "web" / "shoot.mjs"
DEFAULT_OUT = REPO / "state" / "artifacts" / "moodboards"


def _record(place_id: str) -> dict:
    f = RECORDS / f"{place_id}.json"
    return json.loads(f.read_text()) if f.is_file() else {}


def _business_manifest(build_hub: str | Path) -> ImageryManifest:
    """A real build's imagery manifest (``<hub>/design-studio/imagery/manifest.json``)."""

    path = Path(build_hub) / "design-studio" / "imagery" / "manifest.json"
    return ImageryManifest.load(path) if path.is_file() else ImageryManifest()


def _resolve_src(asset, kit) -> Path:
    """Resolve an asset's file: absolute, repo-relative (business build), or kit-relative."""

    path = Path(asset.path)
    if path.is_absolute():
        return path
    for candidate in (REPO / asset.path, kit.dir / asset.path):
        if candidate.is_file():
            return candidate
    return kit.dir / asset.path  # fall through; the caller's is_file() check skips it


def cmd_build(args: argparse.Namespace) -> int:
    kit = load_kit(args.slug)
    if kit is None:
        sys.exit(f"no kit '{args.slug}'. available: {', '.join(list_kits()) or '(none)'}")

    record = _record(args.place_id) if args.place_id else {}
    business_name = (
        args.business_name or record.get("display_name") or f"{kit.recipe.display_name} (sample)"
    )

    # Image layers: real build first (on-brief shots), kit exemplars fill toward --want.
    manifests: list[ImageryManifest] = []
    hub = args.build_hub or (str(SITES / args.place_id) if args.place_id else "")
    if hub:
        manifests.append(_business_manifest(hub))
    manifests.append(kit.manifest)
    assets = collect_images(*manifests, want=args.want)

    out = Path(args.out) if args.out else (
        SITES / args.place_id / "mood-board" if args.place_id else DEFAULT_OUT / args.slug
    )
    out.mkdir(parents=True, exist_ok=True)
    assets_dir = out / "assets"
    if assets_dir.exists():
        shutil.rmtree(assets_dir)
    assets_dir.mkdir(parents=True, exist_ok=True)

    web_paths: list[str] = []
    for asset in assets:
        src = _resolve_src(asset, kit)
        if not src.is_file():
            print(f"  ! skipping missing image: {src}")
            continue
        suffix = src.suffix.lower() or ".png"
        dest = assets_dir / f"{asset.id}{suffix}"
        shutil.copyfile(src, dest)
        web_paths.append(f"assets/{asset.id}{suffix}")

    board = moodboard_from_kit(
        kit, business_name=business_name, images=web_paths, concept_statement=args.concept or ""
    )
    (out / "index.html").write_text(render_moodboard_html(board))
    (out / "board.json").write_text(
        json.dumps(
            {
                "slug": args.slug,
                "business_name": business_name,
                "concept_statement": board.concept_statement,
                "palette": asdict(board.palette),
                "font": {
                    "vibe": board.font.vibe,
                    "display": board.font.display,
                    "body": board.font.body,
                },
                "images": web_paths,
                "image_count": len(web_paths),
                "direction_notes": board.direction_notes,
            },
            indent=2,
        )
        + "\n"
    )
    print(f"✓ mood board → {out / 'index.html'}  ({len(web_paths)} image(s))")
    if len(web_paths) < 6:
        print(
            f"  note: {len(web_paths)} images (<6). Add a --build-hub/--place-id with real "
            "shots, or harvest more exemplars."
        )
    print(f"  preview: python scripts/agency/preview_site.py --dir {out}")

    if args.shoot:
        _shoot(out, args.slug)
    if args.deploy:
        _deploy(out, args, record, business_name)
    return 0


def _shoot(out: Path, slug: str) -> None:
    shots = out / "screenshots"
    shots.mkdir(exist_ok=True)
    result = subprocess.run(
        ["node", str(SHOOT), str(out), str(shots), f"/:{slug}-moodboard", "--width", "1100"],
        capture_output=True,
        text=True,
    )
    png = shots / f"{slug}-moodboard.png"
    if result.returncode == 0 and png.is_file():
        print(f"✓ screenshot → {png} ({png.stat().st_size // 1024} KB)")
    else:
        msg = (result.stderr or result.stdout).strip()[:200] or "unknown error"
        print(f"  ✗ shoot failed: {msg}")


def _deploy(out: Path, args: argparse.Namespace, record: dict, business_name: str) -> None:
    # Same draft-permalink path as build_prospect_site.py — one shared preview site,
    # cheap draft deploys, no new Netlify site per artifact.
    from packages.agency.prospect_site import deploy_preview_dist
    from packages.web.deploy import DeployAccount, NetlifyDeployTarget

    account = DeployAccount(id=args.account) if args.account else None
    target = NetlifyDeployTarget(account=account)
    rec = {"place_id": args.place_id or args.slug, "display_name": business_name}
    result = deploy_preview_dist(rec, out, target=target, account=account)
    print(f"✓ deployed (private draft) → {result.mockup_url}")
    if args.place_id and record:
        record["moodboard_url"] = result.mockup_url
        (RECORDS / f"{args.place_id}.json").write_text(json.dumps(record, indent=2) + "\n")
        print(f"  wrote moodboard_url → record {args.place_id}")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    sub = ap.add_subparsers(dest="command", required=True)
    b = sub.add_parser("build", help="render a mood board from a kit")
    b.add_argument("--slug", required=True, help="kit slug (see art_direction.py list)")
    b.add_argument("--place-id", help="prospect record/site to layer real imagery + target")
    b.add_argument(
        "--build-hub", help="a build hub to pull real imagery from (overrides --place-id's)"
    )
    b.add_argument("--business-name", help="override the displayed business name")
    b.add_argument("--concept", help="override the concept statement")
    b.add_argument("--want", type=int, default=9, help="max images on the board (default 9)")
    b.add_argument(
        "--out",
        help="output dir (default: the site's mood-board/ or state/artifacts/moodboards/<slug>)",
    )
    b.add_argument(
        "--shoot", action="store_true", help="also capture a full-page PNG via shoot.mjs"
    )
    b.add_argument(
        "--deploy", action="store_true", help="publish a private draft (needs $NETLIFY_AUTH_TOKEN)"
    )
    b.add_argument("--account", help="Netlify team/account slug for --deploy")

    args = ap.parse_args(argv)
    if args.command == "build":
        return cmd_build(args)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
