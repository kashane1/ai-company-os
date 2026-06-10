"""Genre art-direction kits — the durable, per-genre design recipe.

A *kit* is the compounding asset behind the web lane. The lesson from real builds
(med-spa, fish-tacos, café) is that **images generated to a specific reference +
palette beat anything pulled off a shelf** — stock dates fast and never matches the
next brand. So the asset worth keeping is the *recipe* that produces on-brief work,
not a warehouse of pixels: image direction, palette, type, composition, references —
plus a few exemplar images as proof.

A kit is a thin crystallization of contracts the design engine already has:

  - the build spec it pre-fills        -> ``packages.web.niches.niche_to_spec``
  - the art-direction packet it feeds  -> ``packages.web.design_studio``
  - exemplar provenance + clearance    -> ``packages.web.imagery`` (``ImageryManifest``)
  - palette + WCAG contrast            -> ``packages.web.palette``

Storage (tracked; **not** under a founder-approval boundary — those are only
``packages/policies``, ``packages/schemas``, ``skills/canonical``, ``skills/registry.yaml``)::

    packages/web/design_reference/kits/<slug>/
      kit.yaml        # the recipe (this module's KitRecipe)
      manifest.json   # exemplar provenance — a real ImageryManifest
      exemplars/*.webp
      reference.webp  # optional art-direction reference

Kit slugs are their OWN namespace, decoupled from the 20 ``GENRE_PALETTES`` keys: a
kit names its palette explicitly (``genre:massage_therapy`` or an explicit ``#hex``),
so a niche like ``med_spa`` can reuse the massage palette without being promoted to a
first-class genre. A kit may be **recipe-only** (no exemplars yet) — exemplars are
harvested from real builds, never fabricated speculatively.

The module is pure and import-light (yaml + the contracts above). Image staging uses
Pillow, imported lazily so the recipe/loader path stays dependency-free for tests.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field, replace
from pathlib import Path

import yaml

from packages.web.design_studio import DesignReference
from packages.web.imagery import (
    PROVENANCE_OWNER,
    ImageAsset,
    ImageryManifest,
    clearance_blockers,
)
from packages.web.palette import Palette, best_text_on, derive_palette, palette_for_genre

REPO = Path(__file__).resolve().parents[2]
KITS_ROOT = REPO / "packages" / "web" / "design_reference" / "kits"


# --------------------------------------------------------------------------- #
# Recipe + kit model
# --------------------------------------------------------------------------- #
@dataclass
class ImagePromptSet:
    """Per-role ChatGPT image prompts — the durable, validated generation asset.

    Generate + ingest in ``ingest_sequence`` order: hero, bento…, **band LAST**. The
    composer (``packages.web.blocks_composer``) reserves the last supporting image for
    the full-bleed band, so the band prompt must be ingested last via
    ``scripts/web/ingest_images.py``. Prompts are self-contained text (no live URLs — a
    URL triggers a web-search loop in the Instant model).
    """

    hero: str = ""
    bento: list[str] = field(default_factory=list)
    band: str = ""

    def to_dict(self) -> dict:
        return {"hero": self.hero, "bento": list(self.bento), "band": self.band}

    @classmethod
    def from_dict(cls, payload: dict | None) -> ImagePromptSet:
        payload = payload or {}
        return cls(
            hero=str(payload.get("hero", "")),
            bento=[str(b) for b in payload.get("bento", [])],
            band=str(payload.get("band", "")),
        )

    def ingest_sequence(self) -> list[tuple[str, str]]:
        """(label, prompt) in generate/ingest order: hero, bento…, band LAST."""

        seq: list[tuple[str, str]] = []
        if self.hero:
            seq.append(("hero", self.hero))
        for i, prompt in enumerate(self.bento, 1):
            seq.append((f"bento-{i}", prompt))
        if self.band:
            seq.append(("band", self.band))
        return seq


@dataclass
class KitRecipe:
    """The durable per-genre recipe — everything except the exemplar pixels.

    ``palette`` is either a ``genre:<key>`` reference into ``GENRE_PALETTES`` or an
    explicit ``#rrggbb`` brand color the synthesizer derives from. ``niche_aliases``
    are substring keys (mirrors the needle lists in ``packages.web.niches``) so a free-
    text niche resolves to this kit.
    """

    slug: str
    display_name: str
    niche_aliases: list[str] = field(default_factory=list)
    concept_statement: str = ""
    palette: str = ""  # "genre:<key>" or "#rrggbb"
    accent: str = ""  # optional explicit accent hex (overrides the palette's accent)
    type_vibe: str = ""  # a vibe from design_reference/font_pairings.md (mood-board fonts)
    concept_type: str = ""  # free-text type steer passed through as the engine's concept_type
    imagery_direction: str = ""
    composition_rules: list[str] = field(default_factory=list)
    image_prompts: ImagePromptSet = field(default_factory=ImagePromptSet)
    references: list[DesignReference] = field(default_factory=list)
    evidence_hints: list[str] = field(default_factory=list)
    harvested_from: list[str] = field(default_factory=list)
    version: int = 1

    def to_dict(self) -> dict:
        payload = asdict(self)
        payload["references"] = [
            r.to_dict() if isinstance(r, DesignReference) else dict(r) for r in self.references
        ]
        return payload

    @classmethod
    def from_dict(cls, payload: dict) -> KitRecipe:
        refs = [
            DesignReference(
                title=str(r["title"]),
                url=str(r.get("url", "")),
                source_type=str(r.get("source_type", "reference")),
                takeaways=list(r.get("takeaways", [])),
            )
            for r in payload.get("references", [])
        ]
        return cls(
            slug=str(payload["slug"]),
            display_name=str(payload.get("display_name", payload["slug"])),
            niche_aliases=list(payload.get("niche_aliases", [])),
            concept_statement=str(payload.get("concept_statement", "")),
            palette=str(payload.get("palette", "")),
            accent=str(payload.get("accent", "")),
            type_vibe=str(payload.get("type_vibe", "")),
            concept_type=str(payload.get("concept_type", "")),
            imagery_direction=str(payload.get("imagery_direction", "")),
            composition_rules=list(payload.get("composition_rules", [])),
            image_prompts=ImagePromptSet.from_dict(payload.get("image_prompts")),
            references=refs,
            evidence_hints=list(payload.get("evidence_hints", [])),
            harvested_from=list(payload.get("harvested_from", [])),
            version=int(payload.get("version", 1)),
        )


@dataclass
class GenreKit:
    """In-memory join of a recipe + its exemplar provenance + on-disk location.

    Exemplar provenance is a real ``ImageryManifest`` (not inlined into the YAML), so
    ``clearance_blockers`` and the deploy guard work on a kit's images unchanged.
    """

    recipe: KitRecipe
    manifest: ImageryManifest
    dir: Path


# --------------------------------------------------------------------------- #
# Storage
# --------------------------------------------------------------------------- #
def kits_root() -> Path:
    return KITS_ROOT


def kit_dir(slug: str) -> Path:
    return KITS_ROOT / slug


def list_kits() -> list[str]:
    """Slugs of every kit on disk (a kit is any dir with a ``kit.yaml``)."""

    if not KITS_ROOT.is_dir():
        return []
    return sorted(p.name for p in KITS_ROOT.iterdir() if (p / "kit.yaml").is_file())


def load_kit(slug: str) -> GenreKit | None:
    """Load a kit by slug, or ``None`` if there's no recipe for it."""

    directory = kit_dir(slug)
    recipe_path = directory / "kit.yaml"
    if not recipe_path.is_file():
        return None
    recipe = KitRecipe.from_dict(yaml.safe_load(recipe_path.read_text()) or {})
    manifest_path = directory / "manifest.json"
    manifest = ImageryManifest.load(manifest_path) if manifest_path.is_file() else ImageryManifest()
    return GenreKit(recipe=recipe, manifest=manifest, dir=directory)


