---
description: Run a repeatable simulator-driven UX audit on an iOS product, capture findings with evidence, and leave behind reusable docs and test hooks.
canonical_source: skills/canonical/products/life-clock/ios-simulator-ux-audit.md
---

# iOS Simulator UX Audit — Claude adapter

Follow the canonical procedure at `skills/canonical/products/life-clock/ios-simulator-ux-audit.md`. This adapter is Claude-specific runtime guidance — read it once, then drive off the canonical body.

## Before you start

Confirm these inputs from the operator (the canonical body lists them; surface them explicitly so you do not silently guess):

- product path under `products/<product-id>-ios/`
- Xcode scheme name
- target Simulator device + iOS version (default: pick the newest installed iPhone runtime via `xcrun simctl list devices available`)
- launch fixture (e.g. `LIFECLOCK_UI_TEST_SCENARIO=onboarded`) — see `LifeClockLaunchConfiguration.swift` for the env-var menu
- audit mode: `first-launch`, `returning-user`, or `both`

If the product has no onboarding, treat the "onboarding completed" checklist line as N/A and document why.

## Tools you should reach for first

- `xcrun simctl list devices available` to pick a deterministic device
- `xcodebuild -list -project <path>` to confirm the scheme exists before booting
- `xcrun simctl boot <udid>` / `install` / `launch` for the audit traversal
- The product's `LifeClockLaunchConfiguration` (or equivalent) for fixture-backed launch states

## Output collisions

If `docs/products/<product-id>/ux-audit-<YYYY-MM-DD>.md` already exists, append a timestamped H2 section to it rather than creating a sibling file. Same-day re-audits should accumulate, not branch.

## When to stop and ask

- Simulator boot failure → report device + iOS + scheme and ask the operator before retrying.
- Onboarding gated by Apple ID / iCloud / push permission → use a launch fixture or ask for one.
- Product has no XCUITest target → bootstrapping it is in scope; flag the cost first.

## Boundaries

The canonical body's `allowed_edit_boundaries` apply: `docs/`, `products/`, `skills/`. Do not touch `packages/policies/` or `state/`.
