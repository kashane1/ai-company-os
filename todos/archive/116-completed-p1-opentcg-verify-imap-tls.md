---
status: completed
priority: p1
issue_id: "116"
tags: [open-tcg, security, imap]
dependencies: []
---

# OpenTCG: verify Gmail's certificate on the IMAP connection

## Problem Statement

`imaplib.IMAP4_SSL(IMAP_HOST, timeout=30)` passed no `ssl_context`, so Python 3.12's stdlib context skipped certificate verification (`verify_mode 0`, `check_hostname False`). An on-path attacker could impersonate imap.gmail.com and capture the Gmail app password at login. The security review proved this with a local fake IMAP server.

## Recommended Action

Pass a verifying context with certifi's roots, shared as `radar/http.py:tls_context()`. As a precaution, the founder rotates the app password, because it was sent over unverified TLS for about two days of logins on the home network.

## Acceptance Criteria

- [x] `ImapMailbox` passes a `CERT_REQUIRED` + `check_hostname` context (test `test_imap_connection_verifies_gmails_certificate`).
- [x] The inbox LaunchAgent reconnects successfully with verification on (2026-09-29 23:43 UTC).
- [ ] Founder rotates the Gmail app password (optional precaution).

## ✓ Completed 2026-09-29
Landed in the OpenTCG audit commit. IMAP and Bluesky now share one certificate-verifying TLS context.