def find_kit_for_niche(niche: str) -> GenreKit | None:
    """The first kit whose ``niche_aliases`` substring-match ``niche`` (lowercased)."""

    key = niche.strip().lower()
    if not key:
        return None
    for slug in list_kits():
        kit = load_kit(slug)
        if kit and any(alias.strip().lower() in key for alias in kit.recipe.niche_aliases):
            return kit
    return None


def save_recipe(recipe: KitRecipe) -> Path:
    """Persist a recipe to ``<kit>/kit.yaml`` (creates the kit dir)."""

    directory = kit_dir(recipe.slug)
    directory.mkdir(parents=True, exist_ok=True)
    out = directory / "kit.yaml"
    out.write_text(yaml.safe_dump(recipe.to_dict(), sort_keys=False, allow_unicode=True))
    return out


def save_manifest(slug: str, manifest: ImageryManifest) -> Path:
    """Persist a kit's exemplar provenance to ``<kit>/manifest.json``."""

    return manifest.save(kit_dir(slug) / "manifest.json")


# --------------------------------------------------------------------------- #
# Palette + exemplar resolution
# --------------------------------------------------------------------------- #
def kit_palette(kit: GenreKit) -> Palette:
    """Resolve the kit's palette: a ``genre:`` reference, else derive from a hex.

    An explicit ``recipe.accent`` overrides the resolved palette's accent (its
    on-color is recomputed for WCAG legibility).
    """

    ref = (kit.recipe.palette or "").strip()
    base: Palette | None = None
    if ref.startswith("genre:"):
        base = palette_for_genre(ref.split(":", 1)[1].strip())
    if base is None:
        seed = ref if ref.startswith("#") else (kit.recipe.accent or "#334155")
        base = derive_palette(seed)
    accent = (kit.recipe.accent or "").strip()
    if accent.startswith("#"):
        base = replace(base, accent=accent, on_accent=best_text_on(accent))
    return base


