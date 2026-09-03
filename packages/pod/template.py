"""Validate safe Printify native-copy and artwork-update requests without network access."""

from __future__ import annotations

from collections.abc import Mapping
from math import isfinite
from typing import Any
from urllib.parse import parse_qs, urlparse


class DraftError(ValueError):
    """A product draft does not preserve the required Printify invariants."""


_MISSING = object()


def _mapping(value: object, name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise DraftError(f"{name} is missing or invalid")
    return value


def _list(value: object, name: str) -> list[Any]:
    if not isinstance(value, list):
        raise DraftError(f"{name} is missing or invalid")
    return value


def _required(product: Mapping[str, Any], key: str) -> Any:
    if key not in product:
        raise DraftError(f"{key} is missing")
    return product[key]


def _blank(value: object) -> bool:
    return value is None or (isinstance(value, str) and not value.strip())


def _external(product: Mapping[str, Any]) -> Mapping[str, Any]:
    external = product.get("external", _MISSING)
    if external is _MISSING or external is None:
        return {}
    return _mapping(external, "external")


def _external_shipping_template_id(product: Mapping[str, Any]) -> Any:
    return _external(product).get("shipping_template_id", _MISSING)


def _camera_key(image: Mapping[str, Any]) -> str:
    src = image.get("src")
    if not isinstance(src, str):
        raise DraftError("mockup src is missing")
    parsed = urlparse(src)
    if parsed.scheme != "https" or parsed.netloc != "images.printify.com":
        raise DraftError("mockup src is not a Printify mockup")
    parts = parsed.path.strip("/").split("/")
    if len(parts) != 5 or parts[0] != "mockup" or not all(parts[1:4]) or not parts[4].endswith(".jpg"):
        raise DraftError("mockup src has an unparseable camera path")
    labels = parse_qs(parsed.query).get("camera_label")
    if not isinstance(labels, list) or len(labels) != 1 or not labels[0]:
        raise DraftError("mockup src is missing camera_label")
    # Product ID and generated title belong to the copy and are deliberately excluded.
    return f"{parts[2]}/{parts[3]}?camera_label={labels[0]}"


def mockup_signature(product: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Return a stable, order-sensitive signature of selected Printify mockups."""
    product = _mapping(product, "product")
    images = _list(product.get("images"), "images")
    selected: list[dict[str, Any]] = []
    for index, raw_image in enumerate(images):
        image = _mapping(raw_image, f"images[{index}]")
        required = (
            "mockup_id",
            "variant_ids",
            "position",
            "is_default",
            "is_selected_for_publishing",
            "order",
        )
        if any(key not in image for key in required):
            raise DraftError("mockup metadata is incomplete")
        variant_ids = _list(image["variant_ids"], "mockup variant_ids")
        if (
            not isinstance(image["mockup_id"], str)
            or not image["mockup_id"]
            or not variant_ids
            or not all(isinstance(variant_id, int) for variant_id in variant_ids)
            or not isinstance(image["position"], str)
            or not isinstance(image["is_default"], bool)
            or (image["order"] is not None and not isinstance(image["order"], int))
        ):
            raise DraftError("mockup metadata is invalid")
        camera = _camera_key(image)
        if image["is_selected_for_publishing"] is True:
            try:
                sorted_ids = sorted(variant_ids)
            except TypeError as exc:
                raise DraftError("mockup variant_ids are invalid") from exc
            selected.append(
                {
                    "camera": camera,
                    "variant_ids": sorted_ids,
                    "position": image["position"],
                    "is_default": image["is_default"],
                    "order": image["order"],
                }
            )
        elif image["is_selected_for_publishing"] is not False:
            raise DraftError("mockup selection metadata is invalid")
    if not selected:
        raise DraftError("at least one mockup must be selected")
    if sum(item["is_default"] for item in selected) != 1:
        raise DraftError("selected mockups must have exactly one default")
    return selected


def _native_variant_signature(product: Mapping[str, Any]) -> dict[Any, tuple[Any, Any, Any]]:
    signatures: dict[Any, tuple[Any, Any, Any]] = {}
    for raw_variant in _list(product.get("variants"), "variants"):
        variant = _mapping(raw_variant, "variant")
        variant_id = _required(variant, "id")
        if variant_id in signatures:
            raise DraftError("variant IDs must be unique")
        signatures[variant_id] = (
            _required(variant, "price"),
            _required(variant, "is_enabled"),
            _required(variant, "is_default"),
        )
    return signatures


def _enabled_skus(product: Mapping[str, Any]) -> set[str]:
    skus: set[str] = set()
    for raw_variant in _list(product.get("variants"), "variants"):
        variant = _mapping(raw_variant, "variant")
        if _required(variant, "is_enabled"):
            sku = variant.get("sku")
            if not isinstance(sku, str) or not sku.strip():
                raise DraftError("enabled variant SKU must be nonempty")
            if sku in skus:
                raise DraftError("enabled variant SKUs must be unique")
            if variant.get("is_available") is not True:
                raise DraftError("enabled variant is unavailable")
            skus.add(sku)
    return skus


def _setting_fields(product: Mapping[str, Any]) -> dict[str, Any]:
    fields = {
        "safety_information": product.get("safety_information", _MISSING),
        "sales_channel_properties": _required(product, "sales_channel_properties"),
    }
    for key, value in product.items():
        if key.startswith("is_printify_express_") or key.startswith("is_economy_shipping_"):
            fields[key] = value
    if not any(key.startswith("is_printify_express_") for key in fields):
        raise DraftError("Printify Express settings are missing")
    if not any(key.startswith("is_economy_shipping_") for key in fields):
        raise DraftError("economy shipping settings are missing")
    return fields


def _native_settings_match(template: Mapping[str, Any], draft: Mapping[str, Any]) -> bool:
    template_settings = _setting_fields(template)
    draft_settings = _setting_fields(draft)
    for key, value in template_settings.items():
        if key == "safety_information" and (
            value is _MISSING or draft_settings[key] is _MISSING
        ):
            continue
        if value != draft_settings[key]:
            return False
    return True


def _assert_unpublished_draft(product: Mapping[str, Any]) -> None:
    _assert_unlocked_not_deleted(product)
    external = _external(product)
    if not _blank(external.get("id")) or not _blank(external.get("handle")):
        raise DraftError("draft external id and handle must be blank")


def _assert_unlocked_not_deleted(product: Mapping[str, Any]) -> None:
    if product.get("is_locked") is not False:
        raise DraftError("product must be unlocked")
    if product.get("is_deleted") is not False:
        raise DraftError("product must not be deleted")


def assert_native_copy(template: Mapping[str, Any], draft: Mapping[str, Any], shop_id: int = 28779955) -> None:
    """Raise unless ``draft`` is an unpublished native duplicate of ``template``."""
    template = _mapping(template, "template")
    draft = _mapping(draft, "draft")
    if _required(template, "id") == _required(draft, "id"):
        raise DraftError("template and draft IDs must differ")
    for product, label in ((template, "template"), (draft, "draft")):
        if product.get("shop_id") != shop_id:
            raise DraftError(f"{label} shop_id must be {shop_id}")
        if product.get("blueprint_id") != 6 or product.get("print_provider_id") != 99:
            raise DraftError(f"{label} must use blueprint 6 and provider 99")
        _assert_unlocked_not_deleted(product)
    _assert_unpublished_draft(draft)
    if draft.get("visible") is not True:
        raise DraftError("draft must remain visible")
    if _native_variant_signature(template) != _native_variant_signature(draft):
        raise DraftError("variants changed from the native copy")
    source_skus = {
        variant.get("sku")
        for raw_variant in _list(template.get("variants"), "variants")
        for variant in [_mapping(raw_variant, "variant")]
        if isinstance(variant.get("sku"), str) and variant["sku"].strip()
    }
    if _enabled_skus(draft) & source_skus:
        raise DraftError("enabled clone skus must be disjoint from source skus")
    if not _native_settings_match(template, draft):
        raise DraftError("shipping or safety settings changed from the template")
    if mockup_signature(template) != mockup_signature(draft):
        raise DraftError("selected mockups changed from the template")


def artwork_placement(width: int, height: int, scale_percent: float | None = None) -> dict[str, Any]:
    """Size original pixels on the tested 3951 × 4919, 300-DPI front area."""
    if not isinstance(width, int) or not isinstance(height, int) or width <= 0 or height <= 0:
        raise DraftError("image dimensions must be positive integers")
    if scale_percent is None:
        image_ratio = width / height
        print_width = min(8.0, 12.0 * image_ratio)
        print_height = print_width / image_ratio
        y = 0.05 + print_height * 300 / (2 * 4919)
    else:
        if (isinstance(scale_percent, bool) or not isinstance(scale_percent, (int, float))
                or not isfinite(scale_percent) or scale_percent <= 0):
            raise DraftError("scale percent must be a finite positive number")
        # UI percent is relative to the original pixels at 300 DPI. Cap at the
        # print area's edges rather than clipping a wide or tall design.
        multiplier = min(scale_percent / 100, 3951 / width, 4919 / height)
        print_width = width * multiplier / 300
        print_height = height * multiplier / 300
        y = 0.5
    return {
        "requested_scale_percent": scale_percent,
        "applied_scale_percent": print_width * 300 / width * 100,
        "width_inches": print_width,
        "height_inches": print_height,
        "dpi": round(width / print_width, 1),
        "x": 0.5,
        "y": y,
        "scale": print_width * 300 / 3951,
        "angle": 0,
    }


def make_print_areas(
    draft: Mapping[str, Any], upload: Mapping[str, Any], width: int, height: int,
    *, scale_percent: float | None = None,
) -> list[dict[str, Any]]:
    """Build a front-only Printify artwork payload without altering the source image."""
    draft = _mapping(draft, "draft")
    upload = _mapping(upload, "upload")
    placement = artwork_placement(width, height, scale_percent)
    if not isinstance(upload.get("id"), str) or not upload["id"].strip():
        raise DraftError("upload id is missing")
    if upload.get("mime_type") != "image/png":
        raise DraftError("upload must be a PNG")
    if upload.get("width") != width or upload.get("height") != height:
        raise DraftError("upload dimensions do not match the image")

    image = {"id": upload["id"], **{key: placement[key] for key in ("x", "y", "scale", "angle")}}
    areas: list[dict[str, Any]] = []
    for raw_area in _list(draft.get("print_areas"), "print_areas"):
        area = _mapping(raw_area, "print area")
        variant_ids = _list(area.get("variant_ids"), "print area variant_ids")
        placeholders = _list(area.get("placeholders"), "print area placeholders")
        front: list[Mapping[str, Any]] = []
        for raw_placeholder in placeholders:
            placeholder = _mapping(raw_placeholder, "print area placeholder")
            images = _list(placeholder.get("images"), "placeholder images")
            if placeholder.get("position") == "front":
                front.append(placeholder)
            elif images:
                raise DraftError("only front artwork may be printed")
        if len(front) != 1 or len(_list(front[0].get("images"), "front images")) != 1:
            raise DraftError("each print area must have exactly one front image")
        areas.append(
            {
                "variant_ids": list(variant_ids),
                "placeholders": [{"position": "front", "images": [image.copy()]}],
            }
        )
    if not areas:
        raise DraftError("at least one print area is required")
    return areas


def _update_variant_signature(product: Mapping[str, Any]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for raw_variant in _list(product.get("variants"), "variants"):
        variant = _mapping(raw_variant, "variant")
        result.append(
            {
                key: value
                for key, value in variant.items()
                if key in {"id", "sku", "cost", "price"} or key.startswith("is_")
            }
        )
    return result


def _normalized_print_areas(product_or_areas: Mapping[str, Any] | list[Any]) -> list[dict[str, Any]]:
    raw_areas = (
        _list(product_or_areas.get("print_areas"), "print_areas")
        if isinstance(product_or_areas, Mapping)
        else _list(product_or_areas, "print_areas")
    )
    areas: list[dict[str, Any]] = []
    for raw_area in raw_areas:
        area = _mapping(raw_area, "print area")
        placeholders: list[dict[str, Any]] = []
        for raw_placeholder in _list(area.get("placeholders"), "print area placeholders"):
            placeholder = _mapping(raw_placeholder, "print area placeholder")
            images = _list(placeholder.get("images"), "placeholder images")
            if images:
                normalized_images = []
                for raw_image in images:
                    image = _mapping(raw_image, "print image")
                    normalized_images.append(
                        {key: _required(image, key) for key in ("id", "x", "y", "scale", "angle")}
                    )
                placeholders.append(
                    {"position": _required(placeholder, "position"), "images": normalized_images}
                )
        areas.append({"variant_ids": list(_list(area.get("variant_ids"), "print area variant_ids")), "placeholders": placeholders})
    return areas


def verify_update(
    before: Mapping[str, Any], after: Mapping[str, Any], payload: Mapping[str, Any]
) -> None:
    """Raise unless an artwork/copy update changed only the requested mutable fields."""
    before = _mapping(before, "before")
    after = _mapping(after, "after")
    payload = _mapping(payload, "payload")
    for key in ("id", "shop_id", "blueprint_id", "print_provider_id", "visible"):
        if _required(before, key) != _required(after, key):
            raise DraftError(f"{key} changed during update")
    _assert_unpublished_draft(after)
    if after.get("is_locked") is not False:
        raise DraftError("updated draft must be unlocked")
    for key in ("title", "description", "tags"):
        if _required(after, key) != _required(payload, key):
            raise DraftError(f"updated {key} does not match payload")
    if _normalized_print_areas(after) != _normalized_print_areas(_required(payload, "print_areas")):
        raise DraftError("updated print_areas do not match payload")
    if _update_variant_signature(before) != _update_variant_signature(after):
        raise DraftError("variants changed during update")
    before_settings = _setting_fields(before)
    after_settings = _setting_fields(after)
    for key in ("safety_information", "sales_channel_properties"):
        if before_settings[key] != after_settings[key]:
            raise DraftError(f"{key} changed during update")
    if _external_shipping_template_id(before) != _external_shipping_template_id(after):
        raise DraftError("shipping_template_id changed during update")
    if {
        key: value for key, value in before_settings.items() if key.startswith(("is_printify_express_", "is_economy_shipping_"))
    } != {
        key: value for key, value in after_settings.items() if key.startswith(("is_printify_express_", "is_economy_shipping_"))
    }:
        raise DraftError("express or economy settings changed during update")
    for key in ("free_personalization_enabled", "is_free_personalization_enabled"):
        if before.get(key) != after.get(key):
            raise DraftError("free personalization setting changed during update")
    if mockup_signature(before) != mockup_signature(after):
        raise DraftError("selected mockups changed during update")
