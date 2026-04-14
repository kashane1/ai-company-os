---
title: "Deleting a SwiftData @Model From a Child Sheet Leaves the Parent Detail View Holding a Dangling Reference"
category: integration-issues
date: 2026-04-14
tags:
  - catchbook
  - ios
  - swiftui
  - swiftdata
  - model-lifecycle
  - sheet
  - navigation-stack
  - detail-view
  - dismiss
  - toolbar
  - dangling-reference
module: Catchbook.Features.Spots
symptom: "When a SwiftUI detail view holds a SwiftData @Model directly (`let spot: Spot`) and presents an edit sheet that can delete the model, dismissing the sheet leaves the parent detail view rendering a now-deleted SwiftData object — a latent crash on any property access that re-runs through SwiftUI's body."
root_cause: "SwiftData @Model objects become invalid after `modelContext.delete(model); save()`. SwiftUI views that captured the model by reference don't get told it's gone — they keep rendering until the next state change, at which point reading any property may trip on a tombstoned object. The fix is to give the child form a deletion callback so the parent can dismiss itself before the next body re-evaluation."
---

## Problem

Catchbook's `SpotsView` lets users tap a spot to open `SpotDetailView`, which shows trips, catches, and recall stats for that spot. We added an Edit button that presents `NewSpotForm` in editing mode (sharing the same form code that creates new spots). The edit sheet also has a Delete Spot button that calls `modelContext.delete(spot)` and dismisses the sheet.

The naive wiring was:

```swift
struct SpotDetailView: View {
    let spot: Spot                              // direct @Model reference
    @State private var showingEditSheet = false

    var body: some View {
        List {
            // … reads spot.title, spot.notes, spot.coordinateSummary, etc.
        }
        .toolbar {
            ToolbarItem(placement: .topBarTrailing) {
                Button("Edit") { showingEditSheet = true }
            }
        }
        .sheet(isPresented: $showingEditSheet) {
            NewSpotForm(editingSpot: spot)      // form deletes spot internally
        }
    }
}
```

After the user taps Delete inside the form:

1. `NewSpotForm` calls `modelContext.delete(spot)` and `try modelContext.save()`.
2. `NewSpotForm` dismisses itself — sheet closes.
3. Control returns to `SpotDetailView`, which is still very much alive.
4. The detail view's body re-evaluates (because `showingEditSheet` flipped back to `false`) and tries to read `spot.title`, `spot.notes`, `spot.coordinateSummary`, the `@Query` joins on `spot.id`, etc.
5. The captured `Spot` is now a tombstoned SwiftData object — its properties may return defaults, throw, or read uninitialized memory depending on the SwiftData runtime's mood.

In the simulator this often "works" (default-zeroed strings, harmless visual glitch). On device under tighter memory pressure it crashes, or — worse — silently displays stale data because the user only sees the detail view for a fraction of a second before they swipe the sheet away.

There's a related problem: presenting the same `SpotDetailView` two different ways revealed that the toolbar Edit button only rendered in one of them. Tapping a row in the list pushed `SpotDetailView` inside the parent `NavigationStack`, so the toolbar appeared. Tapping a pin on the map presented `SpotDetailView` in a `.sheet` — and the sheet's content does NOT inherit the parent's `NavigationStack`. No nav bar, no toolbar, no Edit button.

## Root Cause

Two distinct SwiftData/SwiftUI lifecycle quirks intersect here:

### 1. Captured @Model references survive their model

A `@Model` class is a regular Swift reference type. SwiftUI's view structs capture it as a constant (`let spot: Spot`), and that reference outlives the model's "valid" state. SwiftData doesn't invalidate the Swift reference when you `delete()` — it marks the row for deletion in the context, the next `save()` removes it from the store, but the in-memory object stays around long enough for any code holding it to read it. The properties may return zeroed defaults, the relationship arrays may be empty, and accessing them is undefined behavior territory.

SwiftUI has no mechanism to notice the model is gone. There's no `@Model` equivalent of `@FetchRequest`'s pruning behavior for a single object passed by reference. If you want the view to react, you have to wire it up yourself.

### 2. Sheet content doesn't inherit the parent's NavigationStack

SwiftUI's `.sheet { … }` modifier creates a new presentation context. Anything inside that closure renders in its own window-like container with its own (empty) navigation environment. Toolbars defined on the sheet's content only render if there's a `NavigationStack` (or `NavigationView`) inside the sheet closure.

This is well-known when you build a sheet from scratch. It's easy to forget when you take an existing view that already has a `.toolbar { … }` modifier — designed to render inside a NavigationStack — and reuse it inside a sheet. The toolbar silently drops on the floor with no warning, no log message, nothing.

## Working Solution

### 1. Pass a deletion callback so the parent can dismiss itself first

