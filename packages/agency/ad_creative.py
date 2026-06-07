"""Ad creative generation (Agency layer) — images for Google/Meta ad drafts.

Policy (decided with the founder):
* **Real photos first.** Prefer the client's own photos; only generate AI imagery
  as a fallback when no usable real asset exists. AI imagery for a *real* local
  business risks looking off-brand or misrepresenting them — so generated scenes
  stay lifestyle/product/abstract and NEVER depict the business's specific
  storefront, staff, or "customers" (fake people/awards are a deceptive-ad risk).
* **Clean imagery + promo graphics.** Each background is produced text-free at the
  platform aspect ratios (the ad platform renders the copy). Optionally we also
  burn a headline onto a copy via ``text_overlay`` for promo/sale graphics.
* **Drafts only.** Output is a proposal for operator review; nothing is uploaded.
  Going live stays behind ``ad_campaign_go_live`` (see ``retainer_executor``).

The image generator is injected (default: Gemini ``generate_image``) so tests run
without network. Eligibility (firearms etc.) is enforced upstream by ``ad_policy``.
"""

from __future__ import annotations

import logging
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from pathlib import Path

from PIL import Image, ImageOps

logger = logging.getLogger(__name__)

# Platform ad sizes (px) keyed by aspect ratio. Covers Google + Meta placements.
AD_ASPECT_SIZES: dict[str, tuple[int, int]] = {
    "1:1": (1080, 1080),      # IG/FB feed square, Google square
    "4:5": (1080, 1350),      # IG/FB feed portrait
    "9:16": (1080, 1920),     # Stories / Reels
    "1.91:1": (1200, 628),    # Google/Meta landscape link
}
DEFAULT_ASPECTS: tuple[str, ...] = ("1:1", "4:5", "9:16", "1.91:1")
# Promo (text-overlay) graphics only make sense in the upright/square formats.
_OVERLAY_ASPECTS: tuple[str, ...] = ("1:1", "9:16")

# (prompt, aspect_ratio) -> raw image bytes. The Gemini default is wired lazily.
ImageGenerator = Callable[[str, str], bytes]


@dataclass(frozen=True)
class CreativeConcept:
    """One AI creative idea — used only when no real client photo is available."""

    name: str
    prompt: str
    fallback_prompt: str = ""  # neutral retry if the primary is refused/empty
    headline: str = ""         # for the optional promo overlay


@dataclass(frozen=True)
class CreativeAsset:
    concept: str
    aspect_ratio: str
    path: str
    source: str   # "client-photo" | "generated" | "generated-fallback"
    overlay: bool = False

    def to_dict(self) -> dict[str, object]:
        return {
            "concept": self.concept,
            "aspect_ratio": self.aspect_ratio,
            "path": self.path,
            "source": self.source,
            "overlay": self.overlay,
        }


@dataclass(frozen=True)
class CreativeResult:
    product_id: str
    assets: list[CreativeAsset] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return {
            "product_id": self.product_id,
            "assets": [a.to_dict() for a in self.assets],
            "notes": list(self.notes),
        }


def _slug(text: str) -> str:
    keep = "".join(c if c.isalnum() else "-" for c in text.strip().lower())
    return "-".join(p for p in keep.split("-") if p) or "creative"


def _default_image_generator() -> ImageGenerator:
    """Wrap Gemini ``generate_image`` as an ImageGenerator (lazy import)."""
    from packages.tools.content_tools.gemini_images import generate_image

    def _gen(prompt: str, aspect_ratio: str) -> bytes:
        return generate_image(prompt, aspect_ratio=aspect_ratio).data

    return _gen


def _save_fitted(src: Image.Image, aspect_ratio: str, dest: Path) -> None:
    """Cover-fit ``src`` to the platform size for ``aspect_ratio`` and save JPEG."""
    size = AD_ASPECT_SIZES[aspect_ratio]
    fitted = ImageOps.fit(src.convert("RGB"), size, method=Image.LANCZOS)
    dest.parent.mkdir(parents=True, exist_ok=True)
    fitted.save(dest, format="JPEG", quality=82)


@dataclass(frozen=True)
class _Background:
    name: str          # slug for filenames
    path: Path         # the source image on disk
    source: str        # provenance label
    headline: str = ""


