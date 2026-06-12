# worker-reply-sync

Read-only Gmail poller that captures inbound replies to BBW outreach (item 5).

It matches each new inbox message back to a prospect by the `BBW-<6char>` token
stamped below the email signature (sender address as fallback) and hands it to
`packages.agency.reply_sync.process_reply`, which:

- advances the lane row to `replied` (never downgrading a won/lost/DNC row),
- logs an **inbound** touch (excluded from the `sent` funnel metric by direction),
- writes a snippet to `state/prospects/outreach-lane/replies/<place_id>.md`,
- and for STOP-intent replies, writes to the suppression registry
  (`source="reply_stop"`) and flags the snippet for operator confirmation.

It **never** sends, labels, moves, or marks mail read. Scope is
`gmail.readonly`.

## Setup (one-time)

1. In Google Cloud Console, create an OAuth **Desktop app** client for the BBW
   inbox and download the client-secret JSON.
2. Save it where the worker expects it (or point `BBW_GMAIL_CREDENTIALS` at it):

   ```
   state/secrets/gmail-credentials.json
   ```

3. Mint a readonly user token (this is the only interactive step):

   ```
   pip install -e '.[reply-sync]'
   python apps/worker-reply-sync/main.py --auth
   ```

   A browser opens for consent; the token is written to
   `state/secrets/gmail-token.json` (or `BBW_GMAIL_TOKEN`). The loop is fully
   headless thereafter.

## Run

```
python apps/worker-reply-sync/main.py --once   # single cycle
python apps/worker-reply-sync/main.py          # loop forever
```

In production it is **not** run standalone — the runtime-supervisor starts it
(see `apps/runtime-supervisor/supervisor/specs.py`); launchd runs only the
supervisor.

## Config

| Env | Default | Purpose |
|---|---|---|
| `BBW_GMAIL_CREDENTIALS` | `state/secrets/gmail-credentials.json` | OAuth client secret |
| `BBW_GMAIL_TOKEN` | `state/secrets/gmail-token.json` | stored readonly user token |
| `BBW_GMAIL_ADDRESS` | _(unset)_ | our own address, to skip self-sent mail |
| `AGENCY_REPLY_SYNC_POLL_INTERVAL_SECS` | `120` | loop interval |

## Idempotency

State lives in `state/prospects/outreach-lane/reply-sync-state.json`: the last
Gmail `historyId` cursor plus a bounded processed-thread set. On first run it
backfills `in:inbox newer_than:14d`; subsequent runs are incremental via
`history.list(messageAdded)`. Re-running a cycle reprocesses nothing.
