from pathlib import Path

from PIL import Image, ImageDraw

from packages.home_from_working.assets import AssetStandard, inspect_asset


def _image(path: Path, mode: str, size: tuple[int, int], *, opaque: bool = False) -> None:
    if mode == "RGBA":
        alpha = 255 if opaque else 0
        image = Image.new(mode, size, (255, 0, 0, alpha))
        if not opaque:
            draw = ImageDraw.Draw(image)
            draw.rectangle(
                (size[0] // 4, size[1] // 4, size[0] * 3 // 4, size[1] * 3 // 4),
                fill=(255, 0, 0, 255),
            )
    else:
        image = Image.new(mode, size, "white")
    image.save(path)


def test_missing_asset_is_blocked_not_crash(tmp_path):
    result = inspect_asset(tmp_path / "missing.png")
    assert result["status"] == "blocked_missing_file"


def test_asset_requires_transparency_dimensions_and_effective_dpi(tmp_path):
    path = tmp_path / "small-opaque.png"
    _image(path, "RGB", (1000, 1000))
    result = inspect_asset(path, AssetStandard(min_width=2000, min_height=2000, print_width_inches=12, min_effective_dpi=150))
    assert result["checks"]["dimensions"] == "fail"
    assert result["checks"]["transparency"] == "fail"
    assert result["checks"]["effective_dpi"] == "fail"
    assert result["status"] == "fail"


def test_valid_transparent_production_master_passes_and_hashes(tmp_path):
    path = tmp_path / "master.png"
    _image(path, "RGBA", (2400, 2400))
    result = inspect_asset(path, AssetStandard(min_width=2000, min_height=2000, print_width_inches=12, min_effective_dpi=150))
    assert result["status"] == "pass"
    assert result["checks"] == {
        "file_type": "pass",
        "dimensions": "pass",
        "transparency": "pass",
        "effective_dpi": "pass",
        "nonempty_artwork": "pass",
        "content_padding": "pass",
    }
    assert len(result["sha256"]) == 64


def test_recorded_hash_must_match_inspected_file(tmp_path):
    path = tmp_path / "master.png"
    _image(path, "RGBA", (2400, 2400))

    result = inspect_asset(path, recorded_sha256="0" * 64)

    assert result["checks"]["hash_integrity"] == "fail"
    assert result["status"] == "fail"


def test_ai_hero_manifest_must_be_labeled_as_illustrative(tmp_path):
    path = tmp_path / "master.png"
    _image(path, "RGBA", (2400, 2400))
    result = inspect_asset(path, hero_manifest={"source": "ai", "illustrative_mockup": False})
    assert result["hero_image_check"] == "fail_misrepresentation_risk"


def test_ai_hero_manifest_requires_no_misrepresentation_note(tmp_path):
    path = tmp_path / "master.png"
    _image(path, "RGBA", (2400, 2400))

    missing = inspect_asset(
        path,
        hero_manifest={"source": "ai", "illustrative_mockup": True},
    )
    complete = inspect_asset(
        path,
        hero_manifest={
            "source": "ai",
            "illustrative_mockup": True,
            "no_misrepresentation_note": (
                "Illustrative scene only; garment details are shown in product mockups."
            ),
        },
    )

    assert missing["hero_image_check"] == "fail_missing_no_misrepresentation_note"
    assert missing["status"] == "fail"
    assert complete["hero_image_check"] == "pass_illustrative_mockup_disclosed"


def test_no_hero_manifest_is_explicitly_not_applicable(tmp_path):
    path = tmp_path / "master.png"
    _image(path, "RGBA", (2400, 2400))

    result = inspect_asset(path)

    assert result["hero_image_check"] == "not_applicable_no_manifest"
