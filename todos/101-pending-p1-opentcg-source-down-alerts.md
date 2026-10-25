---
status: pending
priority: p1
issue_id: "101"
tags: [open-tcg, reliability, observability]
dependencies: ["100"]
---

# OpenTCG: alert the founder when a source is down, and log real errors

## Problem Statement

If the inbox login breaks, the Bluesky stream stalls, or a daily poll fails, the radar goes quiet and nobody knows. Silence looks like "no restocks". Build-out 1, slice 5, promised "a stale source sends one 'source down' push", and that was never built.

## Findings

- `radar/sources.py` computes the `failing` and `stale` statuses, but nothing reads them except the `sources` CLI.
- `last_error` is cleared on the next success, and no tracebacks are logged; the `*.err.log` files stay empty even on failures.
- launchd restarts crashed daemons, but a daemon stuck in a backoff loop looks alive.

## Proposed Solutions

1. **(Recommended)** Add a health check to the 15-minute sync job. If any enabled source has been `failing` or `stale` for longer than a threshold (the stream: 30 min without a heartbeat), send one "OpenTCG source down: <source> since <time>" notification per outage, and one "recovered" when it clears. Also flag any LaunchAgent that is not running.
2. Log tracebacks to the `*.err.log` files, and keep an error history table so errors aren't overwritten.

## Acceptance Criteria

- [ ] Simulated outages (inbox auth failure, stream silent for 30 min, sync error) each produce exactly one notification, and one recovery notice.
- [ ] Error tracebacks appear in the err logs, and recent errors survive later successes.