def exemplar_paths(kit: GenreKit, *, selected_only: bool = True) -> list[Path]:
    """Absolute paths to the kit's exemplar images (relative manifest paths are
    resolved against the kit dir)."""

    paths: list[Path] = []
    for asset in kit.manifest.assets:
        if selected_only and not asset.selected:
            continue
        path = Path(asset.path)
        paths.append(path if path.is_absolute() else kit.dir / path)
    return paths


# --------------------------------------------------------------------------- #
# Spec overlay — the build "first draft" (Idea 1)
# --------------------------------------------------------------------------- #
def apply_kit_to_spec(spec: dict, kit: GenreKit) -> dict:
    """Overlay a kit's art-direction fields onto a build ``spec`` dict.

    The base ``spec`` carries the business framing (``site_name``/``audience``/``goal``/
    ``evidence``); the kit adds exactly the durable art direction the framing lacks —
    the validated concept line, the resolved palette + accent, and the imagery
    direction that makes generated shots on-brief. Returns a new dict consumable by
    ``scripts.agency.design_studio.request_from_spec`` unchanged. This is the single
    overlay used by both ``niches.niche_to_spec`` and the ``art_direction scaffold`` CLI
    (no parallel genre→spec catalog).
    """

    out = dict(spec)
    recipe = kit.recipe
    if recipe.concept_statement:
        out["concept_statement"] = recipe.concept_statement
    palette = kit_palette(kit)
    out["concept_palette"] = palette.primary
    out["accent"] = recipe.accent or palette.accent
    if recipe.imagery_direction:
        out["imagery_direction"] = recipe.imagery_direction
    if recipe.concept_type:
        out["concept_type"] = recipe.concept_type
    out.setdefault("imagery_mode", "concept-led")
    if recipe.references:
        out["references"] = [r.to_dict() for r in recipe.references] + list(
            out.get("references", [])
        )
    if not out.get("evidence") and recipe.evidence_hints:
        out["evidence"] = list(recipe.evidence_hints)
    out["kit"] = recipe.slug  # traceability; request_from_spec ignores unknown keys
    return out


