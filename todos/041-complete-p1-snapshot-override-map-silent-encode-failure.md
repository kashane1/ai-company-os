---
status: complete
priority: p1
issue_id: "041"
tags: [code-review, life-clock, ios, data-integrity, overrides]
dependencies: []
---

# P1: SnapshotOverrideMap.encode() silently swallowed failures (data-loss bug)

## Problem Statement

`encode()` returned `Data()` on JSONEncoder failure. `decode(from:)` treats `Data()` as "empty map." So a single encode failure would silently wipe every override on the snapshot the next time `OverrideService.applyOverride` saved it back. JSONEncoder rarely fails on `[String: Double]`, but the silent-fallback path was a latent data-loss bug.

## Findings

Data-integrity review (PR #18, P0): "`SnapshotOverrideMap.encode()` swallows JSONEncoder failures... encoding a non-empty map can theoretically fall through to `Data()`. Since `decode(from:)` treats `Data()` as 'empty map,' a single encode failure silently wipes every override on the snapshot."

## Resolution Applied

- `encode()` is now `throws` and propagates the encoder error.
- `OverrideService.applyOverride` and `revertOverride` call `try overrides.encode()` / `try originals.encode()` BEFORE mutating any model state. On throw, both surface as `OverrideError.persistenceFailed` and the snapshot is never touched.
- `decode(from:)` now `assertionFailure`s in DEBUG when non-empty bytes fail to decode (so we hear about corruption immediately) while still returning empty map in release (no crash, fail-safe).

## Files

- `products/life-clock-ios/Sources/Models/SnapshotOverrideMap.swift`
- `products/life-clock-ios/Sources/Services/OverrideService.swift`
