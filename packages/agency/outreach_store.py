"""SQLite-backed store for outreach touches and operator contact overrides.

Why a database (and not more JSON): the action dashboard is the first
*concurrent writer* over outreach state — an operator clicking "Log sent"
while a follow-up tab is open, or two rapid clicks racing. Append-only
touches and last-write-wins overrides want transactional writes, not
read-modify-write over a shared JSON file.

This mirrors ``packages/db/control_plane_db.py``: SQLite by default (via the
platform-standard ``open_platform_db`` bootstrap — WAL, busy_timeout), and
Postgres when ``AI_COMPANY_OS_DATABASE_URL`` points at one. Flipping that one
env var is the entire migration path; no caller changes.

Boundary: this stores *records of human-gated sends*. It sends nothing. A
touch row exists only because the operator confirmed a manual send.
"""

from __future__ import annotations

import json
import os
import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterator
from urllib.parse import urlparse

from packages.config.settings import DATABASE_URL_ENV_VAR, load_runtime_paths
from packages.db.connection import open_platform_db

try:  # pragma: no cover - exercised only when postgres is configured.
    import psycopg
    from psycopg.rows import dict_row
except ImportError:  # pragma: no cover
    psycopg = None
    dict_row = None

TOUCHES_TABLE = "outreach_touches"
OVERRIDES_TABLE = "outreach_contact_overrides"
SUPPRESSIONS_TABLE = "outreach_suppressions"
REF_TOKENS_TABLE = "outreach_ref_tokens"

# Direction of a logged touch. Outbound = a human-gated send; inbound = a reply
# captured by reply-sync (item 5). Funnel "sent" counts outbound only, so an
# inbound touch never inflates the sent metric.
OUTBOUND = "outbound"
INBOUND = "inbound"

# The channels a button can record a send for. Kept here so the store rejects
# typos instead of silently logging an unknown channel.
ALLOWED_CHANNELS = ("email", "sms", "call", "facebook_dm", "instagram_dm")

# A/B "arm" recorded on every touch so sends can be compared in funnel
# telemetry. ``demo-link`` is the current copy (the preview-link pitch). The
# store accepts any non-empty variant string; KNOWN_VARIANTS just seeds the
# dashboard's per-session selector — edit it to add real arms.
DEFAULT_VARIANT = "demo-link"
KNOWN_VARIANTS = ("demo-link", "short", "social-proof")

# Contact fields an operator may edit inline. These mirror the keys the lane row
# and the scanned record use, so the effective-contact merge is a plain lookup.
ALLOWED_OVERRIDE_FIELDS = (
    "contact_email",
    "phone",
    "contact_instagram",
    "contact_facebook",
    "contact_booking_url",
)

# Maps the various channel spellings used by the lane CLI, the recommended-channel
# logic, and legacy JSONL onto the canonical ALLOWED_CHANNELS. ``sms_or_call``
# (the phone-first recommendation) resolves to ``call`` — most of these SMB
# numbers are landlines, so a logged phone touch is overwhelmingly a call.
_CHANNEL_ALIASES = {
    "email": "email",
    "sms": "sms",
    "text": "sms",
    "sms_or_call": "call",
    "phone": "call",
    "call": "call",
    "facebook": "facebook_dm",
    "messenger": "facebook_dm",
    "facebook_dm": "facebook_dm",
    "instagram": "instagram_dm",
    "instagram_dm": "instagram_dm",
}


def normalize_channel(channel: str) -> str:
    """Canonicalize a channel label to one of ALLOWED_CHANNELS (or pass through
    an unknown lower-cased value so the caller can reject it)."""
    key = (channel or "").strip().lower()
    return _CHANNEL_ALIASES.get(key, key)


def _now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


@dataclass(frozen=True)
class OutreachStoreConfig:
    backend: str
    dsn: str


def default_outreach_db_path(repo_root: Path | None = None) -> Path:
    return (
        load_runtime_paths(repo_root).state_root
        / "prospects"
        / "outreach-lane"
        / "outreach.sqlite3"
    )