def render_recipe_md(recipe: KitRecipe) -> str:
    """A readable brief for the human/agent — what the kit prescribes."""

    lines = [
        f"# Kit — {recipe.display_name} (`{recipe.slug}`)",
        "",
        f"**Concept:** {recipe.concept_statement}",
        f"**Palette:** {recipe.palette}" + (f" · accent {recipe.accent}" if recipe.accent else ""),
        f"**Type vibe:** {recipe.type_vibe}",
        f"**Concept type:** {recipe.concept_type}" if recipe.concept_type else "",
        f"**Niche aliases:** {', '.join(recipe.niche_aliases)}",
        "",
        "## Imagery direction",
        recipe.imagery_direction or "_(none yet)_",
        "",
        "## Composition rules",
        *[f"- {rule}" for rule in recipe.composition_rules],
        "",
    ]
    if recipe.references:
        lines.append("## References (translate, never copy)")
        for ref in recipe.references:
            lines.append(f"- **{ref.title}** {ref.url}".rstrip())
            lines += [f"  - {t}" for t in ref.takeaways]
        lines.append("")
    if recipe.evidence_hints:
        lines += [
            "## Evidence hints (replace with the business's own proof)",
            *[f"- {hint}" for hint in recipe.evidence_hints],
            "",
        ]
    sequence = recipe.image_prompts.ingest_sequence()
    if sequence:
        lines.append("## Image prompts (ChatGPT — generate + ingest in this order, band LAST)")
        lines += [f"- **{label}** — {prompt}" for label, prompt in sequence]
        lines.append("")
    trail = f" · harvested from {', '.join(recipe.harvested_from)}" if recipe.harvested_from else ""
    lines.append(f"_version {recipe.version}{trail}_")
    return "\n".join(lines)


# --------------------------------------------------------------------------- #
# Image staging — no-crop downscale to WebP (Pillow; lazy import)
# --------------------------------------------------------------------------- #
def stage_exemplar(src: Path, dest: Path, *, max_width: int = 1600, quality: int = 82) -> Path:
    """Downscale (NO crop) to ``max_width`` and WebP-encode ``src`` → ``dest``.

    Deliberately crop-free: ``scripts/web/make_thumb.py`` crops to a 4:3.1 top region
    for the BBW landing cards, which would decapitate a square exemplar. Returns ``dest``.
    """

    from PIL import Image  # lazy: keep the recipe/loader path import-free for tests

    dest.parent.mkdir(parents=True, exist_ok=True)
    with Image.open(src) as image:
        image = image.convert("RGB")
        if image.width > max_width:
            height = round(image.height * max_width / image.width)
            image = image.resize((max_width, height), Image.LANCZOS)
        image.save(dest, "WEBP", quality=quality, method=6)
    return dest


# --------------------------------------------------------------------------- #
# Harvest — grow the library from real builds (Idea 3), provenance-honest
# --------------------------------------------------------------------------- #
def _resolve_asset_file(path_str: str, hub: Path, imagery_dir: Path) -> Path:
    """Resolve a manifest asset's ``path`` to a real file.

    Build manifests store paths inconsistently — absolute (``ingest_images``) or
    repo-relative (``generate_imagery``) — so try each candidate and use the first that
    exists, falling back to the basename next to the manifest.
    """

    p = Path(path_str)
    candidates = [p] if p.is_absolute() else [REPO / path_str, hub / path_str]
    candidates.append(imagery_dir / p.name)
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    raise FileNotFoundError(
        f"cannot resolve exemplar source {path_str!r} (tried {[str(c) for c in candidates]})"
    )


def _refresh_recipe_from_packet(recipe: KitRecipe, hub: Path) -> None:
    """Fill *empty* recipe art-direction fields from a build's packet — never clobber
    a curated recipe."""

    import json

    packet_path = hub / "design-studio" / "packet.json"
    if not packet_path.is_file():
        return
    data = json.loads(packet_path.read_text())
    if not recipe.imagery_direction and data.get("imagery_direction"):
        recipe.imagery_direction = str(data["imagery_direction"])
    if not recipe.concept_statement and data.get("concept_statement"):
        recipe.concept_statement = str(data["concept_statement"])
    if not recipe.references and data.get("references"):
        recipe.references = [
            DesignReference(
                title=str(r["title"]),
                url=str(r.get("url", "")),
                source_type=str(r.get("source_type", "reference")),
                takeaways=list(r.get("takeaways", [])),
            )
            for r in data["references"]
        ]


