---
status: pending
priority: p1
issue_id: "102"
tags: [open-tcg, security, ssrf]
dependencies: []
---

# OpenTCG: harden link resolution, browser opens, and sender trust

## Problem Statement

The radar acts on untrusted content. The 2026-09-29 security review demonstrated each of these with offline proofs of concept against the real code, using loopback servers and stubbed send/open:

- **SSRF from any email:** `is_relevant` accepts any sender who writes "pokemon". The first link goes to `resolve_url` (`radar/notify.py`), which is a GET with `follow_redirects=True`, no scheme, IP or per-hop checks, and the whole body buffered. A mail from an outside domain claiming a Costco restock made the radar GET the attacker's URL and follow a 302 to `http://127.0.0.1:PORT/...`. Blind GETs to loopback, LAN and link-local addresses work, including plain http.
- **Resource exhaustion:** a 120 MB body raised memory from 34 to 306 MB, and a 1-byte-every-3-s trickle held the call for 24 s, because timeouts are per read.
- **Forced navigation:** `lands_on` checks only the host, so any `*.costco.com` link from an outsider auto-opens in the signed-in Brave.
- **Alert suppression with a forged `Date`:** an outsider email for a watched item, dated 30–45 min in the past, followed by the real Bluesky alert, produced zero notifications (see also todo 099).
- **CPU:** `_NIS_RETAILER` is quadratic on the uncapped subject line: 20/40/60 KB subjects cost 1.0/4.1/9.1 s per email.
- The repository is public, so `watchlist.toml` and its thresholds are visible to anyone.

What already holds: `lands_on` rejects lookalikes (costco.com.evil.net, evilcostco.com, userinfo tricks, punycode, trailing dots). osascript receives text only as arguments. All SQL is parameterized.

## Proposed Solutions

1. **(Recommended)**
   - Allow `open_in_browser` only for authenticated sources: allowlisted Bluesky DIDs, and email with `dmarc=pass` in `Authentication-Results` from nowinstock.net or keepa.com.
   - Resolve links with `follow_redirects=False`, checking each hop: https only, host on a shortener or retailer allowlist, and never a private, loopback or link-local IP. Cap it at about 5 hops, stream at most ~64 KB, and set a total deadline of about 5 s.
   - Pin the exact retailer hosts to open (www.costco.com and so on).
   - Send the banner before resolving (reliability review, finding 14).
   - Cap subjects at about 300 characters and bound the regex (`[^:\n]{1,80}?`).
   - Clamp email `Date` to the receive time plus or minus 5 minutes.

## Acceptance Criteria

- [ ] Each proof-of-concept scenario becomes a regression test and fails safe: nothing fetched from private addresses, no open for unauthenticated senders, bounded time and memory, no suppression.
- [ ] Legitimate buff.ly → costco.com links still open, tested with a recorded redirect chain.
