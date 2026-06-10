#!/usr/bin/env python3
"""Ingest externally-sourced images into a build's imagery manifest (the bridge).

The design engine normally generates imagery with Gemini and writes
``<hub>/design-studio/imagery/manifest.json``; ``premium_build`` then stages the
``selected`` assets into the Astro ``public/img``. This bridges an EXTERNAL image
source (e.g. images generated in ChatGPT and downloaded) into that same contract, so a
build can use them without the Gemini API — copy the files into the imagery dir and
write a compatible manifest. After running this, rebuild with ``build_premium_site``
(reuses the manifest; no generation).

    python scripts/web/ingest_images.py --target state/artifacts/med-spa-flagship \\
        --hero ~/Downloads/hero.png --supporting ~/Downloads/s1.png ~/Downloads/s2.png

Provenance defaults to ``owner`` (operator-curated assets for our OWN portfolio demos),
so the build never blocks on AI-generation clearance. The prompt field records the real
source for traceability. Use ``--provenance generated`` if these will ship to a client
(so the launch clearance gate flags them for a rights review).
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from packages.web.imagery import (  # noqa: E402
    _VALID_PROVENANCE,
    ImageAsset,
    ImageryManifest,
)


def ingest(
    target: Path,
    hero: Path,
    supporting: list[Path],
    *,
    provenance: str = "owner",
    source_note: str = "ChatGPT (ai-company-os project) — operator-curated",
) -> Path:
    if provenance not in _VALID_PROVENANCE:
        raise ValueError(f"provenance must be one of {sorted(_VALID_PROVENANCE)}")
    imagery_dir = target / "design-studio" / "imagery"
    imagery_dir.mkdir(parents=True, exist_ok=True)

    assets: list[ImageAsset] = []

    def _stage(src: Path, asset_id: str, role: str) -> None:
        src = src.expanduser()
        if not src.is_file():
            raise FileNotFoundError(f"missing image: {src}")
        suffix = src.suffix.lower() or ".png"
        dest = imagery_dir / f"{asset_id}{suffix}"
        shutil.copyfile(src, dest)
        assets.append(
            ImageAsset(
                id=asset_id,
                role=role,
                path=str(dest),  # absolute → always resolvable by _stage_images
                provenance=provenance,
                prompt=f"{source_note} · {src.name}",
                selected=True,
                # Owner assets never block; mark cleared for traceability.
                production_clearance=(provenance != "generated"),
                cleared_by="operator" if provenance != "generated" else "",
            )
        )

    _stage(hero, "hero", "hero")
    for i, s in enumerate(supporting, start=1):
        _stage(s, f"support-{i}", "supporting")

    manifest_path = imagery_dir / "manifest.json"
    ImageryManifest(assets=assets).save(manifest_path)
    print(f"✓ ingested {len(assets)} image(s) → {manifest_path}")
    for a in assets:
        print(f"    {a.role:11} {Path(a.path).name}")
    print("  next: rebuild with build_premium_site (reuses this manifest, no Gemini).")
    return manifest_path


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--target", required=True, help="build hub dir (writes <dir>/design-studio/imagery/)")
    ap.add_argument("--hero", required=True, help="hero image file")
    ap.add_argument("--supporting", nargs="*", default=[], help="supporting image files (in order)")
    ap.add_argument("--provenance", default="owner", choices=sorted(_VALID_PROVENANCE))
    args = ap.parse_args()
    ingest(
        Path(args.target),
        Path(args.hero),
        [Path(s) for s in args.supporting],
        provenance=args.provenance,
    )


if __name__ == "__main__":
    main()
