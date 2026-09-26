"""Group observations into restock episodes and score sources by speed and accuracy.

Reports of the same thing (one watched product, or one product text, at one
retailer, in the same signal family) within EPISODE_WINDOW of each other are
one episode. Each source's lag is measured from the earliest report, which
is what makes duplicate sources useful: they become a speed benchmark.
"""

from __future__ import annotations

import datetime as dt
import json
import sqlite3
import statistics
from dataclasses import dataclass

from .config import BLUESKY_ACCOUNTS
from .matching import normalize

# Bluesky accounts are scored separately: "bluesky:pokemonrestocks", not "bluesky".
_HANDLE_BY_DID = {did: handle.split(".")[0] for handle, did in BLUESKY_ACCOUNTS.items()}

EPISODE_WINDOW = dt.timedelta(minutes=60)
AVAILABILITY_SIGNALS = frozenset({"in_stock", "preorder", "drop", "queue", "invites", "drawing_open"})


def family(signal: str) -> str:
    return "availability" if signal in AVAILABILITY_SIGNALS else "announcement"


def reporter(source_id: str, author: str | None) -> str:
    handle = _HANDLE_BY_DID.get(author or "")
    return f"{source_id}:{handle}" if handle else source_id


def _keys(observation: sqlite3.Row) -> list[tuple[str, str | None]]:
    retailer = observation["retailer"] or "?"
    signal_family = family(observation["signal"])
    matches = json.loads(observation["watch_matches"] or "[]")
    if matches:
        return [(f"watch:{name}|{retailer}|{signal_family}", name) for name in matches]
    text_key = normalize(observation["product_text"] or observation["text"])[:60]
    return [(f"text:{text_key}|{retailer}|{signal_family}", None)]


def _seconds(later: str, earlier: str) -> int:
    return int((dt.datetime.fromisoformat(later) - dt.datetime.fromisoformat(earlier)).total_seconds())


def _recompute_lags(connection: sqlite3.Connection, episode_id: int) -> None:
    rows = connection.execute(
        "SELECT observation_id, source_id, seen_at FROM episode_observations WHERE episode_id = ? ORDER BY seen_at",
        (episode_id,),
    ).fetchall()
    opened = rows[0]
    connection.execute(
        "UPDATE episodes SET opened_at = ?, first_source_id = ?, last_seen_at = ? WHERE id = ?",
        (opened["seen_at"], opened["source_id"], rows[-1]["seen_at"], episode_id),
    )
    for row in rows:
        connection.execute(
            "UPDATE episode_observations SET lag_s = ? WHERE episode_id = ? AND observation_id = ?",
            (_seconds(row["seen_at"], opened["seen_at"]), episode_id, row["observation_id"]),
        )


def assign(connection: sqlite3.Connection, observation_id: int) -> list[int]:
    """Attach an observation to its episode(s), opening new ones as needed."""
    observation = connection.execute("SELECT * FROM observations WHERE id = ?", (observation_id,)).fetchone()
    if observation is None or not observation["is_tcg"]:
        return []
    seen_at = observation["source_time"] or observation["received_at"]
    seen = dt.datetime.fromisoformat(seen_at)
    episode_ids = []
    for episode_key, watch_item in _keys(observation):
        existing = connection.execute(
            "SELECT episode_id FROM episode_observations eo JOIN episodes e ON e.id = eo.episode_id "
            "WHERE eo.observation_id = ? AND e.episode_key = ?",
            (observation_id, episode_key),
        ).fetchone()
        if existing:
            episode_ids.append(existing["episode_id"])
            continue
        candidates = connection.execute(
            "SELECT * FROM episodes WHERE episode_key = ? ORDER BY last_seen_at DESC", (episode_key,)
        ).fetchall()
        episode = next(
            (
                row for row in candidates
                if dt.datetime.fromisoformat(row["opened_at"]) - EPISODE_WINDOW
                <= seen
                <= dt.datetime.fromisoformat(row["last_seen_at"]) + EPISODE_WINDOW
            ),
            None,
        )
        if episode is None:
            cursor = connection.execute(
                """
                INSERT INTO episodes (episode_key, watch_item, retailer, family, first_signal, product_text,
                                      opened_at, last_seen_at, first_source_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    episode_key, watch_item, observation["retailer"], family(observation["signal"]),
                    observation["signal"], observation["product_text"] or observation["text"],
                    seen_at, seen_at, reporter(observation["source_id"], observation["author"]),
                ),
            )
            episode_id = cursor.lastrowid
        else:
            episode_id = episode["id"]
        connection.execute(
            "INSERT INTO episode_observations (episode_id, observation_id, source_id, seen_at, lag_s) VALUES (?, ?, ?, ?, 0)",
            (episode_id, observation_id, reporter(observation["source_id"], observation["author"]), seen_at),
        )
        _recompute_lags(connection, episode_id)
        episode_ids.append(episode_id)
    connection.commit()
    return episode_ids


def assign_pending(connection: sqlite3.Connection) -> list[int]:
    """Assign every TCG observation not yet in an episode; returns touched episode ids."""
    pending = connection.execute(
        "SELECT id FROM observations WHERE is_tcg = 1 AND id NOT IN (SELECT observation_id FROM episode_observations) ORDER BY id"
    ).fetchall()
    touched: list[int] = []
    for row in pending:
        touched.extend(assign(connection, row["id"]))
    return sorted(set(touched))


def set_verdict(connection: sqlite3.Connection, episode_id: int, verdict: str) -> None:
    if verdict not in {"real", "false"}:
        raise ValueError("verdict must be 'real' or 'false'")
    connection.execute("UPDATE episodes SET verdict = ? WHERE id = ?", (verdict, episode_id))
    connection.commit()


@dataclass(frozen=True)
class SourceScore:
    source_id: str
    episodes: int
    first: int                  # episodes this source reported first (ties count)
    median_lag_s: int | None    # over episodes it did not report first
    accuracy: float | None      # real / (real + false) over judged episodes


def scorecard(connection: sqlite3.Connection) -> list[SourceScore]:
    rows = connection.execute(
        """
        SELECT eo.source_id, eo.episode_id, MIN(eo.lag_s) AS lag_s, e.verdict
        FROM episode_observations eo JOIN episodes e ON e.id = eo.episode_id
        GROUP BY eo.source_id, eo.episode_id
        """
    ).fetchall()
    by_source: dict[str, list[sqlite3.Row]] = {}
    for row in rows:
        by_source.setdefault(row["source_id"], []).append(row)
    scores = []
    for source_id, entries in sorted(by_source.items()):
        lags = [entry["lag_s"] for entry in entries if entry["lag_s"] > 0]
        judged = [entry["verdict"] for entry in entries if entry["verdict"]]
        scores.append(
            SourceScore(
                source_id=source_id,
                episodes=len(entries),
                first=sum(1 for entry in entries if entry["lag_s"] == 0),
                median_lag_s=int(statistics.median(lags)) if lags else None,
                accuracy=(judged.count("real") / len(judged)) if judged else None,
            )
        )
    return scores
