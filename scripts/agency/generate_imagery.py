#!/usr/bin/env python3
"""Concept-led imagery CLI — Phase 4 of the design engine.

Drives the imagery pipeline for one premium build, persisting under the build's
hub (`<target>/design-studio/imagery/`):

  brief    --target <dir> --spec <spec.json|->    build cohesive image briefs
  generate --target <dir> [--seed N]              generate the set (Gemini)
  select   --target <dir> --keep <ids.json|->     record curated survivors (agent or human)
  clear    --target <dir> --ids <ids.json|-> --by NAME   founder production-clearance waiver
  status   --target <dir>                         show clearance blockers

`select` and `clear` make curation + clearance agent-callable primitives (parity
with the rest of the lane): the agent decides which ids; the subcommand persists.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from packages.web.imagery import (  # noqa: E402
    PROVENANCE_GENERATED,
    ImageAsset,
    ImageBrief,
    ImageryManifest,
    build_image_briefs,
    clearance_blockers,
)


def imagery_dir(target: str | Path) -> Path:
    return Path(target) / "design-studio" / "imagery"


def _read_json(value: str) -> object:
    return json.loads(sys.stdin.read()) if value == "-" else json.loads(Path(value).read_text())


def _briefs_path(target: str | Path) -> Path:
    return imagery_dir(target) / "briefs.json"


def _manifest_path(target: str | Path) -> Path:
    return imagery_dir(target) / "manifest.json"


def cmd_brief(target: str, spec: object) -> int:
    from packages.web.design_studio import build_design_studio_packet
    from scripts.agency.design_studio import request_from_spec

    packet = build_design_studio_packet(request_from_spec(spec))  # type: ignore[arg-type]
    briefs = build_image_briefs(packet)
    out = _briefs_path(target)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps([b.to_dict() for b in briefs], indent=2) + "\n")
    print(f"✓ {len(briefs)} briefs → {out}")
    return 0


def cmd_generate(target: str, seed: int | None) -> int:
    from packages.tools.content_tools.gemini_images import generate_image

    briefs = [ImageBrief(**b) for b in json.loads(_briefs_path(target).read_text())]
    assets: list[ImageAsset] = []
    for brief in briefs:
        img = generate_image(brief.prompt, aspect_ratio=brief.aspect_ratio)
        path = imagery_dir(target) / f"{brief.id}.png"
        img.save(path)
        assets.append(
            ImageAsset(
                id=brief.id,
                role=brief.role,
                path=str(path),
                provenance=PROVENANCE_GENERATED,
                prompt=brief.prompt,
                seed=seed if seed is not None else brief.seed,
                selected=True,
                production_clearance=False,
            )
        )
        print(f"✓ generated {brief.id}")
    ImageryManifest(assets=assets).save(_manifest_path(target))
    print(f"✓ manifest → {_manifest_path(target)} ({len(assets)} assets, uncleared)")
    return 0


def cmd_select(target: str, keep: list[str] | None, auto_curate: int | None) -> int:
    manifest = ImageryManifest.load(_manifest_path(target))
    if auto_curate is not None:
        # Unattended convergence: keep the hero + the first (N-1) supporting assets in
        # manifest (seed) order, so the loop can run without a human/agent curator.
        ordered = sorted(manifest.assets, key=lambda a: (a.role != "hero", a.id))
        keep_set = {a.id for a in ordered[: max(1, auto_curate)]}
    else:
        keep_set = set(keep or [])
    manifest.assets = [
        ImageAsset(**{**a.to_dict(), "selected": a.id in keep_set}) for a in manifest.assets
    ]
    manifest.save(_manifest_path(target))
    print(f"✓ selected {len(keep_set)} asset(s)")
    return 0


def cmd_clear(target: str, ids: list[str], by: str) -> int:
    manifest = ImageryManifest.load(_manifest_path(target))
    id_set = set(ids)
    manifest.assets = [
        ImageAsset(
            **{**a.to_dict(), "production_clearance": True, "cleared_by": by}
        )
        if a.id in id_set
        else a
        for a in manifest.assets
    ]
    manifest.save(_manifest_path(target))
    print(f"✓ cleared {len(id_set)} asset(s) for production by {by}")
    return 0


def cmd_status(target: str) -> int:
    path = _manifest_path(target)
    if not path.exists():
        print("no imagery manifest (no generated assets to clear)")
        return 0
    blockers = clearance_blockers(ImageryManifest.load(path))
    if blockers:
        print(f"BLOCKED — {len(blockers)} uncleared generated asset(s): {', '.join(blockers)}")
        return 1
    print("cleared — all selected generated assets are founder-cleared")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Concept-led imagery pipeline")
    sub = parser.add_subparsers(dest="command", required=True)

    p_brief = sub.add_parser("brief")
    p_brief.add_argument("--target", required=True)
    p_brief.add_argument("--spec", required=True)

    p_gen = sub.add_parser("generate")
    p_gen.add_argument("--target", required=True)
    p_gen.add_argument("--seed", type=int, default=None)

    p_sel = sub.add_parser("select")
    p_sel.add_argument("--target", required=True)
    p_sel.add_argument("--keep", default=None, help="JSON list of ids, or '-'")
    p_sel.add_argument(
        "--auto-curate",
        type=int,
        default=None,
        metavar="N",
        help="unattended: keep hero + first N-1 supporting assets (no curator needed)",
    )

    p_clear = sub.add_parser("clear")
    p_clear.add_argument("--target", required=True)
    p_clear.add_argument("--ids", required=True, help="JSON list of ids, or '-'")
    p_clear.add_argument("--by", required=True, help="who is clearing (founder)")

    p_status = sub.add_parser("status")
    p_status.add_argument("--target", required=True)

    args = parser.parse_args(argv)

    if args.command == "brief":
        return cmd_brief(args.target, _read_json(args.spec))
    if args.command == "generate":
        return cmd_generate(args.target, args.seed)
    if args.command == "select":
        if args.auto_curate is None and args.keep is None:
            parser.error("select needs --keep <ids> or --auto-curate N")
        keep = list(_read_json(args.keep)) if args.keep is not None else None  # type: ignore[arg-type]
        return cmd_select(args.target, keep, args.auto_curate)
    if args.command == "clear":
        return cmd_clear(args.target, list(_read_json(args.ids)), args.by)  # type: ignore[arg-type]
    if args.command == "status":
        return cmd_status(args.target)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
