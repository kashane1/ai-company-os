"""Guardrails for reusing a Printify product through native Duplicate."""

from __future__ import annotations

from copy import deepcopy

import pytest

from packages.pod.template import (
    DraftError,
    artwork_placement,
    assert_native_copy,
    make_print_areas,
    mockup_signature,
    verify_update,
)


def test_305_percent_portrait_matches_editor_dimensions_and_dpi():
    placement = artwork_placement(1024, 1536, 305)
    assert placement['width_inches'] == pytest.approx(10.4106666667)
    assert placement['height_inches'] == pytest.approx(15.616)
    assert placement['dpi'] == 98.4
    assert placement['applied_scale_percent'] == pytest.approx(305)
    assert placement['x'] == placement['y'] == .5


@pytest.mark.parametrize('width,height', [(1536, 1024), (1024, 3000)])
def test_large_scale_fits_print_area_without_cropping(width, height):
    placement = artwork_placement(width, height, 305)
    assert placement['width_inches'] <= 3951 / 300
    assert placement['height_inches'] <= 4919 / 300
    assert placement['width_inches'] / placement['height_inches'] == pytest.approx(width / height)
    assert placement['applied_scale_percent'] < 305


@pytest.mark.parametrize('value', [0, -1, float('nan'), float('inf'), True])
def test_invalid_scale_is_rejected(value):
    with pytest.raises(DraftError, match='scale percent'):
        artwork_placement(1024, 1536, value)


def _mockup(camera: int, *, default: bool = False, order: int | None = None) -> dict:
    return {
        "mockup_id": f"product_12_{camera}",
        "src": (
            f"https://images.printify.com/mockup/product/12/{camera}/old-title.jpg"
            f"?camera_label=camera-{camera}"
        ),
        "variant_ids": [3, 1],
        "position": "front" if default else "other",
        "is_default": default,
        "is_selected_for_publishing": True,
        "order": order,
    }


def _product(product_id: str, *, sku_prefix: str = "source", published: bool = False) -> dict:
    return {
        "id": product_id,
        "shop_id": 28779955,
        "blueprint_id": 6,
        "print_provider_id": 99,
        "visible": True,
        "is_locked": False,
        "is_deleted": False,
        "title": "Old title",
        "description": "Old description",
        "tags": ["old"],
        "variants": [
            {
                "id": 1,
                "sku": f"{sku_prefix}-small",
                "cost": 700,
                "price": 1200,
                "is_enabled": True,
                "is_default": True,
                "is_available": True,
            },
            {
                "id": 3,
                "sku": f"{sku_prefix}-large",
                "cost": 750,
                "price": 1300,
                "is_enabled": False,
                "is_default": False,
                "is_available": True,
            },
        ],
        "external": {
            "id": "etsy-listing" if published else None,
            "handle": "https://etsy.example/listing" if published else None,
            "shipping_template_id": "shipping-template",
        },
        "safety_information": {"age_group": "adult"},
        "sales_channel_properties": ["etsy"],
        "is_printify_express_enabled": True,
        "is_economy_shipping_enabled": False,
        "free_personalization_enabled": False,
        "print_areas": [
            {
                "variant_ids": [1, 3],
                "placeholders": [
                    {
                        "position": "front",
                        "images": [
                            {"id": "old-upload", "x": 0.5, "y": 0.4, "scale": 0.6, "angle": 0}
                        ],
                    },
                    {"position": "back", "images": []},
                ],
            }
        ],
        "images": [_mockup(10, default=True), _mockup(20)],
    }


def _native_copy() -> tuple[dict, dict]:
    template = _product("template", published=True)
    draft = _product("draft", sku_prefix="clone")
    return template, draft


def test_assert_native_copy_accepts_fixture_like_native_duplicate():
    template, draft = _native_copy()

    assert_native_copy(template, draft)


def test_assert_native_copy_accepts_unlinked_copy_without_optional_safety_information():
    template, draft = _native_copy()
    draft.pop("external")
    draft.pop("safety_information")

    assert_native_copy(template, draft)


@pytest.mark.parametrize(
    ("mutate", "message"),
    [
        (lambda draft: draft.update({"external": {"id": "published", "handle": None, "shipping_template_id": "shipping-template"}}), "external"),
        (lambda draft: draft["variants"][1].update({"price": 1400}), "variants"),
        (lambda draft: draft["variants"][0].update({"sku": "source-small"}), "sku"),
        (lambda draft: draft["variants"][0].update({"is_available": False}), "unavailable"),
    ],
)
def test_assert_native_copy_rejects_unsafe_clone_changes(mutate, message: str):
    template, draft = _native_copy()
    mutate(draft)

    with pytest.raises(DraftError, match=message):
        assert_native_copy(template, draft)


def test_assert_native_copy_rejects_published_template_target():
    template, draft = _native_copy()
    template["external"] = {"id": None, "handle": None, "shipping_template_id": "shipping-template"}
    draft["external"] = {"id": "published", "handle": "https://etsy.example/listing", "shipping_template_id": "shipping-template"}

    with pytest.raises(DraftError, match="external"):
        assert_native_copy(template, draft)


