"""Concept-led imagery pipeline — Phase 4 of the design engine.

Promotes the concept-led-imagery playbook into code: concept -> cohesive image
briefs (one shared style spec so a hero + supporting set read as one shoot) ->
generated assets -> curated survivors -> an optimized manifest.

Per the founder decision (2026-06-08), generated imagery may ship on production
client sites — but every asset carries **provenance** + a **production_clearance**
waiver so the legal posture (AI imagery is non-copyrightable per USCO 2025 and
SynthID-watermarked) is always a logged, conscious choice, never an accident. The
deploy guard refuses an uncleared generated asset on a client go-live.

This module is the pure, testable core (briefs + manifest + clearance). Live
generation is wrapped in `scripts/agency/generate_imagery.py` over the existing
`packages.tools.content_tools.gemini_images.generate_image`.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Protocol

from packages.web.design_studio import DesignStudioPacket


class _Saveable(Protocol):
    def save(self, path: Path) -> object: ...


# (prompt, aspect_ratio, seed) -> an object with a .save(path) method. Matches
# packages.tools.content_tools.gemini_images.generate_image; injectable for tests.
ImageGenerator = Callable[[str, str, int], _Saveable]

PROVENANCE_GENERATED = "generated"
PROVENANCE_OWNER = "owner"
PROVENANCE_LICENSED = "licensed"
_VALID_PROVENANCE = {PROVENANCE_GENERATED, PROVENANCE_OWNER, PROVENANCE_LICENSED}


@dataclass(frozen=True)
class ImageBrief:
    """One image to generate, sharing a style spec with its set for cohesion."""

    id: str
    role: str  # "hero" | "supporting"
    prompt: str
    aspect_ratio: str
    seed: int

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class ImageAsset:
    """A produced image + its provenance and clearance state."""

    id: str
    role: str
    path: str
    provenance: str
    prompt: str = ""
    seed: int = 0
    selected: bool = True
    production_clearance: bool = False
    cleared_by: str = ""

    def __post_init__(self) -> None:
        if self.provenance not in _VALID_PROVENANCE:
            raise ValueError(f"invalid provenance: {self.provenance}")

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class ImageryManifest:
    """The per-build imagery record consumed by the composer + deploy guard."""

    assets: list[ImageAsset] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {"assets": [a.to_dict() for a in self.assets]}

    @classmethod
    def from_dict(cls, payload: dict) -> ImageryManifest:
        return cls(assets=[ImageAsset(**a) for a in payload.get("assets", [])])

    def save(self, path: Path) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.to_dict(), indent=2) + "\n")
        return path

    @classmethod
    def load(cls, path: Path) -> ImageryManifest:
        return cls.from_dict(json.loads(Path(path).read_text()))


# --------------------------------------------------------------------------- #
# Briefs — cohesion comes from a shared style spec + a fixed seed family.
# --------------------------------------------------------------------------- #
def style_spec(packet: DesignStudioPacket) -> str:
    """The shared style suffix that makes a set read as one commissioned shoot."""

    concept = packet.concept_statement.split(";")[0].strip().rstrip(".")
    palette = "deep, premium tones with a single warm accent" if packet.archetype in {
        "service-area-cinematic",
        "product-led",
    } else "bright, refined tones"
    direction = getattr(packet, "imagery_direction", "").strip().rstrip(".")
    style = (
        f"art-directed editorial photography expressing: {concept}. "
        f"{palette}; consistent lighting, color grade, and crop across the set; "
        "premium, cinematic depth; no text, no logos, no watermark."
    )
    if direction:
        # Pull the reference's signature look through the whole set (e.g. an abundant
        # overhead food flat-lay, or soft natural-light interiors).
        style += f" Art direction: {direction}."
    return style


def build_image_briefs(
    packet: DesignStudioPacket,
    *,
    supporting: int = 4,
    base_seed: int = 1000,
) -> list[ImageBrief]:
    """A hero + supporting set, all sharing one style spec and a seed family."""

    spec = style_spec(packet)
    subject = f"{packet.business_category} for {packet.audience}"
    # The hero composition follows the art direction when given (e.g. an overhead
    # flat-lay) instead of the generic "composed scene", which tends to default to a
    # person-in-a-room shot regardless of niche.
    direction = getattr(packet, "imagery_direction", "").strip().rstrip(".")
    hero_comp = direction if direction else "a composed scene"
    briefs = [
        ImageBrief(
            id="hero",
            role="hero",
            prompt=f"Hero image — {hero_comp} of {subject}. {spec}",
            aspect_ratio="16:9",
            seed=base_seed,
        )
    ]
    for i in range(supporting):
        briefs.append(
            ImageBrief(
                id=f"support-{i + 1}",
                role="supporting",
                prompt=f"Supporting detail {i + 1} of {subject}. {spec}",
                aspect_ratio="1:1",
                seed=base_seed + i + 1,
            )
        )
    return briefs


# --------------------------------------------------------------------------- #
# Generate a cohesive set + auto-curate (the loop's imagery leg)
# --------------------------------------------------------------------------- #
def generate_imagery_set(
    packet: DesignStudioPacket,
    out_dir: Path,
    *,
    generate: ImageGenerator,
    supporting: int = 4,
    keep: int = 3,
    base_seed: int = 1000,
) -> ImageryManifest:
    """Generate a hero + supporting set, auto-curate, and persist the manifest.

    This is the loop's imagery leg made self-sufficient: it builds cohesive briefs
    (shared style spec + seed family), runs ``generate`` for each (the live caller
    passes the Pro image model), keeps the hero + the first ``keep``-1 supporting
    assets (unattended curation), and writes ``manifest.json`` next to the PNGs —
    ready for ``build_premium_site`` to stage into the page. ``generate`` is injected
    so this is unit-testable without an API key.
    """

    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    briefs = build_image_briefs(packet, supporting=supporting, base_seed=base_seed)
    assets: list[ImageAsset] = []
    for brief in briefs:
        image = generate(brief.prompt, brief.aspect_ratio, brief.seed)
        path = out_dir / f"{brief.id}.png"
        image.save(path)
        assets.append(
            ImageAsset(
                id=brief.id,
                role=brief.role,
                path=str(path),
                provenance=PROVENANCE_GENERATED,
                prompt=brief.prompt,
                seed=brief.seed,
                selected=True,
            )
        )
    # Auto-curate: hero first, then supporting in seed order; keep the top N.
    ordered = sorted(assets, key=lambda a: (a.role != "hero", a.id))
    keep_ids = {a.id for a in ordered[: max(1, keep)]}
    assets = [ImageAsset(**{**a.to_dict(), "selected": a.id in keep_ids}) for a in assets]
    manifest = ImageryManifest(assets=assets)
    manifest.save(out_dir / "manifest.json")
    return manifest


# --------------------------------------------------------------------------- #
# Clearance gate
# --------------------------------------------------------------------------- #
def clearance_blockers(manifest: ImageryManifest) -> list[str]:
    """Selected, generated assets that are not yet founder-cleared for production.

    Owner-provided and licensed assets never block. Unselected (curated-out)
    assets never block. This is what the deploy guard checks before a client ship.
    """

    return [
        a.id
        for a in manifest.assets
        if a.selected and a.provenance == PROVENANCE_GENERATED and not a.production_clearance
    ]


def imagery_cleared(manifest_path: Path) -> bool:
    """True if there's no manifest, or every selected generated asset is cleared."""

    path = Path(manifest_path)
    if not path.exists():
        return True
    return not clearance_blockers(ImageryManifest.load(path))