class OutreachStore:
    """Transactional store for touches + contact overrides.

    Pass ``sqlite_path`` to point at a specific file (tests use a tmp path);
    otherwise it defaults to ``state/prospects/outreach-lane/outreach.sqlite3``
    or the Postgres DSN from the environment.
    """

    def __init__(self, *, sqlite_path: Path | None = None, repo_root: Path | None = None) -> None:
        self.config = self._load_config(sqlite_path=sqlite_path, repo_root=repo_root)

    def _load_config(
        self, *, sqlite_path: Path | None, repo_root: Path | None
    ) -> OutreachStoreConfig:
        raw_url = os.environ.get(DATABASE_URL_ENV_VAR)
        if raw_url:
            parsed = urlparse(raw_url)
            if parsed.scheme in {"postgres", "postgresql"}:
                return OutreachStoreConfig(backend="postgres", dsn=raw_url)
            if parsed.scheme == "sqlite" and parsed.path:
                return OutreachStoreConfig(backend="sqlite", dsn=parsed.path)
        path = sqlite_path or default_outreach_db_path(repo_root)
        return OutreachStoreConfig(backend="sqlite", dsn=Path(path).as_posix())

    def placeholder(self, name: str) -> str:
        return f"%({name})s" if self.config.backend == "postgres" else f":{name}"

    @contextmanager
    def connection(self) -> Iterator[Any]:
        if self.config.backend == "postgres":  # pragma: no cover - needs a live postgres.
            if psycopg is None:
                raise RuntimeError(
                    "psycopg is required when AI_COMPANY_OS_DATABASE_URL points to Postgres."
                )
            with psycopg.connect(self.config.dsn, row_factory=dict_row) as connection:
                self.ensure_schema(connection)
                yield connection
                connection.commit()
            return

        connection = open_platform_db(Path(self.config.dsn))
        connection.row_factory = sqlite3.Row
        try:
            self.ensure_schema(connection)
            yield connection
            connection.commit()
        finally:
            connection.close()

    def ensure_schema(self, connection: Any) -> None:
        integer_pk = (
            "INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY"
            if self.config.backend == "postgres"
            else "INTEGER PRIMARY KEY AUTOINCREMENT"
        )
        cursor = connection.cursor()
        cursor.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {TOUCHES_TABLE} (
                id {integer_pk},
                place_id TEXT NOT NULL,
                channel TEXT NOT NULL,
                sent_at TEXT NOT NULL,
                via TEXT NOT NULL,
                note TEXT NOT NULL DEFAULT '',
                variant TEXT NOT NULL DEFAULT '{DEFAULT_VARIANT}',
                direction TEXT NOT NULL DEFAULT '{OUTBOUND}'
            )
            """
        )
        cursor.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {OVERRIDES_TABLE} (
                place_id TEXT NOT NULL,
                field TEXT NOT NULL,
                value TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                PRIMARY KEY (place_id, field)
            )
            """
        )
        # Fail-closed do-not-contact registry. One row per suppressed *key*: a
        # place_id ("place:<id>") or a normalized contact handle ("email:<addr>"
        # etc.). Un-suppression is manual-edit only — there is no delete API.
        cursor.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {SUPPRESSIONS_TABLE} (
                key TEXT PRIMARY KEY,
                kind TEXT NOT NULL,
                reason TEXT NOT NULL,
                source TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        # Outbound-token registry: which ``BBW-<6char>`` we actually stamped on a
        # send, mapped to the prospect. Reply-sync matches inbound mail by token,
        # so only tokens that were really sent are resolvable. Deterministic from
        # place_id, but persisted as an audit trail + reverse lookup.
        cursor.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {REF_TOKENS_TABLE} (
                token TEXT PRIMARY KEY,
                place_id TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        cursor.execute(
            f"CREATE INDEX IF NOT EXISTS idx_touches_place ON {TOUCHES_TABLE} (place_id)"
        )
        # Additive migration for DBs created before the variant column existed.
        if not self._column_exists(connection, TOUCHES_TABLE, "variant"):
            cursor.execute(
                f"ALTER TABLE {TOUCHES_TABLE} "
                f"ADD COLUMN variant TEXT NOT NULL DEFAULT '{DEFAULT_VARIANT}'"
            )
        # Additive migration for DBs created before the direction column existed.
        # Pre-existing rows are all human-gated sends, so 'outbound' is correct.
        if not self._column_exists(connection, TOUCHES_TABLE, "direction"):
            cursor.execute(
                f"ALTER TABLE {TOUCHES_TABLE} "
                f"ADD COLUMN direction TEXT NOT NULL DEFAULT '{OUTBOUND}'"
            )

    def _column_exists(self, connection: Any, table: str, column: str) -> bool:
        cursor = connection.cursor()
        if self.config.backend == "postgres":  # pragma: no cover - needs live postgres.
            cursor.execute(
                "SELECT 1 FROM information_schema.columns "
                "WHERE table_name = %(table)s AND column_name = %(column)s",
                {"table": table, "column": column},
            )
            return cursor.fetchone() is not None
        cursor.execute(f"PRAGMA table_info({table})")
        return any(row[1] == column for row in cursor.fetchall())

    # ------------------------------------------------------------------ touches
    def append_touch(
        self,
        place_id: str,
        channel: str,
        *,
        via: str = "dashboard",
        note: str = "",
        sent_at: str | None = None,
        variant: str = DEFAULT_VARIANT,
        direction: str = OUTBOUND,
    ) -> dict[str, object]:
        place_id = place_id.strip()
        if not place_id:
            raise ValueError("place_id is required")
        if channel not in ALLOWED_CHANNELS:
            raise ValueError(
                f"unsupported channel {channel!r}; allowed: {', '.join(ALLOWED_CHANNELS)}"
            )
        direction = (direction or "").strip().lower() or OUTBOUND
        if direction not in (OUTBOUND, INBOUND):
            raise ValueError(
                f"unsupported direction {direction!r}; allowed: {OUTBOUND}, {INBOUND}"
            )
        row = {
            "place_id": place_id,
            "channel": channel,
            "sent_at": sent_at or _now_iso(),
            "via": via,
            "note": note,
            "variant": (variant or "").strip() or DEFAULT_VARIANT,
            "direction": direction,
        }
        query = (
            f"INSERT INTO {TOUCHES_TABLE} "
            f"(place_id, channel, sent_at, via, note, variant, direction) VALUES "
            f"({self.placeholder('place_id')}, {self.placeholder('channel')}, "
            f"{self.placeholder('sent_at')}, {self.placeholder('via')}, "
            f"{self.placeholder('note')}, {self.placeholder('variant')}, "
            f"{self.placeholder('direction')})"
        )
        with self.connection() as connection:
            connection.cursor().execute(query, row)
        return row

    def list_touches(self, place_id: str) -> list[dict[str, object]]:
        # Full per-prospect history, both directions (outbound sends + inbound
        # replies), so the dashboard/CLI can show the whole conversation.
        query = (
            f"SELECT place_id, channel, sent_at, via, note, variant, direction "
            f"FROM {TOUCHES_TABLE} "
            f"WHERE place_id = {self.placeholder('place_id')} ORDER BY sent_at ASC, id ASC"
        )
        with self.connection() as connection:
            cursor = connection.cursor()
            cursor.execute(query, {"place_id": place_id})
            return [self._row_to_dict(row) for row in cursor.fetchall()]

    def variant_counts(self) -> dict[str, int]:
        """``{variant: touch_count}`` across all rows — the A/B arm tally the
        funnel report reads. Counts touches (not distinct places): a prospect
        sent two arms contributes to both. Outbound only — an inbound reply is
        not a send and must not count toward an A/B arm."""
        query = (
            f"SELECT variant, COUNT(*) AS count FROM {TOUCHES_TABLE} "
            f"WHERE direction = '{OUTBOUND}' GROUP BY variant"
        )
        counts: dict[str, int] = {}
        with self.connection() as connection:
            cursor = connection.cursor()
            cursor.execute(query, {})
            for row in cursor.fetchall():
                data = self._row_to_dict(row)
                counts[str(data["variant"] or DEFAULT_VARIANT)] = int(data["count"])
        return counts

    def touch_summary(self) -> dict[str, dict[str, dict[str, object]]]:
        """``{place_id: {channel: {"count": n, "last_sent_at": iso}}}`` for sends.

        Outbound only — this is the "sent" view both the funnel scoreboard and the
        dashboard's per-channel counts read; an inbound reply is tracked via the
        lane's ``replied`` status, never as a send here.
        """
        query = (
            f"SELECT place_id, channel, COUNT(*) AS count, MAX(sent_at) AS last_sent_at "
            f"FROM {TOUCHES_TABLE} WHERE direction = '{OUTBOUND}' GROUP BY place_id, channel"
        )
        summary: dict[str, dict[str, dict[str, object]]] = {}
        with self.connection() as connection:
            cursor = connection.cursor()
            cursor.execute(query, {})
            for row in cursor.fetchall():
                data = self._row_to_dict(row)
                place = str(data["place_id"])
                summary.setdefault(place, {})[str(data["channel"])] = {
                    "count": int(data["count"]),
                    "last_sent_at": str(data["last_sent_at"] or ""),
                }
        return summary

    # --------------------------------------------------------------- overrides
    def set_override(self, place_id: str, field: str, value: str) -> dict[str, object]:
        place_id = place_id.strip()
        if not place_id:
            raise ValueError("place_id is required")
        if field not in ALLOWED_OVERRIDE_FIELDS:
            raise ValueError(
                f"unsupported field {field!r}; allowed: {', '.join(ALLOWED_OVERRIDE_FIELDS)}"
            )
        row = {
            "place_id": place_id,
            "field": field,
            "value": value.strip(),
            "updated_at": _now_iso(),
        }
        # Upsert: SQLite and Postgres both honour ON CONFLICT on the PK.
        query = (
            f"INSERT INTO {OVERRIDES_TABLE} (place_id, field, value, updated_at) VALUES "
            f"({self.placeholder('place_id')}, {self.placeholder('field')}, "
            f"{self.placeholder('value')}, {self.placeholder('updated_at')}) "
            f"ON CONFLICT (place_id, field) DO UPDATE SET "
            f"value = {self.placeholder('value')}, updated_at = {self.placeholder('updated_at')}"
        )
        with self.connection() as connection:
            connection.cursor().execute(query, row)
        return row

    def get_overrides(self, place_id: str) -> dict[str, str]:
        query = (
            f"SELECT field, value FROM {OVERRIDES_TABLE} "
            f"WHERE place_id = {self.placeholder('place_id')}"
        )
        with self.connection() as connection:
            cursor = connection.cursor()
            cursor.execute(query, {"place_id": place_id})
            return {str(r["field"]): str(r["value"]) for r in cursor.fetchall()}

    def all_overrides(self) -> dict[str, dict[str, str]]:
        query = f"SELECT place_id, field, value FROM {OVERRIDES_TABLE}"
        out: dict[str, dict[str, str]] = {}
        with self.connection() as connection:
            cursor = connection.cursor()
            cursor.execute(query, {})
            for row in cursor.fetchall():
                data = self._row_to_dict(row)
                out.setdefault(str(data["place_id"]), {})[str(data["field"])] = str(
                    data["value"]
                )
        return out

    # ------------------------------------------------------------- suppression
    def suppress_key(self, key: str, kind: str, reason: str, source: str) -> dict[str, object]:
        """Record a do-not-contact key. Upsert keeps the *earliest* created_at
        and the *first* reason/source so the original disqualification wins."""
        key = (key or "").strip()
        if not key:
            raise ValueError("suppression key is required")
        row = {
            "key": key,
            "kind": kind,
            "reason": reason,
            "source": source,
            "created_at": _now_iso(),
        }
        query = (
            f"INSERT INTO {SUPPRESSIONS_TABLE} (key, kind, reason, source, created_at) VALUES "
            f"({self.placeholder('key')}, {self.placeholder('kind')}, "
            f"{self.placeholder('reason')}, {self.placeholder('source')}, "
            f"{self.placeholder('created_at')}) "
            f"ON CONFLICT (key) DO NOTHING"
        )
        with self.connection() as connection:
            connection.cursor().execute(query, row)
        return row

    def is_key_suppressed(self, key: str) -> bool:
        query = (
            f"SELECT 1 FROM {SUPPRESSIONS_TABLE} WHERE key = {self.placeholder('key')}"
        )
        with self.connection() as connection:
            cursor = connection.cursor()
            cursor.execute(query, {"key": (key or "").strip()})
            return cursor.fetchone() is not None

    def suppressed_keys(self) -> set[str]:
        query = f"SELECT key FROM {SUPPRESSIONS_TABLE}"
        with self.connection() as connection:
            cursor = connection.cursor()
            cursor.execute(query, {})
            return {str(self._row_to_dict(row)["key"]) for row in cursor.fetchall()}

    def list_suppressions(self) -> list[dict[str, object]]:
        query = (
            f"SELECT key, kind, reason, source, created_at FROM {SUPPRESSIONS_TABLE} "
            f"ORDER BY created_at ASC, key ASC"
        )
        with self.connection() as connection:
            cursor = connection.cursor()
            cursor.execute(query, {})
            return [self._row_to_dict(row) for row in cursor.fetchall()]

    # ------------------------------------------------------------- ref tokens
    def record_ref_token(self, token: str, place_id: str) -> dict[str, object]:
        """Persist a ``token -> place_id`` mapping at send time. Idempotent: the
        token is deterministic, so re-recording the same send is a no-op."""
        token = (token or "").strip()
        place_id = (place_id or "").strip()
        if not token:
            raise ValueError("ref token is required")
        if not place_id:
            raise ValueError("place_id is required")
        row = {"token": token, "place_id": place_id, "created_at": _now_iso()}
        query = (
            f"INSERT INTO {REF_TOKENS_TABLE} (token, place_id, created_at) VALUES "
            f"({self.placeholder('token')}, {self.placeholder('place_id')}, "
            f"{self.placeholder('created_at')}) "
            f"ON CONFLICT (token) DO NOTHING"
        )
        with self.connection() as connection:
            connection.cursor().execute(query, row)
        return row

    def place_id_for_token(self, token: str) -> str | None:
        """The prospect a sent token maps to, or ``None`` if we never sent it."""
        query = (
            f"SELECT place_id FROM {REF_TOKENS_TABLE} "
            f"WHERE token = {self.placeholder('token')}"
        )
        with self.connection() as connection:
            cursor = connection.cursor()
            cursor.execute(query, {"token": (token or "").strip()})
            row = cursor.fetchone()
            return str(self._row_to_dict(row)["place_id"]) if row else None

    # ----------------------------------------------------------------- import
    def import_legacy_jsonl(self, path: Path) -> int:
        """One-time migration of pre-SQLite ``touches.jsonl`` rows. Idempotency is
        the caller's concern; this appends every well-formed line it finds.
        """
        if not path.exists():
            return 0
        imported = 0
        for line in path.read_text().splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                payload = json.loads(line)
            except ValueError:
                continue
            channel = self._normalize_legacy_channel(str(payload.get("channel", "")))
            place_id = str(payload.get("place_id", "")).strip()
            if not place_id or channel not in ALLOWED_CHANNELS:
                continue
            self.append_touch(
                place_id,
                channel,
                via="legacy_jsonl",
                note=str(payload.get("notes", "")),
                sent_at=str(payload.get("occurred_at", "")) or None,
            )
            imported += 1
        return imported

    @staticmethod
    def _normalize_legacy_channel(channel: str) -> str:
        return normalize_channel(channel)

    @staticmethod
    def _row_to_dict(row: Any) -> dict[str, object]:
        if isinstance(row, sqlite3.Row):
            return {key: row[key] for key in row.keys()}
        return dict(row)


__all__ = [
    "OutreachStore",
    "OutreachStoreConfig",
    "ALLOWED_CHANNELS",
    "ALLOWED_OVERRIDE_FIELDS",
    "DEFAULT_VARIANT",
    "KNOWN_VARIANTS",
    "OUTBOUND",
    "INBOUND",
    "normalize_channel",
    "default_outreach_db_path",
]
