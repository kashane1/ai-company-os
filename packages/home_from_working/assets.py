"""Deterministic production-master checks for POD artwork."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

from PIL import Image


@dataclass(frozen=True)
class AssetStandard:
    min_width: int = 2000
    min_height: int = 2000
    print_width_inches: float = 12.0
    min_effective_dpi: float = 150.0
    max_edge_padding_ratio: float = 0.40


def _content_bbox(image: Image.Image) -> tuple[int, int, int, int] | None:
    if "A" in image.getbands():
        return image.getchannel("A").getbbox()
    return image.convert("RGB").getbbox()


def inspect_asset(
    path: str | Path,
    standard: AssetStandard | None = None,
    *,
    hero_manifest: Mapping[str, object] | None = None,
    recorded_sha256: str | None = None,
) -> dict[str, object]:
    standard = standard or AssetStandard()
    path = Path(path)
    if not path.is_file():
        return {"path": str(path), "status": "blocked_missing_file", "checks": {}}

    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    try:
        with Image.open(path) as image:
            image.load()
            width, height = image.size
            bbox = _content_bbox(image)
            transparent = "A" in image.getbands() and image.getchannel("A").getextrema()[0] < 255
            file_type_pass = (image.format or "").upper() == "PNG"
    except (OSError, ValueError) as exc:
        return {
            "path": str(path),
            "sha256": digest,
            "status": "fail",
            "checks": {"file_type": "fail"},
            "error": f"unreadable image: {exc.__class__.__name__}",
        }

    effective_dpi = width / standard.print_width_inches
    padding_pass = False
    padding = None
    if bbox:
        left, top, right, bottom = bbox
        padding = {
            "left": left / width,
            "right": (width - right) / width,
            "top": top / height,
            "bottom": (height - bottom) / height,
        }
        padding_pass = max(padding.values()) <= standard.max_edge_padding_ratio
    checks = {
        "file_type": "pass" if file_type_pass else "fail",
        "dimensions": "pass" if width >= standard.min_width and height >= standard.min_height else "fail",
        "transparency": "pass" if transparent else "fail",
        "effective_dpi": "pass" if effective_dpi >= standard.min_effective_dpi else "fail",
        "nonempty_artwork": "pass" if bbox else "fail",
        "content_padding": "pass" if padding_pass else "fail",
    }
    if recorded_sha256 is not None:
        checks["hash_integrity"] = (
            "pass" if digest.casefold() == recorded_sha256.strip().casefold() else "fail"
        )
    hero_check = "not_applicable_no_manifest"
    if hero_manifest and hero_manifest.get("source") == "ai":
        if hero_manifest.get("illustrative_mockup") is not True:
            hero_check = "fail_misrepresentation_risk"
        else:
            disclosure = hero_manifest.get("no_misrepresentation_note")
            hero_check = (
                "pass_illustrative_mockup_disclosed"
                if isinstance(disclosure, str) and disclosure.strip()
                else "fail_missing_no_misrepresentation_note"
            )
    elif hero_manifest:
        hero_check = "not_applicable_non_ai"
    status = "pass" if all(value == "pass" for value in checks.values()) else "fail"
    if hero_check and hero_check.startswith("fail"):
        status = "fail"
    return {
        "path": str(path),
        "sha256": digest,
        "status": status,
        "width": width,
        "height": height,
        "effective_dpi": round(effective_dpi, 2),
        "content_padding": padding,
        "checks": checks,
        "hash_integrity_check": checks.get("hash_integrity", "unknown_not_recorded"),
        "hero_image_check": hero_check,
    }