def harvest_from_build(
    slug: str,
    build_hub: str | Path,
    *,
    exemplar_ids: list[str] | None = None,
    note: str = "",
    allow_uncleared: bool = False,
    allow_owner: bool = False,
) -> GenreKit:
    """Promote a real build's winning images into kit ``slug`` — the library grows from
    real work, not speculation.

    Copies the chosen exemplars (``exemplar_ids``, or all ``selected``) from
    ``<build_hub>/design-studio/imagery/manifest.json`` into the kit, **preserving each
    asset's provenance + clearance verbatim** (a ``generated`` asset stays ``generated`` —
    we never relabel to dodge the clearance gate). Empty recipe art-direction fields are
    filled from the build's ``packet.json``; ``harvested_from`` + ``version`` are updated.

    Provenance gates (honest by construction):
      * **uncleared generated** exemplars are refused unless ``allow_uncleared`` — and even
        then kept ``production_clearance=False`` so the deploy guard still catches them.
      * **owner** exemplars are refused unless ``allow_owner`` — a business's own photos are
        not ours to reuse on another client through a shared kit (explicit rights ack only).
    """

    kit = load_kit(slug)
    if kit is None:
        raise ValueError(f"no kit '{slug}' — write a kit.yaml recipe first, then harvest into it")
    hub = Path(build_hub)
    src_path = hub / "design-studio" / "imagery" / "manifest.json"
    if not src_path.is_file():
        raise FileNotFoundError(f"no build imagery manifest at {src_path}")
    source = ImageryManifest.load(src_path)

    by_id = {a.id: a for a in source.assets}
    if exemplar_ids is None:
        chosen = [a for a in source.assets if a.selected]
    else:
        missing = [i for i in exemplar_ids if i not in by_id]
        if missing:
            raise ValueError(f"build has no asset(s): {missing}")
        chosen = [by_id[i] for i in exemplar_ids]
    if not chosen:
        raise ValueError("no exemplars selected to harvest")

    blockers = set(clearance_blockers(source))
    uncleared = [a.id for a in chosen if a.id in blockers]
    if uncleared and not allow_uncleared:
        raise PermissionError(
            f"refusing uncleared generated exemplar(s) {uncleared}: clear them first "
            "(generate_imagery.py clear) or pass allow_uncleared=True (they stay uncleared "
            "in the kit, so the deploy guard still catches them)."
        )
    owners = [a.id for a in chosen if a.provenance == PROVENANCE_OWNER]
    if owners and not allow_owner:
        raise PermissionError(
            f"refusing owner exemplar(s) {owners}: a business's own photos are not ours to "
            "reuse on another client via a shared kit. Pass allow_owner=True only if these are "
            "operator-owned and licensed for reuse."
        )

    # Stage exemplars (no-crop WebP); replace-by-id, keep any existing kit exemplars.
    kept: dict[str, ImageAsset] = {a.id: a for a in kit.manifest.assets}
    for asset in chosen:
        source_file = _resolve_asset_file(asset.path, hub, src_path.parent)
        stage_exemplar(source_file, kit.dir / "exemplars" / f"{asset.id}.webp")
        kept[asset.id] = ImageAsset(
            id=asset.id,
            role=asset.role,
            path=f"exemplars/{asset.id}.webp",
            provenance=asset.provenance,  # verbatim — never relabel
            prompt=asset.prompt,
            seed=asset.seed,
            selected=True,
            production_clearance=asset.production_clearance,
            cleared_by=asset.cleared_by,
        )
    save_manifest(slug, ImageryManifest(assets=list(kept.values())))

    recipe = kit.recipe
    entry = f"{build_hub} — {note}" if note else str(build_hub)
    if entry not in recipe.harvested_from:
        recipe.harvested_from.append(entry)
    recipe.version += 1
    _refresh_recipe_from_packet(recipe, hub)
    save_recipe(recipe)
    return load_kit(slug)
