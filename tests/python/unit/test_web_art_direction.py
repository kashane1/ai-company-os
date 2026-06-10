"""Tests for genre art-direction kits (the durable per-genre design recipe).

Locks the testable core: recipe YAML round-trip, the recipe+manifest join, palette
resolution (genre ref / hex / accent override), exemplar-path resolution, niche
matching, and that the two seeded kits load with honest provenance. Image staging
(Pillow→WebP) is covered with a generated fixture so no real asset is needed.
"""

from __future__ import annotations

import pytest

from packages.web import art_direction as ad
from packages.web.design_studio import DesignReference
from packages.web.imagery import (
    PROVENANCE_OWNER,
    ImageAsset,
    ImageryManifest,
    clearance_blockers,
)
from packages.web.palette import GENRE_PALETTES


def _recipe(**over) -> ad.KitRecipe:
    base = dict(
        slug="demo_kit",
        display_name="Demo Kit",
        niche_aliases=["demo", "sample studio"],
        concept_statement="quiet craft",
        palette="genre:coffee_shop",
        type_vibe="warm",
        imagery_direction="warm morning light",
        composition_rules=["Hero: the room at golden hour."],
        references=[
            DesignReference(title="Ref", url="", source_type="direction", takeaways=["a", "b"])
        ],
        evidence_hints=["a real proof point"],
    )
    base.update(over)
    return ad.KitRecipe(**base)


def test_recipe_round_trips_through_dict() -> None:
    recipe = _recipe()
    again = ad.KitRecipe.from_dict(recipe.to_dict())
    assert again.slug == "demo_kit"
    assert again.niche_aliases == ["demo", "sample studio"]
    assert again.composition_rules == ["Hero: the room at golden hour."]
    # References survive as DesignReference with their takeaways intact.
    assert again.references[0].title == "Ref"
    assert again.references[0].takeaways == ["a", "b"]


