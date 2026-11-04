"""TCGplayer Seller Portal CSV: the only sanctioned write path.

TCGplayer has not issued new API keys in years, so prices and quantities reach
the marketplace one way — export a CSV from the Pricing tab, edit it, upload it
back. That capability is reported to be gated to Level 4 sellers, so this is
machinery for later; at Level 1 the Seller Portal is manual.

## Why this edits their file instead of writing one

TCGplayer's exact column set could not be verified while building this: their
help pages refuse automated fetches, and every secondhand description of the
format disagrees on details. Generating a header from guesswork would produce
a file that fails validation on upload, or worse, one that passes and sets the
wrong field.

So the supported path is round-tripping: export the CSV from your Seller
Portal, let this rewrite only the cells it understands, and upload the result.
The header, the column order and every untouched value come back exactly as
TCGplayer produced them, which makes the tool immune to a format change it
does not need to know about.

That also solves an identity problem. TCGplayer sells at SKU granularity —
product plus condition plus printing plus language — and the free TCGCSV feed
this project uses for prices explicitly publishes no SKU data. Your own export
is the only place those SKU rows exist.

`generate_blank` writes a best-effort header for inspection only. Do not upload
its output without checking it against a real export first.
"""

from __future__ import annotations

import csv
import sqlite3
from dataclasses import dataclass, field
from pathlib import Path

# Best-effort header, assembled from secondhand descriptions. UNVERIFIED.
BEST_EFFORT_COLUMNS = (
    "TCGplayer Id",
    "Product Line",
    "Set Name",
    "Product Name",
    "Title",
    "Number",
    "Rarity",
    "Condition",
    "TCG Market Price",
    "TCG Direct Low",
    "TCG Low Price With Shipping",
    "TCG Low Price",
    "Total Quantity",
    "Add to Quantity",
    "TCG Marketplace Price",
    "Photo URL",
)

# The one column TCGplayer requires: the price your listing becomes.
PRICE_COLUMN_CANDIDATES = ("TCG Marketplace Price", "Marketplace Price", "My Price")
ID_COLUMN_CANDIDATES = ("TCGplayer Id", "TCGplayer ID", "TCGPlayer Id", "Product Id")
CONDITION_COLUMN_CANDIDATES = ("Condition",)
QUANTITY_DELTA_CANDIDATES = ("Add to Quantity",)
QUANTITY_TOTAL_CANDIDATES = ("Total Quantity",)

MIN_PRICE_CENTS = 1


class ColumnNotFound(KeyError):
    """The export did not contain a column this tool needs."""


@dataclass
class RewriteReport:
    row_count: int = 0
    priced_count: int = 0
    quantity_changed_count: int = 0
    skipped: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def _resolve(fieldnames: list[str], candidates: tuple[str, ...]) -> str | None:
    lowered = {name.strip().casefold(): name for name in fieldnames}
    for candidate in candidates:
        found = lowered.get(candidate.casefold())
        if found:
            return found
    return None


