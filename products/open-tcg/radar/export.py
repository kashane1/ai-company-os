"""Read-only, versioned export of radar observations."""

from __future__ import annotations

import base64
import datetime as dt
import hashlib
import json
import math
import sqlite3
from pathlib import Path
from urllib.parse import quote

SCHEMA_VERSION = 1
DEFAULT_LIMIT = 100
MAX_LIMIT = 500
MAX_TEXT_LENGTH = 10_000
_OBSERVATION_COLUMNS = frozenset(
    {
        "id",
        "source_id",
        "external_id",
        "author",
        "text",
        "signal",
        "retailer",
        "product_text",
        "price",
        "url",
        "source_time",
        "received_at",
    }
)


# Optional store-offer context (store monitoring P6), null for other sources.
PRICE_CLASSES = frozenset({"below_msrp", "at_msrp", "near_msrp", "market", "marked_up", "no_msrp"})
STORE_TRUST_LEVELS = frozenset({"unvetted", "checked", "purchased_ok", "avoid"})
MSRP_BASES = frozenset(
    {"official_listing", "big_box_first_party", "distributor_or_press", "form_default", "per_pack_estimate"}
)
_OFFER_FIELDS = ("msrp_cents", "msrp_basis", "price_class", "store_trust", "catalog_product_id")


class ExportError(ValueError):
    """The requested source database or export parameters are invalid."""


def _parse_time(value: object, field: str) -> str:
    if not isinstance(value, str):
        raise ExportError(f"{field} must be an ISO-8601 timestamp")
    try:
        parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ExportError(f"{field} must be an ISO-8601 timestamp") from exc
    if parsed.tzinfo is None:
        raise ExportError(f"{field} must include a UTC offset")
    return parsed.astimezone(dt.timezone.utc).isoformat()


def _validate_text(value: object, field: str, *, nullable: bool = True) -> str | None:
    if value is None and nullable:
        return None
    if not isinstance(value, str):
        raise ExportError(f"{field} must be text")
    if len(value) > MAX_TEXT_LENGTH:
        raise ExportError(f"{field} is too long")
    return "".join(
        " " if ord(character) < 32 or ord(character) == 127 else character for character in value
    )


def _encode_cursor(received_at: str, observation_id: int) -> str:
    payload = json.dumps([received_at, observation_id], separators=(",", ":")).encode()
    return base64.urlsafe_b64encode(payload).decode().rstrip("=")


def _decode_cursor(cursor: str | None) -> tuple[str, int] | None:
    if cursor is None:
        return None
    if not isinstance(cursor, str) or not cursor:
        raise ExportError("cursor is invalid")
    try:
        payload = base64.urlsafe_b64decode(cursor + "=" * (-len(cursor) % 4))
        received_at, observation_id = json.loads(payload)
    except (UnicodeDecodeError, ValueError, json.JSONDecodeError) as exc:
        raise ExportError("cursor is invalid") from exc
    _parse_time(received_at, "cursor received_at")
    if (
        isinstance(observation_id, bool)
        or not isinstance(observation_id, int)
        or observation_id < 1
    ):
        raise ExportError("cursor is invalid")
    return received_at, observation_id


def _connect_read_only(path: str | Path) -> sqlite3.Connection:
    database = Path(path)
    if not database.is_file():
        raise ExportError(f"source database does not exist: {database}")
    uri = f"file:{quote(str(database.resolve()))}?mode=ro"
    try:
        connection = sqlite3.connect(uri, uri=True)
    except sqlite3.Error as exc:
        raise ExportError(f"cannot open source database read-only: {exc}") from exc
    connection.row_factory = sqlite3.Row
    return connection


def _validate_schema(connection: sqlite3.Connection) -> None:
    try:
        rows = connection.execute("PRAGMA table_info(observations)").fetchall()
    except sqlite3.Error as exc:
        raise ExportError("unsupported source database schema") from exc
    columns = {row[1] for row in rows}
    missing = _OBSERVATION_COLUMNS.difference(columns)
    if missing:
        raise ExportError(
            f"unsupported source database schema; missing {', '.join(sorted(missing))}"
        )


def _origin_key(source_id: str, external_id: str) -> str:
    return hashlib.sha256(json.dumps([source_id, external_id]).encode("utf-8")).hexdigest()