Give `NewSpotForm` an `onDeleted` closure. Call it from the success path of the delete write, **before** the form's own `dismiss()`:

```swift
struct NewSpotForm: View {
    var editingSpot: Spot?
    var onSaved: ((Spot) -> Void)?
    var onDeleted: (() -> Void)?

    private func deleteEditingSpot() {
        guard let editingSpot else { return }
        PersistenceWriteCoordinator.perform(
            commit: {
                modelContext.delete(editingSpot)
                try modelContext.save()
            },
            rollback: { modelContext.rollback() },
            onSuccess: {
                onDeleted?()    // tell the parent first
                dismiss()       // then close the sheet
            },
            onFailure: { message in
                persistenceErrorMessage = message
            }
        )
    }
}
```

In the parent, capture the parent's own `@Environment(\.dismiss)` and pass it through:

```swift
struct SpotDetailView: View {
    @Environment(\.dismiss) private var dismiss
    let spot: Spot
    @State private var showingEditSheet = false

    var body: some View {
        List { /* … */ }
            .toolbar {
                ToolbarItem(placement: .topBarTrailing) {
                    Button("Edit") { showingEditSheet = true }
                }
            }
            .sheet(isPresented: $showingEditSheet) {
                NewSpotForm(
                    editingSpot: spot,
                    onDeleted: {
                        // Pop/close the detail view before its body re-runs
                        // and tries to read a now-deleted SwiftData object.
                        dismiss()
                    }
                )
            }
    }
}
```

`@Environment(\.dismiss)` is context-aware: in the pushed-from-list case it pops the navigation stack; in the presented-from-map-pin sheet case it dismisses the sheet. Both work without the parent needing to know how it was presented.

The crucial sequencing: `onDeleted?()` runs *before* `dismiss()`. SwiftUI processes the parent's dismissal as part of the same update cycle, so the parent never gets a chance to re-render its body against the dead model.

### 2. Wrap the sheet-presented detail view in a NavigationStack

For the map-pin path that presents `SpotDetailView` via `.sheet`, wrap the content so the toolbar has somewhere to render:

```swift
.sheet(item: $selectedSpotForDetail) { spot in
    NavigationStack {
        SpotDetailView(spot: spot)
    }
    .presentationDetents([.medium, .large])
}
```

The list-row path uses `NavigationLink { SpotDetailView(spot: spot) }` inside the existing `NavigationStack`, so it already had a stack. The sheet path didn't. One `NavigationStack` wrapper, and the toolbar Edit button works in both presentation contexts.

## Prevention

- **Default to a deletion callback whenever a child view can delete a `@Model` that the parent renders by reference.** It's two lines and removes a whole class of latent crashes. The opposite — having the parent observe the model's existence — is much more code.
- **Never assume `.sheet { Detail() }` inherits the surrounding navigation environment.** If `Detail()` declares `.toolbar` or `.navigationTitle`, wrap it in `NavigationStack` inside the sheet closure. This applies even when reusing an existing detail view that already worked fine when pushed.
- **Sequence callbacks before dismissals**: `onDeleted?(); dismiss()`, not `dismiss(); onDeleted?()`. SwiftUI batches updates per cycle, and you want the parent's dismissal queued in the same cycle as the child's, so the dead model is never read between them.
- **Treat `let model: SomeModel` in a SwiftUI view as borrowed-with-lifetime-tied-to-the-presenter**, the same way you'd treat a borrowed reference in any GC'd-object UI framework. The view does not own the model and cannot detect its destruction.

A related pattern worth knowing: when you reuse a "create" form as an "edit" form by adding an optional `editingSpot` parameter, branch the side-effect logic explicitly. In Catchbook's case, `NewSpotForm` runs waterbody auto-detection on the pin coordinate when creating a new spot. In edit mode we skip that pass entirely with `guard !isEditing else { return }` so the existing waterbody tag isn't clobbered by a re-detection. Mutating the existing record in place (`editingSpot.title = draft.title; editingSpot.notes = draft.notes; …`) preserves all `@Relationship` joins automatically — trips and catches stay linked without any extra work.

## Cross-References

- [SwiftData @Model Mandatory-Attribute Migration Landmine](swiftdata-mandatory-attribute-migration-landmine.md) — the other SwiftData-on-device gotcha that's bitten this codebase. Both are about how `@Model` lifecycle differs from what a SwiftUI-only mental model expects.
- Commit `b68cac7` — feat(catchbook): edit and delete spots from the Spots screen — the fix described here.
- Commit `c10b93a` — fix(catchbook): alphabetize spot picker in Start Trip sheet — landed in the same session, unrelated.
- [iOS App Runs in iPhone Compatibility Mode on iPad](ios-ipad-compatibility-mode-cramped-layout.md) — another "the simulator hides it, the device shows it" Catchbook bug from the same week.
