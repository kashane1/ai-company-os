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


def test_never_run_and_failing_sources_are_due(connection):
    assert sources.is_due(connection, "pokebeach_rss", NOW)
    sources.record_run(connection, "pokebeach_rss", ok=False, error="timeout", now=NOW)
    assert sources.is_due(connection, "pokebeach_rss", NOW + dt.timedelta(minutes=1))


def test_polled_sources_are_due_again_after_their_cadence(connection):
    sources.record_run(connection, "pokebeach_rss", ok=True, now=NOW)
    assert not sources.is_due(connection, "pokebeach_rss", NOW + dt.timedelta(minutes=10))
    # A minute of slack so a 15-minute timer does not skip every other run.
    assert sources.is_due(connection, "pokebeach_rss", NOW + dt.timedelta(minutes=14, seconds=30))


def test_tcgcsv_is_due_once_after_each_nightly_rebuild(connection):
    before_rebuild = dt.datetime(2026, 9, 26, 19, 0, tzinfo=dt.timezone.utc)
    after_rebuild = dt.datetime(2026, 9, 26, 20, 45, tzinfo=dt.timezone.utc)
    sources.record_run(connection, "tcgcsv", ok=True, now=dt.datetime(2026, 9, 25, 21, 0, tzinfo=dt.timezone.utc))
    assert not sources.is_due(connection, "tcgcsv", before_rebuild)
    assert sources.is_due(connection, "tcgcsv", after_rebuild)
    sources.record_run(connection, "tcgcsv", ok=True, now=after_rebuild)
    assert not sources.is_due(connection, "tcgcsv", after_rebuild + dt.timedelta(hours=2))


def test_manual_sources_report_manual_until_used(connection):
    statuses = {row.source_id: row.status for row in sources.health(connection, NOW)}
    assert statuses["guppy"] == "manual"