def _optional_int(value: object, field: str, *, minimum: int) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise ExportError(f"{field} must be an integer of at least {minimum} or null")
    return value


def _optional_enum(value: object, field: str, allowed: frozenset[str]) -> str | None:
    if value is None:
        return None
    if value not in allowed:
        raise ExportError(f"{field} is not a known value")
    return value


def _offer_fields(row: sqlite3.Row) -> dict[str, object]:
    keys = row.keys()
    values = {field: row[field] if field in keys else None for field in _OFFER_FIELDS}
    return {
        "msrp_cents": _optional_int(values["msrp_cents"], "msrp_cents", minimum=0),
        "msrp_basis": _optional_enum(values["msrp_basis"], "msrp_basis", MSRP_BASES),
        "price_class": _optional_enum(values["price_class"], "price_class", PRICE_CLASSES),
        "store_trust": _optional_enum(values["store_trust"], "store_trust", STORE_TRUST_LEVELS),
        "catalog_product_id": _optional_int(values["catalog_product_id"], "catalog_product_id", minimum=1),
    }


def _record(row: sqlite3.Row) -> dict[str, object]:
    source_id = _validate_text(row["source_id"], "source_id", nullable=False)
    external_id = _validate_text(row["external_id"], "external_id", nullable=False)
    assert source_id is not None and external_id is not None
    received_at = _parse_time(row["received_at"], "received_at")
    observed_at = (
        _parse_time(row["source_time"], "source_time") if row["source_time"] is not None else None
    )
    price = row["price"]
    if price is not None:
        if (
            isinstance(price, bool)
            or not isinstance(price, (int, float))
            or not math.isfinite(price)
        ):
            raise ExportError("price must be a finite number or null")
        price = float(price)
    observation_id = row["id"]
    if (
        isinstance(observation_id, bool)
        or not isinstance(observation_id, int)
        or observation_id < 1
    ):
        raise ExportError("observation id is invalid")
    return {
        "schema_version": SCHEMA_VERSION,
        "origin": "open_tcg",
        "origin_key": _origin_key(row["source_id"], row["external_id"]),
        "source": source_id,
        "source_author": _validate_text(row["author"], "author"),
        "observed_at": observed_at,
        "received_at": received_at,
        "signal": _validate_text(row["signal"], "signal", nullable=False),
        "retailer_hint": _validate_text(row["retailer"], "retailer"),
        "item_hint": _validate_text(row["product_text"], "product_text"),
        "price_hint": price,
        "url": _validate_text(row["url"], "url"),
        "raw_text": _validate_text(row["text"], "text", nullable=False),
        "cursor": _encode_cursor(row["received_at"], observation_id),
        **_offer_fields(row),
    }


def export_observations(
    path: str | Path, *, after: str | None = None, limit: int = DEFAULT_LIMIT
) -> list[dict[str, object]]:
    """Export bounded observations without initializing or writing the radar DB."""
    if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= MAX_LIMIT:
        raise ExportError(f"limit must be an integer from 1 to {MAX_LIMIT}")
    cursor = _decode_cursor(after)
    connection = _connect_read_only(path)
    try:
        _validate_schema(connection)
        has_offers = connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'store_offer_details'"
        ).fetchone()
        offer_columns = (
            ", d.msrp_cents, d.msrp_basis, d.price_class, d.store_trust, d.catalog_product_id" if has_offers else ""
        )
        offer_join = " LEFT JOIN store_offer_details d ON d.observation_id = observations.id" if has_offers else ""
        query = f"""
            SELECT observations.id AS id, source_id, external_id, author, text, signal, retailer,
                   product_text, price, url, source_time, received_at{offer_columns}
            FROM observations{offer_join}
        """
        values: tuple[object, ...] = ()
        if cursor is not None:
            query += " WHERE (received_at > ?) OR (received_at = ? AND observations.id > ?)"
            values = (cursor[0], cursor[0], cursor[1])
        query += " ORDER BY received_at ASC, observations.id ASC LIMIT ?"
        rows = connection.execute(query, (*values, limit)).fetchall()
        return [_record(row) for row in rows]
    except sqlite3.Error as exc:
        raise ExportError(f"unsupported source database schema: {exc}") from exc
    finally:
        connection.close()
