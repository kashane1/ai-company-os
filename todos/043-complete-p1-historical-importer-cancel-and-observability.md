---
status: complete
priority: p1
issue_id: "043"
tags: [code-review, life-clock, ios, importer, concurrency]
dependencies: []
---

# P1: HistoricalImportCoordinator — cancel didn't propagate; status mutations didn't trigger UI

## Problem Statement

Two bugs in one object:

1. **Cancel did nothing**. `currentTask = Task { await task.value }` wrapped a `Task.detached`. Calling `cancel()` on the wrapper does NOT propagate to the inner detached task, and `Task.detached` doesn't inherit cancellation. So `Task.isCancelled` checks inside `run()` were always false; cancelling the import was silently ignored.

2. **`HistoryView.importStatusBanner` never re-rendered.** `status` mutations didn't trigger SwiftUI to re-evaluate because `HistoricalImportCoordinator` wasn't `@Observable`.

## Findings

Architecture review (PR #18, item 1): "Three intertwined issues: `Task.detached` doing zero work because `run()` is `@MainActor` (hops back immediately); `cancel()` doesn't propagate across `await task.value`; `status` mutated but coordinator not `@Observable` so banner doesn't re-render."

## Resolution Applied

- Coordinator marked `@Observable`. Non-published deps tagged `@ObservationIgnored`.
- Replaced `Task.detached` + outer wrapper with a single `Task { @MainActor [weak self] in await self?.run() }`. Cancel now propagates through `currentTask?.cancel()` because cooperative cancellation flows through the structured `Task`.
- Comment explains why we didn't keep `Task.detached` (would just hop back to main and break cancellation).

## Files

- `products/life-clock-ios/Sources/Services/HistoricalImportCoordinator.swift`
