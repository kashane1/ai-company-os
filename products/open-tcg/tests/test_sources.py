"""Source registry and health states."""

from __future__ import annotations

import datetime as dt

from radar import sources

from .conftest import NOW


def status_of(connection, source_id: str, now: dt.datetime) -> str:
    return {row.source_id: row.status for row in sources.health(connection, now)}[source_id]


def test_every_registered_source_starts_as_never_run(connection):
    statuses = {row.source_id: row.status for row in sources.health(connection, NOW)}
    assert statuses["tcgcsv"] == "never_run"
    assert statuses["southern_hobby"] == "never_run"
    assert statuses["pokebeach_rss"] == "never_run"


def test_blocked_sources_are_registered_disabled_with_a_reason(connection):
    rows = {row.source_id: row for row in sources.health(connection, NOW)}
    assert rows["pokemon_news"].status == "disabled"
    assert "bot" in rows["pokemon_news"].note.lower()


def test_success_is_ok_until_three_cadences_pass(connection):
    sources.record_run(connection, "pokebeach_rss", ok=True, now=NOW)
    cadence = sources.get("pokebeach_rss").cadence_s
    assert status_of(connection, "pokebeach_rss", NOW + dt.timedelta(seconds=cadence * 3 - 1)) == "ok"
    assert status_of(connection, "pokebeach_rss", NOW + dt.timedelta(seconds=cadence * 3 + 1)) == "stale"


def test_failures_are_counted_and_reset_by_success(connection):
    sources.record_run(connection, "tcgcsv", ok=False, error="HTTP 503", now=NOW)
    sources.record_run(connection, "tcgcsv", ok=False, error="HTTP 503", now=NOW)
    row = {r.source_id: r for r in sources.health(connection, NOW)}["tcgcsv"]
    assert row.status == "failing"
    assert row.consecutive_failures == 2
    assert row.last_error == "HTTP 503"

    sources.record_run(connection, "tcgcsv", ok=True, now=NOW)
    row = {r.source_id: r for r in sources.health(connection, NOW)}["tcgcsv"]
    assert row.status == "ok"
    assert row.consecutive_failures == 0


def test_has_succeeded_marks_the_bootstrap_boundary(connection):
    assert not sources.has_succeeded(connection, "tcgcsv")
    sources.record_run(connection, "tcgcsv", ok=True, now=NOW)
    assert sources.has_succeeded(connection, "tcgcsv")
