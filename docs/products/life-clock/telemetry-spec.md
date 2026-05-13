# Telemetry Spec — Life Clock

> **Status:** Canonical product policy. Telemetry in Life Clock is **local-only, OSLog-based, with `privacy: .private` on every value.** No analytics SDK ships in v1. This spec defines what events exist, how they're redacted, and what post-TestFlight instrumentation will look like.
>
> Implementation: [`Sources/Services/OnboardingTelemetry.swift`](../../../products/life-clock-ios/Sources/Services/OnboardingTelemetry.swift) (protocol + `OSLogTelemetry` + `StubTelemetry` for tests) and [`Sources/Services/TelemetryRecorder.swift`](../../../products/life-clock-ios/Sources/Services/TelemetryRecorder.swift) (the aggregator stub).

## One-line rule

**Telemetry events fire locally via `Logger` (OSLog 2.0) with `privacy: .private` on every value field. No event leaves the device in v1. Post-TestFlight analytics will respect the same redaction contract by design.**

## What events fire today

| Event | Where | Payload (all `privacy: .private`) |
|---|---|---|
| `screenAppeared(screen:)` | Every onboarding screen mount | screen rawValue (`OnboardingScreen.rawValue` — see `onboarding-funnel.md`) |
| `screenAppeared("under13Block")` | DOB → under-13 routing | **No DOB / no age bucket** — presence-only event per `AGE_COMPLIANCE.md` |
| `screenAppeared("safetyNet")` | SafetyNet mount | **No affordance-choice telemetry** per [`safetynet-spec.md`](safetynet-spec.md) |
| `valueBucket(screen:, bucket:)` | Numeric onboarding inputs (cardio mins, sleep target, etc.) | screen + bucket label (e.g. "300-449m") — **never the raw user value** |
| `dialAdjusted(yearsBucket:)` | Healthspan dial commit | yearsBucket (e.g. "-1.5 to -0.5") — **never the user's specific anchor** |

The event names + bucket labels are stable identifiers consumed by future post-TestFlight aggregators. Renaming a key is a breaking change for the funnel; treat as such.

## Privacy contract (binding)

`OSLogTelemetry.record(...)` uses `Logger` from `os.log` (OSLog 2.0). Every interpolated value uses the `privacy: .private` qualifier:

```swift
logger.log(
    "screenAppeared screen=\(screen.rawValue, privacy: .public) \
     valueBucket=\(valueBucket, privacy: .private)"
)
```

- Event names + screen identifiers are `.public` (safe — they're enum strings, not user data).
- Every value, bucket, score, age, count, time, location, identifier is `.private`.
- `.private` values are redacted from sysdiagnose / Console.app outputs on production builds and visible only on the device in development.

`StubTelemetry` is the test-double — captures events in-memory for assertion in `OnboardingTelemetryTests`.

## Outstanding (post-TestFlight)

Real funnel analytics requires:

1. **An aggregator SDK pick.** Candidates: TelemetryDeck (privacy-friendly), PostHog (self-hosted option), Mixpanel. Decision pending vision-question.
2. **Privacy policy update.** Any SDK addition triggers a `legal/privacy-policy.md` rev + App Store privacy disclosure update (currently "Data Linked to You: None").
3. **Event-schema lock.** Once an SDK lands, every event becomes a stable schema entry. Renaming becomes a breaking change for the funnel.
4. **No retro-active capture.** Adding an SDK never captures events from prior local logs — those stay device-local.

Until those land, the metrics in [`ROADMAP_METRICS.md`](ROADMAP_METRICS.md) describe a *target* funnel computable post-instrumentation.

## What telemetry must NEVER do

- **Never capture HealthKit values.** Even bucketed. HealthKit data is contractually device-local (App Review § 5.1.3).
- **Never capture user names, emails, identifiers** beyond opaque-app-scoped install IDs.
- **Never capture content of `OnboardingDraft.birthDate` for under-13 users.** Specifically guarded — `under13Block` fires as presence-only.
- **Never capture SafetyNet affordance choices.** Presence-only.
- **Never fire on Pro-gate violations.** A Free user tapping a locked Plan Editor chip doesn't record "user wanted Pro feature X" — that's anti-pattern surveillance.

## Cross-references

- Onboarding funnel: [`onboarding-funnel.md`](onboarding-funnel.md)
- Privacy policy: [`PRIVACY_COMPLIANCE.md`](PRIVACY_COMPLIANCE.md), [`legal/privacy-policy.md`](legal/privacy-policy.md)
- Age-block telemetry guard: [`AGE_COMPLIANCE.md`](AGE_COMPLIANCE.md) § Item 2
- SafetyNet telemetry guard: [`safetynet-spec.md`](safetynet-spec.md) § Anti-patterns
- Target metrics: [`ROADMAP_METRICS.md`](ROADMAP_METRICS.md)
- Source: [`OnboardingTelemetry.swift`](../../../products/life-clock-ios/Sources/Services/OnboardingTelemetry.swift), [`TelemetryRecorder.swift`](../../../products/life-clock-ios/Sources/Services/TelemetryRecorder.swift)

## Validation

Telemetry is on-spec when ALL of the following hold:

1. Every interpolated value field uses `privacy: .private`.
2. Event names + screen identifiers are stable across releases.
3. No DOB / no HK value / no SafetyNet choice / no Pro-gate-violation event fires.
4. `StubTelemetry` covers every event for test assertion.
5. No analytics SDK is wired in v1 (`grep -rE 'import (Firebase|Mixpanel|Amplitude|TelemetryDeck|PostHog|Sentry)' Sources/` returns nothing).
6. Privacy policy + App Store disclosure stay at "Data Linked to You: None" until an SDK is added.
