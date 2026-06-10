#!/usr/bin/env python3
"""Genre art-direction kits CLI — inspect kits and scaffold a build's first draft.

A kit is the durable per-genre recipe (palette + type + imagery direction +
composition + a few exemplars). See ``packages/web/art_direction.py`` and
``packages/web/design_reference/kits/README.md``.

  list                                   show every kit + freshness
  show     --slug <s>                    print the recipe (markdown)
  scaffold --slug <s> --site-name … --audience … --goal …   emit an enriched build spec

The ``scaffold`` spec is the instant first draft — pipe it straight into the build:

    python scripts/agency/art_direction.py scaffold --slug med_spa \\
        --site-name "Lumina Aesthetics" --audience "..." --goal "..." \\
      | python scripts/agency/design_studio.py packet --target <hub> --spec -

(``harvest`` — promote a real build's winning prompt + images back into a kit — is a
separate verb added with the harvest loop.)
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from packages.web.art_direction import (  # noqa: E402
    apply_kit_to_spec,
    exemplar_paths,
    harvest_from_build,
    kit_palette,
    list_kits,
    load_kit,
    render_recipe_md,
)


def cmd_list() -> int:
    slugs = list_kits()
    if not slugs:
        print("no kits yet.")
        return 0
    print(f"{len(slugs)} kit(s):\n")
    for slug in slugs:
        kit = load_kit(slug)
        recipe = kit.recipe
        n_ex = len(exemplar_paths(kit))
        kind = f"{n_ex} exemplar(s)" if n_ex else "recipe-only"
        trail = f" · harvested×{len(recipe.harvested_from)}" if recipe.harvested_from else ""
        print(f"  {slug:16} v{recipe.version}  {kind:16} palette={recipe.palette}{trail}")
        print(f"  {'':16} aliases: {', '.join(recipe.niche_aliases)}")
    return 0


def cmd_show(slug: str) -> int:
    kit = load_kit(slug)
    if kit is None:
        sys.exit(f"no kit '{slug}'. available: {', '.join(list_kits()) or '(none)'}")
    print(render_recipe_md(kit.recipe))
    palette = kit_palette(kit)
    print(f"\n_resolved palette: primary {palette.primary} · accent {palette.accent}_")
    for path in exemplar_paths(kit):
        print(f"  exemplar: {path.relative_to(REPO) if path.is_relative_to(REPO) else path}")
    return 0


def cmd_prompts(slug: str) -> int:
    kit = load_kit(slug)
    if kit is None:
        sys.exit(f"no kit '{slug}'. available: {', '.join(list_kits()) or '(none)'}")
    sequence = kit.recipe.image_prompts.ingest_sequence()
    if not sequence:
        print(f"kit '{slug}' has no image prompts yet (harvest or add them to kit.yaml).")
        return 0
    print(f"# ChatGPT image prompts — {kit.recipe.display_name}")
    print("# Instant model (NOT Thinking); self-contained text, no live URLs. Save to ~/Downloads.")
    print()
    for label, prompt in sequence:
        print(f"## {label}\n{prompt}\n")
    order = [label for label, _ in sequence]
    supporting = " ".join(f"~/Downloads/{label}.png" for label in order[1:])
    print("# then ingest (hero + bento first, BAND LAST):")
    print("#   python scripts/web/ingest_images.py --target <hub> \\")
    print(f"#       --hero ~/Downloads/{order[0]}.png --supporting {supporting}")
    return 0


def cmd_scaffold(args: argparse.Namespace) -> int:
    kit = load_kit(args.slug)
    if kit is None:
        sys.exit(f"no kit '{args.slug}'. available: {', '.join(list_kits()) or '(none)'}")
    base: dict[str, object] = {
        "site_name": args.site_name,
        "business_category": args.business_category
        or (kit.recipe.niche_aliases or [kit.recipe.slug])[0],
        "audience": args.audience,
        "goal": args.goal,
    }
    if args.evidence:
        base["evidence"] = list(args.evidence)
    spec = apply_kit_to_spec(base, kit)
    print(json.dumps(spec, indent=2))
    return 0


def cmd_harvest(args: argparse.Namespace) -> int:
    ids = json.loads(args.exemplars) if args.exemplars else None
    try:
        kit = harvest_from_build(
            args.slug,
            args.build_hub,
            exemplar_ids=ids,
            note=args.note,
            allow_uncleared=args.allow_uncleared,
            allow_owner=args.allow_owner,
        )
    except PermissionError as exc:
        sys.exit(f"✗ harvest blocked — {exc}")
    n = len(exemplar_paths(kit))
    print(f"✓ harvested into '{args.slug}' (v{kit.recipe.version}) — {n} exemplar(s) total")
    print(f"  from: {kit.recipe.harvested_from[-1]}")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    sub = ap.add_subparsers(dest="command", required=True)

    sub.add_parser("list", help="show every kit + freshness")

    p_show = sub.add_parser("show", help="print a kit's recipe")
    p_show.add_argument("--slug", required=True)

    p_prompts = sub.add_parser("prompts", help="print the kit's ChatGPT image prompts (in order)")
    p_prompts.add_argument("--slug", required=True)

    p_scaffold = sub.add_parser("scaffold", help="emit an enriched build spec from a kit")
    p_scaffold.add_argument("--slug", required=True)
    p_scaffold.add_argument("--site-name", required=True, dest="site_name")
    p_scaffold.add_argument("--audience", required=True)
    p_scaffold.add_argument("--goal", required=True)
    p_scaffold.add_argument(
        "--business-category", dest="business_category",
        help="defaults to the kit's first niche alias",
    )
    p_scaffold.add_argument("--evidence", nargs="*", help="real proof points from the business")

    p_harvest = sub.add_parser("harvest", help="promote a build's winning images into a kit")
    p_harvest.add_argument("--slug", required=True)
    p_harvest.add_argument(
        "--from", dest="build_hub", required=True, help="build hub (has design-studio/imagery/)"
    )
    p_harvest.add_argument("--exemplars", help="JSON list of asset ids (default: all selected)")
    p_harvest.add_argument("--note", default="", help="provenance note for the harvest trail")
    p_harvest.add_argument(
        "--allow-uncleared", action="store_true", dest="allow_uncleared",
        help="permit uncleared generated assets (kept uncleared; gate still applies downstream)",
    )
    p_harvest.add_argument("--allow-owner", action="store_true", dest="allow_owner",
                           help="permit owner assets (only if operator-owned + licensed for reuse)")

    args = ap.parse_args(argv)
    if args.command == "list":
        return cmd_list()
    if args.command == "show":
        return cmd_show(args.slug)
    if args.command == "prompts":
        return cmd_prompts(args.slug)
    if args.command == "scaffold":
        return cmd_scaffold(args)
    if args.command == "harvest":
        return cmd_harvest(args)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
