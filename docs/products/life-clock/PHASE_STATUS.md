# Phase Status

- **Product:** Life Clock
- **Last updated:** 2026-04-28
- **Phase:** discovery → **pre-TestFlight** (skeleton complete, no real submission yet)
- **Owner:** founder (Kashane)
- **Source tree:** `products/life-clock-ios/` (worktree: `/Users/simons/ai-company-os-life-clock`)
- **Docs root:** `docs/products/life-clock/`
- **Branch:** `feat/life-clock-mvp-skeleton` (PR #14, six commits)

## Current state

Founder pack ingested and registered. iOS MVP skeleton scaffolded with deterministic engines, six SwiftUI screens, three live integrations (HealthKit, SwiftData, StoreKit 2), and unit tests for the load-bearing pieces.

### Done

- ✅ Founder pack normalized into platform conventions (18 files in `docs/products/life-clock/`).
- ✅ Xcode project scaffold (`project.yml` + `Info.plist` + `PrivacyInfo.xcprivacy` + `LifeClock.entitlements`).
- ✅ Deterministic engines: `ClockEngine`, `QuestEngine`, `ConfidenceModel`, `EngineClock` (Date/Calendar/TimeZone injected — CI grep gates enforce this).
- ✅ Six SwiftUI screens (Onboarding, Today, Time Ledger, Quests, Weekly Report, Profile) + Quick Log sheet + Paywall sheet.
- ✅ Three tone modes (gentle / coach / memento mori).
- ✅ Disclaimer banner on every primary screen; no medical-claim copy (grep-verified).
- ✅ **Live HealthKit:** `HKHealthStore` queries via `HKStatisticsCollectionQuery` + sleep `HKSampleQuery`, progressive authorization, honest auth model (read denials are silent — we never claim "Connected"/"Denied"), `LIFECLOCK_USE_MOCK_HEALTH=1` env override for dev.
- ✅ **SwiftData persistence:** `@Model` + `LifeClockSchemaV1: VersionedSchema` + `LifeClockMigrationPlan: SchemaMigrationPlan` (empty stages). `ModelContainer` with `cloudKitDatabase: .none`. Cold-start state survival: profile, today's habits, and ledger restore across launches.
- ✅ **StoreKit 2 paywall:** three products (annual / monthly / lifetime), `Transaction.updates` listener in `init`, `Transaction.currentEntitlements` as single source of truth (no UserDefaults cache), `Products.storekit` config for local sim testing, restore via `AppStore.sync()`. Weekly Report drivers/lever gated behind Pro; net delta stays free.
- ✅ Unit tests: `ClockEngineTests`, `QuestEngineTests`, `LifeClockStoreTests` (cold-restart restoration, upsert, reset), `HealthKitAggregatorTests`, `SubscriptionStoreTests` (purchase, restore, refund via `SKTestSession`).
- ✅ CI grep gates clean: no `HKHealthStore()` outside `LiveHealthKitService.swift`; no `Date()`/`.current` outside `EngineClock.swift`; no `diagnose`/`prescribe`/`guarantee` in user-facing copy; only `cloudKitDatabase: .none` references iCloud.
- ✅ Past learnings applied: `swiftdata-mandatory-attribute-migration-landmine` (property-level defaults), `ios-ipad-compatibility-mode-cramped-layout` (`TARGETED_DEVICE_FAMILY = "1,2"`).

### Roadmap Phase 1 (founder pack `ROADMAP_METRICS.md`)

| Feature | Status |
|---|---|
| Onboarding | ✅ |
| HealthKit core import | ✅ |
| Baseline survey | ✅ |
| Clock estimate | ✅ |
| Today screen | ✅ |
| Time ledger | ✅ |
| Quests | ✅ |
| Weekly report | ✅ |
| Paywall | ✅ |

**Phase 1 completion: 9/9.** Ready to graduate from skeleton to TestFlight pending the gates below.

### Not done — blocking TestFlight

- ⏳ **Brand-name resolution** (Open Question 1) — code identifier is `LifeClock`; no UI rename strategy. UI strings inline (not yet in `Localizable.strings`), so a future rename is a multi-file change.
- ⏳ **App Store Connect product setup** — three product IDs (`com.life-clock.pro.{monthly,annual,lifetime}`) must be created in ASC with the same Subscription Group config as `Products.storekit` before submission. Local config currently doesn't sync.
- ⏳ **Privacy Policy + Terms of Use URLs** — `PaywallSheet` links to placeholder `https://example.com/privacy`. Apple's standard EULA is fine for ToS; the privacy URL must be real.
- ⏳ **PrivacyInfo.xcprivacy** — currently empty arrays; will need declared `NSPrivacyAccessedAPITypes` reasons (file timestamp, UserDefaults, etc.) once SwiftData persistence is exercised on real devices. Apple started enforcing this 2024.
- ⏳ **App icon** — no icon set in `Assets.xcassets/AppIcon.appiconset/Contents.json` beyond a single placeholder. App Store Connect requires a 1024×1024 marketing icon.
- ⏳ **App Store metadata** — no submission copy, no screenshot strategy chosen from the six options in `APP_STORE_ASO.md`, no keyword set.

### Not done — out of scope for v1

Correctly deferred per founder pack:

- Background HealthKit observer queries (`enableBackgroundDelivery` + `HKObserverQuery`).
- Apple Watch companion, widgets, Lock Screen surfaces (Phase 2).
- AI coach, meal photos, weekly coach summary (Phase 3).
- Lab upload, BP/glucose, clinician review (Phase 4).
- Backend / sync (V1 engineering rule: no backend until retention proven).
- Trial flows, offer codes, promo offers.
- Analytics / crash reporting (premature pre-TestFlight).
- HealthKit *writes* (read-only v1; no `NSHealthUpdateUsageDescription`).

## Open questions (full list, with status)

Source: `OPEN_QUESTIONS.md`. Status reflects what implementation has already decided (where applicable).

### Brand
1. **Should the app lean into mortality with "Life Clock" or soften ("TimeBack" / "Long Game")?** — *Unresolved.* Working title `LifeClock` retained.
2. **Should the default UI show projected date, projected age, or healthspan score?** — *Implemented as projected age + healthspan score; date shown as anchor.* Founder ratification needed.
3. **Should "death clock mode" be opt-in?** — *Resolved by implementation.* Default tone is `coach`. `mementoMori` is opt-in. Aligns with the founder pack's "agency over fear" principle.

### Product
4. **How intense should negative feedback be?** — *Soft.* Negative deltas use muted orange, not alarming red. Recovery quest after heavy alcohol log replaces a punitive tone.
5. **Hide the clock, show only "time earned"?** — *Unresolved.* No toggle exists. The `gentle` tone mode comes closest.
6. **Minimum manual logging?** — *Implemented.* Five fields in `QuickLogSheet` (alcohol, smoking, diet, stress, strength) — feedback needed on whether this is too many.
7. **Diet as daily quality score, or photo meals?** — *Daily score (great/okay/rough).* Photo meals deferred.

### Model
8. **Which public actuarial research after MVP?** — *Unresolved.* Currently CDC FastStats only.
9. **One day vs weekly smoothing?** — *Implemented.* Daily delta is raw; weekly trend is summed dailies. No smoothing of "single bad day spikes" yet.
10. **Communicate uncertainty without feeling weak?** — *Implemented as `ConfidenceBadge`.* "Confidence: High/Medium/Low" — copy review needed.

### Compliance
11. **Clinician review before submission?** — *Unresolved, recommended.* Especially for the disclaimer copy and the "memento mori" tone strings.
12. **Age rating: 13+, 17+, or general wellness?** — *Unresolved.* Default tone is non-medical; mortality framing in optional tone might warrant 17+. **Ask App Review.**
13. **Self-harm adjacent language / anxious users?** — *Unresolved, high-priority.* No safety net copy implemented. Should at minimum surface a "feeling overwhelmed?" link to mental-health resources before any negative-delta tone-mode prompt.

### Monetization
14. **Pro at $39.99 or $59.99/year?** — *Implemented at $49.99* (midpoint per `MONETIZATION.md` recommendation). Easy to change in ASC.
15. **Lifetime at launch?** — *Yes, implemented at $129.99.* Founder can drop or change this in ASC without code changes.
16. **First paywall after initial reveal or after first weekly report?** — *Resolved as after first weekly report.* The "See full week" button on Weekly Report is the only paywall placement currently. Adding a post-reveal placement would require a one-line change.

### Technical
17. **V1 entirely local-first, no account?** — *Resolved.* No backend, no account, `cloudKitDatabase: .none`.
18. **Should derived data ever sync?** — *Resolved as no for v1.* iCloud sync is forbidden for HealthKit-derived data per App Review.
19. **HK data types on first launch vs later?** — *Implemented as one tier (`core`).* All six core types requested at the same time. Founder pack envisioned progressive prompts; this is acceptable for v1 because the core set is contiguous.

## Next steps (recommended order)

### 1. Founder decisions (no code work)

These unblock TestFlight and several of the gaps above:

- **Resolve brand name (Q1).** If staying with "Life Clock", just confirm. If switching, the rename is a Localizable.strings refactor (~1 hour).
- **Resolve age rating (Q12).** Apple's age rating is configured in App Store Connect — pick a default; can change later.
- **Decide on safety-net copy (Q13).** Even one screen ("Feeling overwhelmed? Talk to someone…") before any memento-mori tone prompt is enough for App Review. Otherwise the tone is a soft rejection risk.
- **Decide ToS / Privacy hosting.** Apple's standard EULA URL works for ToS. Privacy needs a real page or a hosted gist.

### 2. Pre-submission engineering (small)

- **Replace `https://example.com/privacy`** in `PaywallSheet.swift` with a real URL.
- **Author app icon** (1024×1024 + the standard sizes) into `AppIcon.appiconset/`. Could lean on the existing `infra/scripts/generate_afterplans_icon_options.py` pattern from After Plans.
- **Wire ASC products** matching the IDs in `Products.storekit`. Same Subscription Group, same prices, then flip the `.storekit` config from local to "Synced (App Store Connect)" before submission.
- **Update `PrivacyInfo.xcprivacy`** with declared API reasons (CA92.1 for SwiftData's UserDefaults touch, C617.1 for filesystem timestamp). Apple started enforcing 2024.
- **Move UI strings to `Localizable.strings`** so brand-name change is one file. ~1 hour.
- **Add a single integration test** that constructs `LifeClockApp` end-to-end with `LIFECLOCK_USE_MOCK_HEALTH=1` and the in-memory model container, completes onboarding, and verifies the Today → Quick Log → Weekly Report flow renders without crashes.

### 3. TestFlight beta (founder pack `GTM_LAUNCH_PLAN.md` Days 46–65)

After steps 1 + 2:

- Submit to TestFlight with a sandbox tester for App Review.
- Recruit 50–100 self-improvement / quantified-self users.
- Measure activation: onboarding completion, HealthKit grant rate, first quest completion.
- Measure emotional safety: support requests mentioning anxiety, app deletion within 24h of first reveal, tone-mode distribution.

### 4. Post-TestFlight (depends on data)

- **Trend vs prior week** in Weekly Report — needs ≥2 weeks of persisted data to be meaningful.
- **Tone-mode-aware copy** on Time Ledger, Quests, Profile (currently only Today varies).
- **Progressive HK auth** if beta users complain the all-at-once prompt is too much.
- **Habit streaks**, **manual quick-log adoption analysis**.
- **Founder pack Roadmap Phase 2** (widgets, Lock Screen, Apple Watch) — only after retention is shown.

## Gaps still open (not next-step priority but worth tracking)

- **No "trend vs prior week"** in Weekly Report — `ROADMAP_METRICS.md` calls it out and the founder pack PRD includes it. Implementation needs a `previousWeekStart` fetch and a delta line; ~30 min of work *after* there's a real prior week of data.
- **Tone-mode coverage is partial.** Only Today screen varies copy by tone. Time Ledger, Quests, Weekly Report, Profile use neutral copy. Cosmetic, not blocking, but a tone-mode change should *feel* total.
- **HabitLog deletion path missing.** User can `setTodayHabits(...)` but cannot clear them. Edge case but pollutes the engine result if a user mis-taps.
- **No analytics taxonomy.** When TestFlight starts, founder needs to know which metrics from `ROADMAP_METRICS.md` to collect and which SDK to wire (founder pack defers analytics — needs a decision pre-beta).
- **No bug-reporting / crash-reporting hook.** Same as above. Sentry / Firebase Crashlytics / TelemetryDeck are the usual choices.
- **iPad layout untested.** `TARGETED_DEVICE_FAMILY = "1,2"` is set, but no SwiftUI adaptive sizing audit has been done. Forms render natively; cards may look thin in landscape.
- **No "skip onboarding for testers" path.** Useful for App Review and TestFlight beta — not blocking but pleasant.
- **`completeOnboarding` doesn't verify `disclaimerAcceptedAt`.** The UI gates the "Continue" button on the disclaimer toggle, but the store mutation trusts the caller. A second client (App Intents, Shortcuts) could bypass. Low risk; worth a one-line guard.
- **No background refresh.** App must be foregrounded for `refreshFromHealthKit()` to fire. Listed under "out of scope" intentionally; surface to the user via the founder pack's Roadmap Phase 2.

## Pre-submission checklist (running)

Hand to ASC / App Review when ready:

- [ ] Q1 brand decided
- [ ] Q12 age rating decided
- [ ] Q13 safety-net copy authored
- [ ] Real privacy URL hosted
- [ ] App icon set (all sizes)
- [ ] ASC products configured matching `Products.storekit` IDs
- [ ] `PrivacyInfo.xcprivacy` API reasons declared
- [ ] `Localizable.strings` extracted (enables rename later)
- [ ] Sandbox tester credentials prepared for review notes
- [ ] Subtitle chosen from `APP_STORE_ASO.md` shortlist
- [ ] Six App Store screenshots produced
- [ ] Keyword set chosen
