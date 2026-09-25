"""Conservative trust and disclosure checks for Etsy listing records."""

from __future__ import annotations

from typing import Mapping


_CHECKS = {
    "production_partner": "production_partner_disclosed",
    "ai_disclosure": "ai_disclosure_complete",
    "shipping_origin": "shipping_origin_verified",
    "processing_policy": "processing_policy_complete",
    "returns_policy": "returns_policy_complete",
    "size_information": "size_information_complete",
}


def _identifier(value: object) -> str | None:
    if value is None:
        return None
    candidate = str(value).strip()
    return candidate or None


def derive_live_etsy_trust(
    listing: Mapping[str, object],
    *,
    shipping_profiles: list[Mapping[str, object]],
    production_partners: list[Mapping[str, object]],
) -> dict[str, bool | None]:
    """Derive fail-closed trust fields from a sanitized Etsy snapshot.

    This verifies only facts present in the live snapshot. It does not infer a
    relationship by title and it does not substitute historical Printify data.
    """

    partner_ids = listing.get("production_partner_ids")
    listed_partner_ids = (
        {
            identifier
            for value in partner_ids
            if (identifier := _identifier(value)) is not None
        }
        if isinstance(partner_ids, list)
        else None
    )
    partners_by_id = {
        identifier: partner
        for partner in production_partners
        if (identifier := _identifier(partner.get("production_partner_id"))) is not None
    }
    if listed_partner_ids is None:
        partner_disclosed: bool | None = None
    elif not listed_partner_ids:
        partner_disclosed = False
    else:
        partner_statuses: list[bool | None] = []
        for partner_id in listed_partner_ids:
            partner = partners_by_id.get(partner_id)
            if partner is None:
                partner_statuses.append(False)
            elif "is_active" not in partner or "is_deleted" not in partner:
                partner_statuses.append(None)
            else:
                partner_statuses.append(
                    partner.get("is_active") is True and partner.get("is_deleted") is False
                )
        partner_disclosed = (
            False
            if False in partner_statuses
            else None
            if None in partner_statuses
            else True
        )

    shipping_profile_id = _identifier(listing.get("shipping_profile_id"))
    profile = next(
        (
            candidate
            for candidate in shipping_profiles
            if _identifier(candidate.get("shipping_profile_id")) == shipping_profile_id
        ),
        None,
    )
    processing_min = profile.get("processing_min") if profile else None
    processing_max = profile.get("processing_max") if profile else None
    if profile is None or "processing_min" not in profile or "processing_max" not in profile:
        processing_complete: bool | None = None
    else:
        processing_complete = (
            isinstance(processing_min, int)
            and not isinstance(processing_min, bool)
            and isinstance(processing_max, int)
            and not isinstance(processing_max, bool)
            and 0 <= processing_min <= processing_max
        )
    shipping_origin = _identifier(profile.get("origin_country_iso")) if profile else None

    description = listing.get("description")
    copy = description.casefold() if isinstance(description, str) else ""
    ai_disclosed = any(
        phrase in copy
        for phrase in (
            "ai-assisted",
            "ai assisted",
            "ai image-generation",
            "artificial intelligence",
        )
    )
    sizing_copy = "fit and sizing" in copy or "size chart" in copy
    inventory = listing.get("inventory")
    has_size_property = False
    if isinstance(inventory, list):
        for product in inventory:
            if not isinstance(product, Mapping):
                continue
            properties = product.get("property_values")
            if not isinstance(properties, list):
                continue
            if any(
                isinstance(prop, Mapping)
                and (
                    str(prop.get("property_name", "")).casefold() == "size"
                    or prop.get("property_id") == 100
                    or str(prop.get("property_name", "")).casefold()
                    == "clothing sizes"
                    or prop.get("property_id") == 513
                )
                for prop in properties
            ):
                has_size_property = True
                break

    return {
        "production_partner_disclosed": partner_disclosed,
        "ai_disclosure_complete": ai_disclosed,
        "shipping_origin_verified": shipping_origin is not None,
        "processing_policy_complete": processing_complete,
        "returns_policy_complete": _identifier(listing.get("return_policy_id")) is not None,
        "size_information_complete": sizing_copy and has_size_property,
    }


def audit_listing_trust(record: Mapping[str, object]) -> dict[str, object]:
    etsy = record.get("etsy")
    fields = etsy if isinstance(etsy, Mapping) else {}
    checks: dict[str, str] = {}
    for label, source_field in _CHECKS.items():
        value = fields.get(source_field)
        if value is True:
            checks[label] = "pass"
        elif value is False:
            checks[label] = "fail"
        else:
            checks[label] = "unknown"
    if "fail" in checks.values():
        overall = "fail"
    elif "unknown" in checks.values():
        overall = "blocked_unknown"
    else:
        overall = "pass"
    return {
        "key": record.get("key"),
        "overall": overall,
        "checks": checks,
        "next_action": (
            "review_failed_trust_fields"
            if overall == "fail"
            else "obtain_live_etsy_listing_evidence"
            if overall == "blocked_unknown"
            else "none"
        ),
    }
