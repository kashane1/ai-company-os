---
status: pending
priority: p1
issue_id: "100"
tags: [open-tcg, reliability, sqlite]
dependencies: []
---

# OpenTCG: make ingestion crash-proof so no alert is ever silently lost

## Problem Statement

A single bad input, or a transient database lock, can stall a source or drop an alert with no visible error. The reliability review verified each case below in simulation.

## Findings

- **Poison email:** `get_content()` raises `LookupError` on an unknown charset (`radar/inbox/message.py`). `poll` aborts before saving the cursor, so every later mail is blocked, and the backoff resets to 5 s after each login, so it re-logs in every ~5 s forever (`radar/inbox/reader.py`).
- **Lost after commit:** the stream commits the observation and cursor before `on_observation` runs. If assign or notify then raises (a locked DB, or a half-edited `watchlist.toml`), the row is never assigned, and a replay is ignored as a duplicate. A mid-batch inbox failure can commit rows without their notification. `cmd_inbox` never runs `assign_pending`.
- **Long write transactions:** transactions stay open across network fetches (IMAP batches, tcgcsv, Southern Hobby pages), with only the default 5 s lock timeout. A second writer got "database is locked" after 5.4 s.
- **Bad Jetstream event:** a malformed event makes the stream reconnect every 1 s forever.
- **Race:** `episodes.assign` reads, then inserts, outside a transaction, so the stream and inbox daemons could both open the same episode.
- A timezone-less timestamp raises `TypeError` in `assign`, including in the startup `assign_pending`, which crash-loops the stream.
- **More stalls found by the security review**, all tested with real `poll()`. Each is raised before `is_relevant`, so ordinary unrelated mail can trigger them:
  - `LookupError` for charsets such as iso-8859-8-i, windows-874 and unknown-8bit
  - `OverflowError` for `Date: Fri, 31 Dec 9999 23:59:59 -0100`
  - `RecursionError` at 974 nested multipart levels (a 54 KB message)

## Proposed Solutions

1. **(Recommended)** Handle each message in its own `try`: record the error, skip the message, advance the cursor. Decode with a fallback charset. Reset backoff only after a successful poll. Settle via `assign_pending()` after every message or poll instead of trusting returned ids. Roll back in error handlers before `record_run`. Fetch first, then write in short transactions. Use `connect(timeout=30)` / `busy_timeout`, and `BEGIN IMMEDIATE` in `assign`. Guard `record_run` so it can never kill a loop.

## Acceptance Criteria

- [ ] Tests with a fake socket and fake mailbox: a bad message is skipped and later ones are processed; an `on_observation` failure is retried by `assign_pending`; a mid-batch failure loses nothing; backoff behaves.
- [ ] A two-connection lock test passes. No write transaction is held across a network call.
- [ ] A broken-charset email and a timezone-less timestamp no longer stall or crash anything.
