---
status: pending
priority: p2
issue_id: "112"
tags: [open-tcg, alerts, founder-decision]
dependencies: []
---

# OpenTCG: get alerts to the founder's phone when away from the Mac

## Problem Statement

Alerts are Mac notifications only. When the founder is away from the Mac, every drop is missed. On 2026-09-26, ntfy pushes showed up inside the iPhone app but never as iPhone notifications, and the founder paused that setup.

## Proposed Solutions

1. **iMessage to self (free, no new app):** the Mac's Messages app sends a text to the founder's own number. It needs Messages signed in on the Mac, and the founder's approval to send messages on their behalf.
2. **Fix ntfy on iOS:** reinstall, and allow notifications at the first prompt.
3. **Pushover:** a $4.99 one-time purchase, with very reliable iOS delivery.
4. **Telegram bot:** free and reliable, but needs a Telegram account.

## Recommended Action

The founder picks a channel. Then add it as a second sender beside macOS, with its own dedupe, and send watched availability alerts only (not the digest).

## Acceptance Criteria

- [ ] A test alert reaches the founder's phone lock screen.
- [ ] Real alerts go to both channels, once each.
