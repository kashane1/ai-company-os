---
status: pending
priority: p3
issue_id: "118"
tags: [open-tcg, security, maintenance]
dependencies: []
---

# OpenTCG: low-severity security hygiene from the 2026-09-29 review

## Findings

- **Terminal escapes:** ESC/OSC sequences in post and email text survive parsing and are printed raw to logs and `tail -f` (`radar/__main__.py`, `_print_observation`). Strip C0 and C1 control characters at ingest and at print.
- **Permissions:** `data/` is 0755, and `radar.db` (which holds email bodies), the logs and the inbox samples are 0644. The home directory (0750) and single user limit exposure. Run `chmod 700 data`, and add `Umask 63` to the plists.
- **Supply chain:** Makefile setup installs httpx, websockets and pytest unpinned, with no lockfile or hashes. Python 3.12.3 (Apr 2024) is missing later stdlib security fixes. Add a hashed lockfile with `--require-hashes`, and plan a Python upgrade.
- **Trusted-source checks:**
  - `handle_message` doesn't check the event's DID against `BLUESKY_ACCOUNTS`.
  - A non-string `text` raises an exception.
  - A garbage `createdAt` stores a row that crash-loops `assign_pending()` at startup (also todo 100).
- **Stored bodies:** `radar inbox-export` saves mail from any sender. Limit it to relevant senders and strip tracking links.

## Acceptance Criteria

- [ ] Each item is fixed, or explicitly accepted with a reason in this file.
