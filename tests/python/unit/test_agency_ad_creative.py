"""Ad creative generation: real-photo-first, AI fallback, promo overlays."""

from __future__ import annotations

import io
from pathlib import Path

import pytest
from PIL import Image

from packages.agency.ad_creative import (
    AD_ASPECT_SIZES,
    CreativeConcept,
    generate_ad_creative,
)


def _png_bytes(color=(120, 140, 160)) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (640, 640), color).save(buf, format="PNG")
    return buf.getvalue()


def _write_photo(path: Path, color=(10, 20, 30)) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (800, 600), color).save(path, format="JPEG")
    return path


def _fake_generator(calls: list[str]):
    def _gen(prompt: str, aspect_ratio: str) -> bytes:
        calls.append(prompt)
        return _png_bytes()

    return _gen


def test_generates_when_no_client_photos(tmp_path: Path) -> None:
    calls: list[str] = []
    concepts = [
        CreativeConcept("lifestyle", "a tidy modern kitchen, warm light", headline="Book Today"),
        CreativeConcept("service", "tools on a clean workbench", headline="Free Estimates"),
    ]
    result = generate_ad_creative(
        product_id="joe-site",
        out_dir=tmp_path,
        concepts=concepts,
        promo_headlines=["Spring Special"],
        image_generator=_fake_generator(calls),
    )
    # Two concepts generated.
    assert len(calls) == 2
    clean = [a for a in result.assets if not a.overlay]
    # 2 concepts x 4 aspect ratios clean images.
    assert len(clean) == 2 * len(AD_ASPECT_SIZES)
    assert {a.source for a in clean} == {"generated"}
    # Every clean asset exists on disk at the right pixel size.
    for a in clean:
        with Image.open(a.path) as img:
            assert img.size == AD_ASPECT_SIZES[a.aspect_ratio]
    # Promo overlays were produced (upright formats only).
    assert any(a.overlay for a in result.assets)


def test_real_photos_first_skips_generation(tmp_path: Path) -> None:
    calls: list[str] = []
    photo = _write_photo(tmp_path / "src" / "storefront.jpg")
    result = generate_ad_creative(
        product_id="joe-site",
        out_dir=tmp_path / "out",
        concepts=[CreativeConcept("x", "should not be used")],
        client_photos=[photo],
        image_generator=_fake_generator(calls),
    )
    assert calls == []  # no AI generation when a real photo exists
    assert {a.source for a in result.assets if not a.overlay} == {"client-photo"}
    assert any("client photo" in n for n in result.notes)


def test_falls_back_to_secondary_prompt_on_refusal(tmp_path: Path) -> None:
    def _gen(prompt: str, aspect_ratio: str) -> bytes:
        if "REFUSE" in prompt:
            raise RuntimeError("safety filter refused")
        return _png_bytes()

    result = generate_ad_creative(
        product_id="joe-site",
        out_dir=tmp_path,
        concepts=[CreativeConcept("c", "REFUSE this", fallback_prompt="safe neutral scene")],
        image_generator=_gen,
        make_overlays=False,
    )
    assert {a.source for a in result.assets} == {"generated-fallback"}
    assert any("used fallback" in n for n in result.notes)


def test_concept_skipped_when_both_prompts_fail(tmp_path: Path) -> None:
    def _gen(prompt: str, aspect_ratio: str) -> bytes:
        raise RuntimeError("always fails")

    result = generate_ad_creative(
        product_id="joe-site",
        out_dir=tmp_path,
        concepts=[CreativeConcept("c", "primary", fallback_prompt="fallback")],
        image_generator=_gen,
        make_overlays=False,
    )
    assert result.assets == []
    assert any("generation failed" in n for n in result.notes)


def test_idempotent_reruns(tmp_path: Path) -> None:
    photo = _write_photo(tmp_path / "p.jpg")
    kwargs = dict(product_id="joe-site", out_dir=tmp_path / "out", client_photos=[photo])
    first = generate_ad_creative(**kwargs)
    second = generate_ad_creative(**kwargs)
    assert len(first.assets) == len(second.assets)
    # Same filenames overwritten, not duplicated.
    jpgs = list((tmp_path / "out").glob("*.jpg"))
    assert len(jpgs) == len([a for a in second.assets if not a.overlay])


def test_unknown_aspect_ratio_raises(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="unknown aspect ratio"):
        generate_ad_creative(
            product_id="x",
            out_dir=tmp_path,
            client_photos=[_write_photo(tmp_path / "p.jpg")],
            aspect_ratios=["2:3"],
        )


def test_no_photos_and_no_concepts_raises(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="nothing to make creative from"):
        generate_ad_creative(product_id="x", out_dir=tmp_path)
