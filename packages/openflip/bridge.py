"""Validate OpenTCG observation exports without fetching their URLs."""

from __future__ import annotations

import base64
import datetime as dt
import json
import math

SCHEMA_VERSION = 1
MAX_TEXT_LENGTH = 10_000
MAX_RECORDS = 500
_REQUIRED_FIELDS = frozenset(
    {
        "schema_version",
        "origin",
        "origin_key",
        "source",
        "source_author",
        "observed_at",
        "received_at",
        "signal",
        "retailer_hint",
        "item_hint",
        "price_hint",
        "url",
        "raw_text",
        "cursor",
    }
)
_TEXT_FIELDS = frozenset(
    {
        "origin_key",
        "source",
        "source_author",
        "signal",
        "retailer_hint",
        "item_hint",
        "url",
        "raw_text",
        "cursor",
    }
)


# Optional store-offer context (OpenTCG store monitoring P6). Absent or null
# for non-store observations; v1 exports from before P6 omit them entirely.
_PRICE_CLASSES = frozenset({"below_msrp", "at_msrp", "near_msrp", "market", "marked_up", "no_msrp"})
_STORE_TRUST_LEVELS = frozenset({"unvetted", "checked", "purchased_ok", "avoid"})
_MSRP_BASES = frozenset(
    {"official_listing", "big_box_first_party", "distributor_or_press", "form_default", "per_pack_estimate"}
)


class OpenTcgBridgeError(ValueError):
    """The supplied export cannot safely be treated as OpenTCG evidence."""


def cursor_position(value: str) -> tuple[str, int]:
    try:
        decoded = json.loads(base64.urlsafe_b64decode(value + "=" * (-len(value) % 4)))
        if not isinstance(decoded, list) or len(decoded) != 2:
            raise ValueError("invalid cursor shape")
        received, identifier = decoded
        _validate_time(received, "cursor.received_at")
        if type(identifier) is not int or identifier < 1:
            raise ValueError("invalid cursor ID")
        return received, identifier
    except (ValueError, KeyError, TypeError) as error:
        raise OpenTcgBridgeError("invalid export cursor") from error


def _validate_time(value: object, field: str) -> str:
    if not isinstance(value, str):
        raise OpenTcgBridgeError(f"{field} must be an ISO-8601 timestamp")
    try:
        parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise OpenTcgBridgeError(f"{field} must be an ISO-8601 timestamp") from exc
    if parsed.tzinfo is None:
        raise OpenTcgBridgeError(f"{field} must include a UTC offset")
    return parsed.astimezone(dt.timezone.utc).isoformat()


def _validate_text(value: object, field: str, *, nullable: bool = True) -> str | None:
    if value is None and nullable:
        return None
    if not isinstance(value, str):
        raise OpenTcgBridgeError(f"{field} must be text")
    if len(value) > MAX_TEXT_LENGTH:
        raise OpenTcgBridgeError(f"{field} is too long")
    return "".join(
        " " if ord(character) < 32 or ord(character) == 127 else character for character in value
    )


def _parse_record(value: object) -> dict[str, object]:
    if not isinstance(value, dict):
        raise OpenTcgBridgeError("each NDJSON line must be a JSON object")
    missing = _REQUIRED_FIELDS.difference(value)
    if missing:
        raise OpenTcgBridgeError(f"missing required fields: {', '.join(sorted(missing))}")
    if type(value["schema_version"]) is not int or value["schema_version"] != SCHEMA_VERSION:
        raise OpenTcgBridgeError("unsupported schema_version")
    if value["origin"] != "open_tcg":
        raise OpenTcgBridgeError("origin must be open_tcg")

    parsed: dict[str, object] = {"schema_version": SCHEMA_VERSION, "origin": "open_tcg"}
    for field in _TEXT_FIELDS:
        parsed[field] = _validate_text(
            value[field],
            field,
            nullable=field not in {"origin_key", "source", "signal", "raw_text", "cursor"},
        )
    if (
        not parsed["origin_key"]
        or not parsed["source"]
        or not parsed["signal"]
        or not parsed["raw_text"]
        or not parsed["cursor"]
    ):
        raise OpenTcgBridgeError("required text fields must not be empty")
    parsed["observed_at"] = (
        _validate_time(value["observed_at"], "observed_at")
        if value["observed_at"] is not None
        else None
    )
    parsed["received_at"] = _validate_time(value["received_at"], "received_at")
    cursor_time, _ = cursor_position(parsed["cursor"])
    if _validate_time(cursor_time, "cursor.received_at") != parsed["received_at"]:
        raise OpenTcgBridgeError("cursor does not match received_at")

    # Optional fields are kept only when the export sent them.
    for field, minimum in (("msrp_cents", 0), ("catalog_product_id", 1)):
        if field not in value:
            continue
        number = value[field]
        if number is not None and (isinstance(number, bool) or not isinstance(number, int) or number < minimum):
            raise OpenTcgBridgeError(f"{field} must be an integer of at least {minimum} or null")
        parsed[field] = number
    for field, allowed in (
        ("msrp_basis", _MSRP_BASES), ("price_class", _PRICE_CLASSES), ("store_trust", _STORE_TRUST_LEVELS)
    ):
        if field not in value:
            continue
        label = value[field]
        if label is not None and label not in allowed:
            raise OpenTcgBridgeError(f"{field} is not a known value")
        parsed[field] = label

    price = value["price_hint"]
    if price is not None:
        if (
            isinstance(price, bool)
            or not isinstance(price, (int, float))
            or not math.isfinite(price)
            or price < 0
        ):
            raise OpenTcgBridgeError("price_hint must be a finite number or null")
        parsed["price_hint"] = float(price)
    else:
        parsed["price_hint"] = None
    return parsed


def parse_observations(text: str) -> list[dict]:
    """Parse bounded v1 NDJSON into normalized source-evidence records.

    This function deliberately treats URLs as inert strings. It opens neither URLs
    nor source databases and makes no network calls.
    """
    if not isinstance(text, str):
        raise OpenTcgBridgeError("NDJSON input must be text")
    if len(text.encode("utf-8")) > 8 * 1024 * 1024:
        raise OpenTcgBridgeError("NDJSON input exceeds 8 MiB")
    records: list[dict] = []
    for line_number, line in enumerate(text.splitlines(), start=1):
        if not line.strip():
            continue
        if len(records) >= MAX_RECORDS:
            raise OpenTcgBridgeError(f"too many records; maximum is {MAX_RECORDS}")
        try:
            raw = json.loads(line)
        except json.JSONDecodeError as exc:
            raise OpenTcgBridgeError(f"line {line_number} is not valid JSON") from exc
        records.append(_parse_record(raw))
    return records