def test_assert_native_copy_rejects_duplicate_enabled_clone_skus():
    template, draft = _native_copy()
    template["variants"][1]["is_enabled"] = True
    draft["variants"][1]["is_enabled"] = True
    draft["variants"][1]["sku"] = draft["variants"][0]["sku"]

    with pytest.raises(DraftError, match="unique"):
        assert_native_copy(template, draft)


@pytest.mark.parametrize(
    ("mutate", "raises"),
    [
        (lambda product: product["images"].pop(), False),
        (lambda product: product["images"].reverse(), False),
        (lambda product: product["images"][0].update({"is_default": False}), True),
    ],
)
def test_mockup_signature_detects_lost_reordered_or_default_changed_mockups(mutate, raises: bool):
    product = _product("draft")
    original = mockup_signature(product)
    mutate(product)

    if raises:
        with pytest.raises(DraftError, match="default"):
            mockup_signature(product)
    else:
        assert mockup_signature(product) != original


def test_mockup_signature_fails_closed_when_mockup_metadata_is_missing():
    product = _product("draft")
    product["images"][0].pop("mockup_id")

    with pytest.raises(DraftError, match="metadata"):
        mockup_signature(product)


def test_mockup_signature_rejects_a_missing_camera_label_without_a_type_error():
    product = _product("draft")
    product["images"][0]["src"] = product["images"][0]["src"].split("?")[0]

    with pytest.raises(DraftError, match="camera_label"):
        mockup_signature(product)


def test_make_print_areas_contains_a_non_two_to_three_image_and_omits_empty_locations():
    draft = _product("draft")
    upload = {"id": "new-upload", "width": 3000, "height": 1000, "mime_type": "image/png"}

    areas = make_print_areas(draft, upload, width=3000, height=1000)

    assert areas == [
        {
            "variant_ids": [1, 3],
            "placeholders": [
                {
                    "position": "front",
                    "images": [
                        {
                            "id": "new-upload",
                            "x": 0.5,
                            "y": pytest.approx(0.05 + (8 / 3) * 300 / (2 * 4919)),
                            "scale": pytest.approx(8 * 300 / 3951),
                            "angle": 0,
                        }
                    ],
                }
            ],
        }
    ]


def test_make_print_areas_rejects_upload_dimensions_that_do_not_match_input():
    draft = _product("draft")
    upload = {"id": "new-upload", "width": 3000, "height": 1000, "mime_type": "image/png"}

    with pytest.raises(DraftError, match="dimensions"):
        make_print_areas(draft, upload, width=3000, height=1001)


def test_make_print_areas_rejects_existing_non_front_artwork():
    draft = _product("draft")
    draft["print_areas"][0]["placeholders"][1]["images"] = [{"id": "back-art"}]
    upload = {"id": "new-upload", "width": 3000, "height": 1000, "mime_type": "image/png"}

    with pytest.raises(DraftError, match="front"):
        make_print_areas(draft, upload, width=3000, height=1000)


def test_verify_update_accepts_artwork_and_copy_update_and_ignores_transient_image_id():
    before = _product("draft")
    after = deepcopy(before)
    payload = {
        "title": "New title",
        "description": "New description",
        "tags": ["new", "shirt"],
        "print_areas": make_print_areas(
            before,
            {"id": "new-upload", "width": 2000, "height": 3000, "mime_type": "image/png"},
            width=2000,
            height=3000,
        ),
    }
    after.update({key: value for key, value in payload.items()})
    after["print_areas"][0]["placeholders"][0]["images"][0]["imageId"] = "read-only"
    after["images"][0]["src"] = after["images"][0]["src"].replace("old-title", "new-title")

    verify_update(before, after, payload)


def test_verify_update_rejects_changed_mockup_selection_or_order():
    before = _product("draft")
    after = deepcopy(before)
    payload = {"title": "Old title", "description": "Old description", "tags": ["old"], "print_areas": before["print_areas"]}
    after["images"][1]["is_selected_for_publishing"] = False

    with pytest.raises(DraftError, match="mockup"):
        verify_update(before, after, payload)


def test_verify_update_rejects_provider_change_when_optional_fields_are_absent():
    before = _product("draft")
    before.pop("external")
    before.pop("safety_information")
    after = deepcopy(before)
    after["print_provider_id"] = 100
    payload = {
        "title": "Old title",
        "description": "Old description",
        "tags": ["old"],
        "print_areas": before["print_areas"],
    }

    with pytest.raises(DraftError, match="print_provider_id"):
        verify_update(before, after, payload)


def test_verify_update_rejects_changed_exposed_shipping_template():
    before = _product("draft")
    after = deepcopy(before)
    after["external"]["shipping_template_id"] = "different-template"
    payload = {
        "title": "Old title",
        "description": "Old description",
        "tags": ["old"],
        "print_areas": before["print_areas"],
    }

    with pytest.raises(DraftError, match="shipping_template_id"):
        verify_update(before, after, payload)
