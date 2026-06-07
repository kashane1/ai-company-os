---
status: complete
priority: p2
issue_id: "046"
tags: [code-review, life-clock, ios, layering, models]
dependencies: []
---

# P2: Models/SnapshotOverrideMap.swift imported UIKit (layering violation)

## Problem

`FieldSpec` had `keyboard: UIKeyboardType` which forced `import UIKit` in `Sources/Models/`. Models is supposed to be UI-framework-free for cross-target reuse and headless testability.

## Resolution

`Spec.keyboard: UIKeyboardType` → `Spec.acceptsDecimal: Bool` (a policy bit, not a UI type). `OverrideSheet` derives the UIKeyboardType from the bool in the UI layer:

```swift
var keyboardType: UIKeyboardType {
    spec.acceptsDecimal ? .decimalPad : .numberPad
}
```

Models is now UIKit-free.

## Files

- `products/life-clock-ios/Sources/Models/SnapshotOverrideMap.swift`
- `products/life-clock-ios/Sources/Features/History/OverrideSheet.swift`