def test_save_recipe_and_load_kit_round_trip(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(ad, "KITS_ROOT", tmp_path)
    ad.save_recipe(_recipe())
    # A recipe with no manifest.json loads as a recipe-only kit (empty manifest).
    kit = ad.load_kit("demo_kit")
    assert kit is not None
    assert kit.recipe.display_name == "Demo Kit"
    assert kit.manifest.assets == []
    assert ad.list_kits() == ["demo_kit"]


def test_load_kit_unknown_slug_returns_none(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(ad, "KITS_ROOT", tmp_path)
    assert ad.load_kit("nope") is None
    assert ad.list_kits() == []


def test_kit_palette_resolves_genre_reference(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(ad, "KITS_ROOT", tmp_path)
    ad.save_recipe(_recipe(palette="genre:coffee_shop"))
    kit = ad.load_kit("demo_kit")
    assert ad.kit_palette(kit) == GENRE_PALETTES["coffee_shop"]


def test_kit_palette_derives_from_hex_and_applies_accent_override(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(ad, "KITS_ROOT", tmp_path)
    ad.save_recipe(_recipe(palette="#2E5A4B", accent="#E8557A"))
    kit = ad.load_kit("demo_kit")
    palette = ad.kit_palette(kit)
    # Derived from the brand hex; the explicit accent overrides and stays AA-legible.
    assert palette.primary.lower() == "#2e5a4b"
    assert palette.accent == "#E8557A"
    from packages.web.palette import contrast_ratio

    assert contrast_ratio(palette.on_accent, palette.accent) >= 4.5


def test_exemplar_paths_resolve_relative_against_kit_dir(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(ad, "KITS_ROOT", tmp_path)
    ad.save_recipe(_recipe())
    ad.save_manifest(
        "demo_kit",
        ImageryManifest(
            assets=[
                ImageAsset(
                    id="hero", role="hero", path="exemplars/hero.webp", provenance=PROVENANCE_OWNER
                ),
                ImageAsset(id="drop", role="supporting", path="exemplars/drop.webp",
                           provenance=PROVENANCE_OWNER, selected=False),
            ]
        ),
    )
    kit = ad.load_kit("demo_kit")
    paths = ad.exemplar_paths(kit)  # selected only
    assert len(paths) == 1
    assert paths[0] == ad.kit_dir("demo_kit") / "exemplars/hero.webp"
    assert paths[0].is_absolute()
    assert len(ad.exemplar_paths(kit, selected_only=False)) == 2


def test_find_kit_for_niche_matches_aliases(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(ad, "KITS_ROOT", tmp_path)
    ad.save_recipe(_recipe(slug="med_spa", niche_aliases=["med spa", "botox", "injectable"]))
    assert ad.find_kit_for_niche("a luxe MED SPA downtown").recipe.slug == "med_spa"
    assert ad.find_kit_for_niche("plumbing") is None
    assert ad.find_kit_for_niche("") is None


def test_stage_exemplar_no_crop_downscales_to_webp(tmp_path) -> None:
    Image = pytest.importorskip("PIL.Image")
    src = tmp_path / "src.png"
    Image.new("RGB", (3000, 2000), (40, 90, 75)).save(src)
    dest = ad.stage_exemplar(src, tmp_path / "out" / "hero.webp", max_width=1600)
    assert dest.is_file()
    with Image.open(dest) as out:
        assert out.format == "WEBP"
        # No crop: aspect ratio preserved (3:2), just downscaled to max_width.
        assert out.width == 1600
        assert out.height == round(2000 * 1600 / 3000)


# --- the two seeded kits (integration against the real on-disk library) --------- #
def test_seeded_kits_load_with_honest_provenance() -> None:
    slugs = ad.list_kits()
    assert {"med_spa", "fish_tacos"} <= set(slugs)

    # med_spa is the validated sage recipe: an explicit hex seed + explicit accent
    # (the accent is the key control that stops the engine's default bright complement).
    med = ad.load_kit("med_spa")
    assert med.recipe.palette == "#869178"
    assert med.recipe.accent == "#6F7D58"
    assert len(ad.exemplar_paths(med)) == 3
    assert all(p.is_file() for p in ad.exemplar_paths(med))
    assert clearance_blockers(med.manifest) == []  # owner-cleared, never blocks

    fish = ad.load_kit("fish_tacos")
    assert fish.recipe.palette == "#C8553D"
    assert len(ad.exemplar_paths(fish)) == 5
    # The band image is generated + ingested LAST (the composer reserves the last image).
    assert fish.recipe.image_prompts.ingest_sequence()[-1][0] == "band"


# --- per-role image prompts (the durable generation asset) --------------------- #
def test_image_prompt_set_round_trip_and_band_last_order() -> None:
    prompts = ad.ImagePromptSet(hero="H", bento=["B1", "B2"], band="BAND")
    again = ad.ImagePromptSet.from_dict(prompts.to_dict())
    assert (again.hero, again.bento, again.band) == ("H", ["B1", "B2"], "BAND")
    # generate/ingest order: hero, bento…, band LAST.
    labels = [label for label, _ in prompts.ingest_sequence()]
    assert labels == ["hero", "bento-1", "bento-2", "band"]
    assert prompts.ingest_sequence()[-1] == ("band", "BAND")


def test_recipe_round_trip_preserves_concept_type_and_prompts() -> None:
    recipe = _recipe(
        concept_type="refined serif display",
        image_prompts=ad.ImagePromptSet(hero="H", bento=["B"], band="BD"),
    )
    again = ad.KitRecipe.from_dict(recipe.to_dict())
    assert again.concept_type == "refined serif display"
    assert (again.image_prompts.hero, again.image_prompts.bento, again.image_prompts.band) == (
        "H", ["B"], "BD",
    )


# --- Idea 1: spec overlay (the build first draft) ------------------------------ #
def _overlay_kit() -> ad.GenreKit:
    return ad.GenreKit(
        recipe=ad.KitRecipe(
            slug="overlay_demo",
            display_name="Overlay Demo",
            palette="genre:coffee_shop",
            concept_statement="the morning ritual",
            imagery_direction="warm, lived-in",
            type_vibe="warm",
            concept_type="warm editorial serif",
            references=[
                DesignReference(title="R", url="", source_type="direction", takeaways=["t"])
            ],
            evidence_hints=["the regulars"],
        ),
        manifest=ImageryManifest(),
        dir=ad.kits_root() / "overlay_demo",
    )


def test_apply_kit_to_spec_overlays_art_direction() -> None:
    base = {
        "site_name": "Bean", "business_category": "coffee", "audience": "locals", "goal": "visits"
    }
    spec = ad.apply_kit_to_spec(base, _overlay_kit())
    assert spec["concept_statement"] == "the morning ritual"
    assert spec["concept_palette"] == GENRE_PALETTES["coffee_shop"].primary
    assert spec["accent"] == GENRE_PALETTES["coffee_shop"].accent
    assert spec["imagery_direction"] == "warm, lived-in"
    assert spec["concept_type"] == "warm editorial serif"  # passed through to the engine
    assert spec["imagery_mode"] == "concept-led"
    assert spec["references"][0]["title"] == "R"
    assert spec["evidence"] == ["the regulars"]  # base had none → kit hints fill it
    assert spec["kit"] == "overlay_demo"
    assert "kit" not in base  # base spec is not mutated


def test_apply_kit_to_spec_keeps_base_evidence_and_prepends_refs() -> None:
    base = {
        "site_name": "X", "business_category": "coffee", "audience": "a", "goal": "g",
        "evidence": ["real proof"], "references": [{"title": "existing", "takeaways": []}],
    }
    spec = ad.apply_kit_to_spec(base, _overlay_kit())
    assert spec["evidence"] == ["real proof"]  # a real business's evidence wins
    assert [r["title"] for r in spec["references"]] == ["R", "existing"]  # kit refs lead


def test_render_recipe_md_has_key_sections() -> None:
    md = ad.render_recipe_md(_overlay_kit().recipe)
    assert "# Kit — Overlay Demo" in md
    assert "Imagery direction" in md
    assert "the morning ritual" in md


def test_niche_to_spec_enriches_from_real_kits() -> None:
    # Integration against the seeded library: a matching niche gets kit fields; a
    # non-matching niche is the untouched base spec (legacy path unaffected).
    from packages.web.niches import niche_to_spec

    med = niche_to_spec("a luxe med spa downtown")
    assert med["kit"] == "med_spa"
    assert med["imagery_direction"]
    assert med["concept_palette"] == "#869178"  # validated sage seed
    assert med["accent"] == "#6F7D58"
    assert med["concept_type"]  # passed through from the kit

    fish = niche_to_spec("a baja fish taco shop")
    assert fish["kit"] == "fish_tacos"

    plain = niche_to_spec("emergency plumbing")
    assert "kit" not in plain


# --- Idea 3: harvest (provenance-honest) --------------------------------------- #
def _build_hub(tmp_path, assets):
    """A fake build hub with real (tiny) image files + an imagery manifest."""

    Image = pytest.importorskip("PIL.Image")
    hub = tmp_path / "build"
    img_dir = hub / "design-studio" / "imagery"
    img_dir.mkdir(parents=True)
    built = []
    for spec in assets:
        path = img_dir / f"{spec['id']}.png"
        Image.new("RGB", (640, 640), (110, 70, 40)).save(path)
        built.append(
            ImageAsset(
                id=spec["id"], role=spec.get("role", "supporting"), path=str(path),
                provenance=spec["provenance"], selected=spec.get("selected", True),
                production_clearance=spec.get("cleared", False), cleared_by=spec.get("by", ""),
            )
        )
    ImageryManifest(assets=built).save(img_dir / "manifest.json")
    return hub


def _seed_recipe_only_kit(monkeypatch, tmp_path, slug="cafe"):
    monkeypatch.setattr(ad, "KITS_ROOT", tmp_path / "kits")
    ad.save_recipe(ad.KitRecipe(slug=slug, display_name="Cafe", palette="genre:coffee_shop"))
    ad.save_manifest(slug, ImageryManifest())


def test_harvest_preserves_provenance_and_updates_recipe(tmp_path, monkeypatch) -> None:
    _seed_recipe_only_kit(monkeypatch, tmp_path)
    hub = _build_hub(tmp_path, [
        {"id": "hero", "role": "hero", "provenance": "generated", "cleared": True, "by": "founder"},
        {"id": "s1", "provenance": "licensed"},
    ])
    kit = ad.harvest_from_build("cafe", hub)
    by_id = {a.id: a for a in kit.manifest.assets}
    assert set(by_id) == {"hero", "s1"}
    assert by_id["hero"].provenance == "generated"  # never relabeled to owner
    assert by_id["hero"].production_clearance is True  # clearance preserved verbatim
    assert by_id["hero"].path == "exemplars/hero.webp"
    assert (kit.dir / "exemplars" / "hero.webp").is_file()
    assert kit.recipe.version == 2  # bumped
    assert any(str(hub) in entry for entry in kit.recipe.harvested_from)


def test_harvest_refuses_uncleared_generated_but_never_launders(tmp_path, monkeypatch) -> None:
    _seed_recipe_only_kit(monkeypatch, tmp_path)
    # 'hero' is generated + uncleared (no production_clearance).
    hub = _build_hub(tmp_path, [{"id": "hero", "role": "hero", "provenance": "generated"}])
    with pytest.raises(PermissionError, match="uncleared generated"):
        ad.harvest_from_build("cafe", hub)
    # --allow-uncleared lets it in but keeps it uncleared, so the gate still catches it.
    kit = ad.harvest_from_build("cafe", hub, allow_uncleared=True)
    hero = kit.manifest.assets[0]
    assert hero.provenance == "generated"
    assert hero.production_clearance is False
    assert clearance_blockers(kit.manifest) == ["hero"]


def test_harvest_refuses_owner_photos_by_default(tmp_path, monkeypatch) -> None:
    _seed_recipe_only_kit(monkeypatch, tmp_path)
    hub = _build_hub(tmp_path, [{"id": "hero", "role": "hero", "provenance": "owner"}])
    with pytest.raises(PermissionError, match="owner"):
        ad.harvest_from_build("cafe", hub)
    kit = ad.harvest_from_build("cafe", hub, allow_owner=True)
    assert kit.manifest.assets[0].provenance == "owner"


def test_harvest_into_unknown_kit_raises(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(ad, "KITS_ROOT", tmp_path / "kits")
    hub = _build_hub(tmp_path, [{"id": "hero", "role": "hero", "provenance": "licensed"}])
    with pytest.raises(ValueError, match="no kit"):
        ad.harvest_from_build("ghost", hub)


def test_harvest_explicit_ids_and_missing(tmp_path, monkeypatch) -> None:
    _seed_recipe_only_kit(monkeypatch, tmp_path)
    hub = _build_hub(tmp_path, [
        {"id": "hero", "role": "hero", "provenance": "licensed"},
        {"id": "s1", "provenance": "licensed"},
    ])
    kit = ad.harvest_from_build("cafe", hub, exemplar_ids=["hero"])
    assert {a.id for a in kit.manifest.assets} == {"hero"}
    with pytest.raises(ValueError, match="no asset"):
        ad.harvest_from_build("cafe", hub, exemplar_ids=["nope"])
