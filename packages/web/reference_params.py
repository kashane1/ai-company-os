"""Reference analyzer core — Phase 5 of the design engine.

Turns a structured read of a Dribbble/Awwwards shot into inputs the synthesizer
and packet consume — palette hexes, type-scale ratio, density, grid, hero
structure, motion cues. Per the agent-native design, the *vision* (looking at the
shot) is an agent capability; this module is the deterministic contract that
validates the structured params and folds them into a build spec as concrete
parameters (not hand-fed prose).
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path

from packages.web.palette import parse_color

_DENSITY = {"airy", "balanced", "dense"}


@dataclass(frozen=True)
class ReferenceParams:
    """A structured read of one inspiration reference."""

    title: str
    url: str = ""
    palette: list[str] = field(default_factory=list)
    type_scale_ratio: float = 1.25
    density: str = "balanced"
    grid: str = "asymmetric"
    hero_structure: str = ""
    motion_cues: list[str] = field(default_factory=list)
    takeaways: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        for hexv in self.palette:
            parse_color(hexv)  # raises on anything we can't resolve
        if not 1.0 < self.type_scale_ratio < 2.5:
            raise ValueError(f"implausible type_scale_ratio: {self.type_scale_ratio}")
        if self.density not in _DENSITY:
            raise ValueError(f"density must be one of {_DENSITY}")

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: dict) -> ReferenceParams:
        allowed = {f for f in cls.__dataclass_fields__}
        return cls(**{k: v for k, v in payload.items() if k in allowed})


def params_to_takeaways(params: ReferenceParams) -> list[str]:
    """Translate structured params into reference takeaways (translate, not copy)."""

    out = list(params.takeaways)
    out.append(f"{params.density} density, {params.grid} grid")
    if params.hero_structure:
        out.append(f"hero: {params.hero_structure}")
    for cue in params.motion_cues:
        out.append(f"motion: {cue}")
    # Dedupe preserving order.
    seen: set[str] = set()
    return [x for x in out if not (x in seen or seen.add(x))]


def palette_from_image(path: str | Path, k: int = 5) -> list[str]:
    """Extract the k dominant colors from a reference image, most-frequent first.

    Real reference *reading* (the v2 analyzer never ingested an image — it only
    validated agent-typed JSON). Uses Pillow's median-cut quantizer; deterministic
    and offline, so it runs without an API key.
    """

    from PIL import Image  # local import keeps Pillow optional for the rest of the lane

    img = Image.open(path).convert("RGB")
    img.thumbnail((200, 200))
    quantized = img.quantize(colors=max(1, k), method=Image.Quantize.MEDIANCUT)
    palette = quantized.getpalette() or []
    by_freq = sorted(quantized.getcolors() or [], reverse=True)  # (count, index)
    hexes: list[str] = []
    for _, idx in by_freq:
        r, g, b = palette[idx * 3 : idx * 3 + 3]
        hexes.append(f"#{r:02x}{g:02x}{b:02x}")
    return hexes[:k]


# hero_structure keyword -> which composition variant fits. Variant index 1 is, by
# convention, each archetype's image-led skeleton (leads with FullBleedMedia early);
# index 0 is the clean editorial skeleton. So a reference's hero structure
# measurably changes the LAYOUT, not just the palette (the Phase 5 exit criterion).
def recommended_variant(params: ReferenceParams, n: int) -> int:
    """Pick a composition variant from the reference's hero structure / grid."""

    if n <= 1:
        return 0
    hero = (params.hero_structure or "").lower()
    if any(t in hero for t in ("full", "bleed", "image", "cinematic", "photo", "media")):
        return 1  # image-led variant (FullBleedMedia early)
    if any(t in hero for t in ("split", "editorial", "text", "type")):
        return 0  # clean editorial variant
    return 2 % n if params.grid == "asymmetric" else 0


def apply_to_spec(params: ReferenceParams, spec: dict) -> dict:
    """Fold reference params into a build spec for the synthesizer + composer.

    - Seeds `concept_palette` from the reference's dominant color (only if the
      spec hasn't already set one — the business's own cue always wins).
    - Appends a translated reference (takeaways) to `references`.
    Returns a new spec dict; does not mutate the input.
    """

    out = {**spec}
    if params.palette and not out.get("concept_palette"):
        out["concept_palette"] = params.palette[0]
    references = list(out.get("references", []))
    references.append(
        {
            "title": params.title,
            "url": params.url,
            "source_type": "reference",
            "takeaways": params_to_takeaways(params),
        }
    )
    out["references"] = references
    return out