def read_export(path: Path) -> tuple[list[dict[str, str]], list[str]]:
    """Read a Seller Portal export, preserving its header verbatim."""
    with open(path, newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise ColumnNotFound(f"{path} has no header row")
        return list(reader), list(reader.fieldnames)


def rewrite(
    rows: list[dict[str, str]],
    fieldnames: list[str],
    *,
    price_cents_by_key: dict[tuple[str, str], int] | None = None,
    quantity_delta_by_key: dict[tuple[str, str], int] | None = None,
) -> RewriteReport:
    """Update price and quantity cells in place, keyed on (id, condition).

    Only cells with a supplied value are touched. Everything else — including
    columns this tool has never heard of — is left exactly as exported.
    """
    report = RewriteReport(row_count=len(rows))

    id_column = _resolve(fieldnames, ID_COLUMN_CANDIDATES)
    if id_column is None:
        raise ColumnNotFound(
            f"No TCGplayer id column. Looked for {ID_COLUMN_CANDIDATES}, "
            f"found {fieldnames}"
        )
    condition_column = _resolve(fieldnames, CONDITION_COLUMN_CANDIDATES)
    price_column = _resolve(fieldnames, PRICE_COLUMN_CANDIDATES)
    delta_column = _resolve(fieldnames, QUANTITY_DELTA_CANDIDATES)

    if price_cents_by_key and price_column is None:
        raise ColumnNotFound(
            f"No marketplace price column. Looked for {PRICE_COLUMN_CANDIDATES}"
        )
    if quantity_delta_by_key and delta_column is None:
        report.warnings.append(
            "No 'Add to Quantity' column in this export — quantity changes were "
            "skipped. Verify how your export expresses quantity before relying "
            "on delisting through CSV."
        )

    seen_ids: set[str] = set()

    for row in rows:
        product_id = (row.get(id_column) or "").strip()
        condition = (row.get(condition_column) or "").strip() if condition_column else ""
        key = (product_id, condition)

        # TCGplayer rejects a file containing the same id twice.
        if product_id and product_id in seen_ids and not condition_column:
            report.skipped.append(f"duplicate id {product_id}")
            continue
        seen_ids.add(product_id)

        if price_cents_by_key and key in price_cents_by_key:
            cents = max(price_cents_by_key[key], MIN_PRICE_CENTS)
            row[price_column] = f"{cents / 100:.2f}"
            report.priced_count += 1

        if quantity_delta_by_key and delta_column and key in quantity_delta_by_key:
            row[delta_column] = str(quantity_delta_by_key[key])
            report.quantity_changed_count += 1

    return report


def write_import(path: Path, rows: list[dict[str, str]], fieldnames: list[str]) -> None:
    """Write the edited rows back in TCGplayer's own column order."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def generate_blank(path: Path, conn: sqlite3.Connection, copy_ids: list[int]) -> int:
    """Write a best-effort CSV for inspection. NOT verified for upload.

    Useful for seeing what the tool would send. The header below is assembled
    from secondhand descriptions of TCGplayer's format and has not been checked
    against a real export.
    """
    from . import catalog

    rows = []
    for copy_id in copy_ids:
        row = conn.execute(
            """
            SELECT c.copy_id, c.variant_id, c.condition_code,
                   s.product_id, s.card_name, s.card_number, s.rarity,
                   s.set_name, s.sub_type, s.current_price, s.image_url
              FROM copies c
              JOIN catalog.screener_rows s ON s.variant_id = c.variant_id
             WHERE c.copy_id = ?
            """,
            (copy_id,),
        ).fetchone()
        if row is None:
            continue

        price = catalog.market_price_cents(conn, row["variant_id"], row["condition_code"])
        label = {
            "NM": "Near Mint", "LP": "Lightly Played", "MP": "Moderately Played",
            "HP": "Heavily Played", "DMG": "Damaged",
        }.get(row["condition_code"], row["condition_code"])
        if "Holofoil" in (row["sub_type"] or ""):
            label = f"{label} Foil"

        rows.append({
            "TCGplayer Id": row["product_id"],
            "Product Line": "Pokemon",
            "Set Name": row["set_name"],
            "Product Name": row["card_name"],
            "Title": "",
            "Number": row["card_number"],
            "Rarity": row["rarity"],
            "Condition": label,
            "TCG Market Price": f"{row['current_price']:.2f}" if row["current_price"] else "",
            "TCG Direct Low": "",
            "TCG Low Price With Shipping": "",
            "TCG Low Price": "",
            "Total Quantity": "1",
            "Add to Quantity": "0",
            "TCG Marketplace Price": f"{(price or 1) / 100:.2f}",
            "Photo URL": row["image_url"] or "",
        })

    write_import(path, rows, list(BEST_EFFORT_COLUMNS))
    return len(rows)
