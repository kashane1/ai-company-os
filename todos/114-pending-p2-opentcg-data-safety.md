---
status: pending
priority: p2
issue_id: "114"
tags: [open-tcg, data, maintenance]
dependencies: []
---

# OpenTCG: back up irreplaceable data and fix latent data-model issues

## Problem Statement

`data/radar.db` holds data that can't be rebuilt, such as episode verdicts, the Guppy log and calendar history, and nothing backs it up.

## Findings

- A UIDVALIDITY of 2^31 or more would overflow the packed IMAP cursor and stall the inbox. Gmail's value here is 1, so the problem is latent (`radar/inbox/reader.py`).
- `radar log --retailer target` is stored as typed, so Guppy entries won't join "Target" episodes, which breaks the benchmark (`radar/manual.py`).

## Proposed Solutions

1. **(Recommended)** A nightly SQLite backup through the online backup API, into `data/backups/`, keeping 14 days.
2. `radar export`, which writes JSON of founder-entered data.
3. Two-column IMAP cursor state.
4. Canonical retailer names everywhere, through one alias table.

## Acceptance Criteria

- [ ] Backups rotate and a restore test passes.
- [ ] The cursor handles a large UIDVALIDITY value.
- [ ] `radar log --retailer target` joins "Target" episodes.