def _materialize_backgrounds(
    *,
    out_dir: Path,
    concepts: Sequence[CreativeConcept],
    client_photos: Sequence[Path],
    image_generator: ImageGenerator,
    notes: list[str],
) -> list[_Background]:
    """Resolve source backgrounds — real client photos first, AI fallback."""
    usable = [p for p in client_photos if Path(p).is_file()]
    if usable:
        notes.append(f"using {len(usable)} client photo(s) — no AI imagery generated")
        return [
            _Background(
                name=f"photo-{i + 1}-{_slug(Path(p).stem)}",
                path=Path(p),
                source="client-photo",
            )
            for i, p in enumerate(usable)
        ]

    if not concepts:
        raise ValueError("no client photos and no concepts — nothing to make creative from")

    src_dir = out_dir / "_source"
    src_dir.mkdir(parents=True, exist_ok=True)
    notes.append(f"no client photos — generating {len(concepts)} AI background(s)")
    backgrounds: list[_Background] = []
    for concept in concepts:
        raw, source = _generate_one(concept, image_generator, notes)
        if raw is None:
            continue
        src_path = src_dir / f"{_slug(concept.name)}.png"
        src_path.write_bytes(raw)
        backgrounds.append(
            _Background(
                name=_slug(concept.name),
                path=src_path,
                source=source,
                headline=concept.headline,
            )
        )
    return backgrounds


def _generate_one(
    concept: CreativeConcept, image_generator: ImageGenerator, notes: list[str]
) -> tuple[bytes | None, str]:
    """Generate a concept's image, dropping to its fallback prompt on refusal."""
    try:
        return image_generator(concept.prompt, "1:1"), "generated"
    except Exception as exc:  # noqa: BLE001 - safety refusal / API error → try fallback
        if concept.fallback_prompt:
            try:
                notes.append(f"concept {concept.name!r}: primary refused, used fallback")
                return image_generator(concept.fallback_prompt, "1:1"), "generated-fallback"
            except Exception as exc2:  # noqa: BLE001 - record and skip the concept
                notes.append(f"concept {concept.name!r}: generation failed ({exc2})")
                return None, "generated"
        notes.append(f"concept {concept.name!r}: generation failed ({exc})")
        return None, "generated"


def generate_ad_creative(
    *,
    product_id: str,
    out_dir: Path,
    concepts: Sequence[CreativeConcept] = (),
    client_photos: Sequence[Path] = (),
    promo_headlines: Sequence[str] = (),
    aspect_ratios: Sequence[str] = DEFAULT_ASPECTS,
    image_generator: ImageGenerator | None = None,
    make_overlays: bool = True,
) -> CreativeResult:
    """Produce ad creative for a client into ``out_dir`` (idempotent).

    Backgrounds come from ``client_photos`` when present, else are generated from
    ``concepts``. Each background is cover-fit to every requested aspect ratio as a
    clean, text-free image. When ``make_overlays`` and ``promo_headlines`` are
    given, a headline is also burned onto a copy (promo graphic) in the upright
    formats. Returns the asset manifest + provenance notes.
    """
    for ar in aspect_ratios:
        if ar not in AD_ASPECT_SIZES:
            raise ValueError(f"unknown aspect ratio {ar!r}; known: {sorted(AD_ASPECT_SIZES)}")

    generator = image_generator or _default_image_generator()
    notes: list[str] = []
    backgrounds = _materialize_backgrounds(
        out_dir=out_dir,
        concepts=concepts,
        client_photos=client_photos,
        image_generator=generator,
        notes=notes,
    )

    assets: list[CreativeAsset] = []
    for bg in backgrounds:
        with Image.open(bg.path) as img:
            base = img.copy()
        for ar in aspect_ratios:
            dest = out_dir / f"{bg.name}__{ar.replace(':', 'x')}.jpg"
            _save_fitted(base, ar, dest)
            assets.append(CreativeAsset(bg.name, ar, str(dest), bg.source))

    if make_overlays and promo_headlines:
        assets.extend(_overlay_assets(out_dir, backgrounds, promo_headlines, aspect_ratios))

    return CreativeResult(product_id=product_id, assets=assets, notes=notes)


def _overlay_assets(
    out_dir: Path,
    backgrounds: list[_Background],
    promo_headlines: Sequence[str],
    aspect_ratios: Sequence[str],
) -> list[CreativeAsset]:
    """Burn promo headlines onto backgrounds (upright formats only)."""
    from packages.tools.content_tools.text_overlay import SlideTextConfig, overlay_text

    overlay_dir = out_dir / "promo"
    aspects = [a for a in aspect_ratios if a in _OVERLAY_ASPECTS] or ["1:1"]
    out: list[CreativeAsset] = []
    for bg in backgrounds:
        headline = bg.headline or promo_headlines[0]
        for ar in aspects:
            dest = overlay_dir / f"{bg.name}__{ar.replace(':', 'x')}__promo.jpg"
            dest.parent.mkdir(parents=True, exist_ok=True)
            overlay_text(
                bg.path,
                SlideTextConfig(headline=headline),
                dest,
                target_size=AD_ASPECT_SIZES[ar],
            )
            out.append(CreativeAsset(bg.name, ar, str(dest), bg.source, overlay=True))
    return out
