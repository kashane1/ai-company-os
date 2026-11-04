"""Storing card photos, and deriving the versions eBay wants.

Two files per shot, on purpose.

The original is kept forever at whatever resolution the phone produced. It is
the evidence in a not-as-described case: a 4,000px shot of clean edges at
intake is what actually answers a buyer who says the card arrived damaged.

The listing derivative is resized to eBay's recommended long edge and
converted to JPEG, because iPhones shoot HEIC by default and eBay will not
take it. Conversion prefers Pillow and falls back to `sips`, which ships with
macOS and reads HEIC natively — that avoids a pillow-heif dependency for the
one format that needs it.
"""

from __future__ import annotations

import shutil
import sqlite3
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from . import db

SHOTS = ("front", "back", "angled")

# eBay recommends at least this on the long edge; beyond it is wasted bytes.
LISTING_LONG_EDGE = 1600

PHOTO_ROOT = db.PROJECT_ROOT / "data" / "photos"


class UnreadableImage(RuntimeError):
    """The uploaded file could not be decoded by Pillow or sips."""


@dataclass(frozen=True)
class StoredPhoto:
    photo_id: int
    copy_id: int
    shot: str
    original_path: Path
    listing_path: Path | None


def _copy_dir(copy_id: int) -> Path:
    path = PHOTO_ROOT / f"copy-{copy_id:06d}"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _to_listing_jpeg(source: Path, destination: Path) -> bool:
    """Resize and convert to JPEG. Returns False if the image can't be read."""
    try:
        from PIL import Image

        with Image.open(source) as image:
            image = image.convert("RGB")
            image.thumbnail((LISTING_LONG_EDGE, LISTING_LONG_EDGE))
            image.save(destination, "JPEG", quality=88, optimize=True)
        return True
    except Exception:
        pass

    # HEIC, most likely. sips is part of macOS and reads it without extra deps.
    if shutil.which("sips") is None:
        return False
    result = subprocess.run(
        [
            "sips", "-s", "format", "jpeg",
            "-Z", str(LISTING_LONG_EDGE),
            str(source), "--out", str(destination),
        ],
        capture_output=True,
    )
    return result.returncode == 0 and destination.exists()


def store(
    conn: sqlite3.Connection,
    copy_id: int,
    shot: str,
    data: bytes,
    *,
    original_suffix: str = ".jpg",
) -> StoredPhoto:
    """Save one shot for one copy, replacing any previous photo of that shot."""
    if shot not in SHOTS:
        raise ValueError(f"shot must be one of {SHOTS}, got {shot!r}")

    directory = _copy_dir(copy_id)
    original = directory / f"{shot}-original{original_suffix}"
    listing = directory / f"{shot}.jpg"

    original.write_bytes(data)
    if not _to_listing_jpeg(original, listing):
        original.unlink(missing_ok=True)
        raise UnreadableImage(
            f"Could not decode the uploaded {original_suffix} for copy {copy_id}"
        )

    captured_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    conn.execute("DELETE FROM photos WHERE copy_id = ? AND shot = ?", (copy_id, shot))
    cursor = conn.execute(
        """
        INSERT INTO photos (copy_id, shot, original_path, listing_path, captured_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        (copy_id, shot, str(original), str(listing), captured_at),
    )
    conn.commit()

    return StoredPhoto(
        photo_id=cursor.lastrowid,
        copy_id=copy_id,
        shot=shot,
        original_path=original,
        listing_path=listing,
    )


def for_copy(conn: sqlite3.Connection, copy_id: int) -> dict[str, sqlite3.Row]:
    rows = conn.execute("SELECT * FROM photos WHERE copy_id = ?", (copy_id,)).fetchall()
    return {row["shot"]: row for row in rows}


def missing_shots(conn: sqlite3.Connection, copy_id: int) -> tuple[str, ...]:
    have = set(for_copy(conn, copy_id))
    return tuple(shot for shot in SHOTS if shot not in have)


def queue(conn: sqlite3.Connection, limit: int = 100) -> list[sqlite3.Row]:
    """Cards that still need photos, best candidates first.

    Only cards worth photographing appear: photos exist for eBay, and eBay is
    only worth the five minutes above its breakeven price. Everything cheaper
    lists on TCGplayer against a stock image and never needs a shot.
    """
    from . import economics as ec

    floor = ec.breakeven_price_cents(conn, "ebay", cards_in_order=1)

    rows = conn.execute(
        """
        SELECT c.copy_id, c.variant_id, c.condition_code,
               s.card_name, s.sub_type, s.set_name, s.card_number,
               m.current_price,
               (SELECT COUNT(*) FROM photos p WHERE p.copy_id = c.copy_id) AS photo_count
          FROM copies c
          JOIN catalog.screener_rows s ON s.variant_id = c.variant_id
          LEFT JOIN catalog.card_metrics m ON m.variant_id = c.variant_id
          JOIN copy_current_state cs ON cs.copy_id = c.copy_id
         WHERE cs.state = 'in_binder'
           AND m.current_price IS NOT NULL
         ORDER BY photo_count ASC, m.current_price DESC
         LIMIT ?
        """,
        (limit * 4,),
    ).fetchall()

    from . import catalog

    worth_it = []
    for row in rows:
        if row["photo_count"] >= len(SHOTS):
            continue
        price = catalog.market_price_cents(conn, row["variant_id"], row["condition_code"])
        if price and price >= floor:
            worth_it.append(row)
        if len(worth_it) >= limit:
            break
    return worth_it
