# iOS Conventions

Lightweight code conventions for managed iOS products in `ai-company-os`.

This doc is for Codex and iOS worker execution consistency. It is not a comprehensive Swift style guide.

Product scope and architecture remain authoritative in product docs.
Code-style choices here apply to all managed iOS products unless a product doc overrides.

---

## Logging

Use `os.Logger`. Do not use `print` in production code paths.

```swift
import OSLog

private let logger = Logger(subsystem: "com.ai-company-os.catchbook", category: "LocationRecorder")

// state transitions → .debug
logger.debug("Location authorization changed: \(status.rawValue)")

// failures → .error
logger.error("Location capture failed: \(error.localizedDescription)")
```

- **subsystem**: reverse-DNS prefix for the product, e.g. `com.ai-company-os.<product-id>`
- **category**: the class or feature name
- Use `.debug` for state transitions and flow events
- Use `.error` for failures and unexpected conditions
- `print` is acceptable in tests and previews; not in production service or view code

---

## Typed errors

Services should surface typed domain errors, not raw strings or untyped `NSError`.
Conform to `LocalizedError` where the message will surface in UI or logs.

```swift
enum TripError: LocalizedError {
    case saveFailed(underlying: Error)
    case invalidState(String)

    var errorDescription: String? {
        switch self {
        case .saveFailed(let error): "Failed to save trip: \(error.localizedDescription)"
        case .invalidState(let reason): "Invalid trip state: \(reason)"
        }
    }
}
```

- One error enum per domain area is enough; do not over-split
- Services rethrow or wrap lower-level errors into domain errors at the boundary
- Plain `throws` without a typed enum is acceptable for small private helpers that don't cross service boundaries

---

## Async loading state

Use a `LoadingState<T>` enum as the standard pattern for async-backed view state.

```swift
enum LoadingState<T> {
    case idle
    case loading
    case loaded(T)
    case failed(AppError)
}
```

- `AppError` is the app-level error type (see typed errors section); use it here so UI layers receive a typed, displayable error
- `idle` is the initial state before any load has been requested
- View models hold `@Published var state: LoadingState<T> = .idle`
- Do not use raw `Bool` + optional value pairs as a substitute — they make error handling invisible

For a simple one-shot load, a minimal view model looks like:

```swift
@MainActor
final class TripListViewModel: ObservableObject {
    @Published var state: LoadingState<[Trip]> = .idle

    func load() async {
        state = .loading
        do {
            let trips = try await tripRepository.fetchAll()
            state = .loaded(trips)
        } catch let error as TripError {
            state = .failed(AppError.trip(error))
        } catch {
            state = .failed(AppError.unexpected(error))
        }
    }
}
```

---

## Protocol-first services

Expose a protocol for services and feature-level objects where a test double would materially improve test quality.

```swift
protocol PersonalBestProviding {
    func refresh(with catchRecord: CatchRecord, in context: ModelContext) throws
    func rebuild(in context: ModelContext) throws
}

final class PersonalBestService: PersonalBestProviding { ... }

// In tests:
final class FakePersonalBestService: PersonalBestProviding {
    var didRefresh = false
    func refresh(with catchRecord: CatchRecord, in context: ModelContext) throws { didRefresh = true }
    func rebuild(in context: ModelContext) throws {}
}
```

- Scope this to services and feature-layer objects that cross test boundaries
- Do not add protocol ceremony to small internal helpers, pure functions, or utilities that are easily tested directly
- The concrete class remains the default everywhere; the protocol is for injection points

---

## Alignment with repo conventions

- **Local-first** applies to data flow: service and model logic must not assume network availability
- **Deterministic insights**: no generative or non-reproducible output from service layer
- **Tests-with-code**: logic-bearing changes in `Sources/` require lane-matching tests in `Tests/`; these conventions inform what shape those tests take
- **Product scope**: product docs override general conventions for product-specific decisions
