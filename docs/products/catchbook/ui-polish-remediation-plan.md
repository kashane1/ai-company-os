# Catchbook UI Polish Remediation Plan

Date: 2026-04-10
Owner: iOS lane (Codex + iOS worker)
Source review: `state/artifacts/ios/catchbook-polish-review.md`
Authoritative product scope: `docs/products/catchbook/mvp-spec.md`, `docs/products/catchbook/ios-architecture.md`
Engineering conventions: `docs/ios-conventions.md`

## 1. Goals

Ship Catchbook to TestFlight and App Review without the WeatherKit-attribution or data-integrity risks surfaced in the 2026-04-10 polish review, and close every finding (2 blocking, 9 should-fix, 10 nice-to-have) before the iOS build is marked release-ready. No new product features; no Build-Next scope pulled forward beyond what is already shipping in the current binary.

**Timeline:** no explicit target date. M1 (blockers) is the only real pressure because it gates the next TestFlight build; M2/M3 proceed at steady pace with no date-driven compromises.

## 2. Non-Goals

- No feature work outside the 21 review findings.
- No refactor of logic layers (`HomeDashboardLogic`, `TripPresentationLogic`, `SpotRecallSummary`, `LogFeatureLogic`) except where a finding demands it.
- No minimum-OS backport. Plan assumes iOS 17 target, consistent with current entitlements and `TimelineView` / `ContentUnavailableView` usage already in the codebase.
- No CloudKit work, no new share-card entry points, no Spot DNA.
- No Home screen layout refactor beyond what a specific finding forces (see review-log D3 for the dropped `ScrollView → List` refactor).

## 3. Pre-flight spikes (before coding)

These are time-boxed investigations that de-risk the plan itself. Each is ~30 minutes.

- **PF-1. WeatherKit attribution API surface.** Confirm the exact `WeatherKit` APIs available on iOS 17 for (a) the legal attribution URL, (b) the list of data sources, and (c) the Apple-logo mark asset. The relevant type is `WeatherAttribution` returned on a `Weather` object. Output: a 3-line note in the PR description of M1.1 listing the API calls used, so future migrations can trace back.
- **PF-2. Locale decimal audit.** Grep for every call site that converts a user-entered string into a `Double`. Expected hits: `TripEditingLogic.catchDraft`, `TripEditingLogic.conditionDraft`, maybe `LogFeatureLogic`. Output: a short list pasted into the M2.8 PR so nothing is missed.
- **PF-3. `DesignTokens.swift` merge-conflict survey.** M2.5, M3.2, M3.10 and M3.6 all touch shared UI files. Decide whether to batch them into one PR or stagger them. Default: batch into a single `ui-polish/M2-M3-design-tokens` PR.
- **PF-4. Snapshot-test infrastructure verification.** Check whether `products/catchbook-ios/Tests/` already has a snapshot-testing harness (e.g. `swift-snapshot-testing`) wired up. If not, either add the dependency or fall back to preview-based visual review + one-shot screenshots committed under `docs/products/catchbook/screenshots/`. Output: one-line decision in this plan's §7 before M1.1 starts. This blocks every snapshot-test acceptance criterion in M1.1, M2.4, M2.5.

## 4. Milestones

### M1 — Release Blockers (must ship before next TestFlight build)

#### M1.1 WeatherKit attribution compliance (review B1)

- **Files:** `products/catchbook-ios/Sources/Features/Log/LogView.swift:288-304`, `products/catchbook-ios/Sources/Features/Trips/TripsView.swift:473-478`, `products/catchbook-ios/Sources/Services/WeatherKitService.swift`, new `products/catchbook-ios/Sources/Shared/UI/WeatherAttributionView.swift`.
- **PF-1 finding:** `WeatherAttribution` on iOS 17 exposes only `legalPageURL`, `combinedMarkLightURL`, `combinedMarkDarkURL`, `serviceName`, `squareMarkURL`. There is **no** `dataSources` array — the legal page itself is the data-sources destination. Apple's WeatherKit requirements are satisfied by a single `Link` to `legalPageURL` plus the combined mark asset. No separate data-sources sheet is needed.
- **Work:**
  1. Introduce `WeatherAttributionView` that renders `combinedMarkLight/DarkURL` via `AsyncImage` + " Weather" text as a `Link` to `legalPageURL`. Fall back to the `"\u{F8FF} Weather"` glyph if the mark asset fails to load.
  2. Render the view at `.footnote` minimum, `.secondary` foreground. Never `.quaternary`.
  3. Show it anywhere weather data is displayed — both the trip-start preview (`LogView`) and the trip detail conditions section (`TripsView`). Hide it when `weatherSummary == nil` (pure-offline trip) so it never dangles without data.
  4. Extend `WeatherKitService` to fetch and cache `try await WeatherService.shared.attribution` once per actor lifetime (it is a static URL set), exposing an actor-isolated `func attribution() async -> WeatherAttribution?` that returns nil on any error.
  5. Add `docs/products/catchbook/screenshots/weatherkit-attribution-light.png` and `...-dark.png` for App Review.
- **Acceptance:**
  - Tapping the "Weather" link opens Apple's legal page in Safari.
  - Tapping "Data sources" opens a sheet with at least one entry.
  - With weather data unavailable (airplane mode trip), neither control is visible.
  - Screenshots are committed to the repo.
- **Tests:**
  - `WeatherAttributionViewTests` — snapshot in light + dark mode.
  - Unit test confirming `WeatherKitService` exposes the attribution after a successful fetch.
- **Effort:** 0.5 day (after PF-1).
- **Risk & fallback:** If `WeatherAttribution` does not expose data sources on iOS 17 in the form documented, hardcode the known URL from Apple's WeatherKit docs and document the constant at the top of `WeatherAttributionView.swift` so a future iOS audit can revisit it.

#### M1.2 Lock down coordinate / temperature editing (review B2)

- **Files:** `products/catchbook-ios/Sources/Features/Trips/TripsView.swift:607-803`, `products/catchbook-ios/Sources/Features/Trips/TripEditingLogic.swift`.
- **Work:**
  1. **Verified 2026-04-10:** `coordinateSummary` is a computed property on `ConditionSnapshot` (`FishingModels.swift:168-171`). Clearing `latitude`/`longitude` automatically clears the rendered coordinate string — no separate stored-field handling needed.
  2. Remove the `latitude`, `longitude`, and `temperatureC` `TextField`s at `TripsView.swift:718-723`.
  3. Replace with a `LabeledContent` read-only row showing the existing `coordinateSummary` plus a single destructive `Button("Clear recorded location")` that nils `latitude`, `longitude`, and `temperatureC` (and `coordinateSummary` if stored) on the snapshot atomically inside the same `PersistenceWriteCoordinator.perform` call.
  4. Drop `latitude`, `longitude`, `temperatureC` from `TripEditingLogic.conditionDraft(...)`. The function becomes a text-only descriptive editor.
  5. Keep place/time-window/light/weather/wind/cloud/precipitation text editing (those are descriptive strings and are safe).
  6. Update `Tests/TripEditingLogicTests.swift` to reflect the new signature and add a test for the clear-location path.
  7. Fold the `LocationRecorder.swift:41` `print` → `os.Logger` cleanup (D2) into this PR since it touches the same feature area, per §10.
- **Acceptance:** it is impossible to silently mutate saved coordinates via the edit form; clearing the location sets all three fields to nil and persists; all other descriptive edits still work.
- **Tests:** unit tests for the trimmed `conditionDraft` signature and the `clearLocation` path; UI smoke via preview.
- **Effort:** 0.5 day.
- **Dependency:** none.

**M1 total: ~1 engineer-day. M1.1 and M1.2 are independent and may land in parallel.**

---

### M2 — Should-Fix Polish Pass (land before marking release-ready)

#### M2.1 Live-ticking trip elapsed time (review S1)

- **Files:** `HomeView.swift:290-346` (`ActiveTripHero`), `LogView.swift:696-744` (`ActiveTripStatusCard`), `HomeDashboardLogic.swift`.
- **Work:** wrap the elapsed label in `TimelineView(.periodic(from: trip.startAt, by: 60))` and derive the elapsed text inside the closure. Add a `relativeTo:` parameter to `HomeDashboardLogic.elapsedText(startAt:)` so tests can inject a fixed clock.
- **Acceptance:** on an active trip, the elapsed label advances at least once per minute with no user interaction.
- **Tests:** `HomeDashboardLogicTests` — elapsed text at t=0, t=59s, t=60s, t=3661s.
- **Effort:** 0.25 day.

#### M2.2 Keyboard dismissal for numeric and multi-line fields (review S2, expanded)

- **Files:** new `products/catchbook-ios/Sources/Shared/UI/KeyboardDoneToolbar.swift`, `LogView.swift` (`StartTripView` notes field + `ActiveTripView` quick-catch decimal fields — note: `LogView` has two distinct `List`/form surfaces, each needs its own toolbar), `TripsView.swift` (`TripEditorView` temperature/coordinate context + `CatchEditorView` weight/length).
- **Work:**
  1. Create a dismissal-closure helper to avoid the generic-`FocusState` compile friction across heterogeneous call sites:
     ```swift
     struct KeyboardDoneToolbar: ToolbarContent {
         let onDone: () -> Void
         var body: some ToolbarContent {
             ToolbarItemGroup(placement: .keyboard) {
                 Spacer()
                 Button("Done", action: onDone)
             }
         }
     }
     ```
     Each call site passes its own `{ focusedField = nil }` closure. This sidesteps having to make the helper generic over every view's `Field` enum and works identically whether the consumer uses `@FocusState` or not. If, during implementation, only one call site needs this, **inline the toolbar** at the call site instead of creating the shared helper (per adversarial review: the shared helper only pays off at 2+ consumers).
  2. Apply it to:
     - `LogView.StartTripView` — notes `TextField(axis: .vertical)`.
     - `LogView.ActiveTripView` — weight + length decimal fields (existing `@FocusState focusedField: QuickCatchField?` already wired at line 334).
     - `TripsView.TripEditorView` — for any remaining numeric fields after M1.2 lands (temperature is removed; confirm none of the descriptive fields still need it).
     - `TripsView.CatchEditorView` — weight + length decimal fields and notes.
  3. Also apply `.scrollDismissesKeyboard(.interactively)` to the top-level `List`/`Form` in all four views as a belt-and-braces dismissal path.
- **Acceptance:** every decimal keyboard and every multi-line notes field in the app has a visible Done control; swiping the list down also dismisses the keyboard.
- **Tests:** UI test driving the quick-catch weight field; snapshot of the keyboard toolbar.
- **Effort:** 0.5 day.

#### M2.3 Species Return actually saves (review S3)

- **Files:** `LogView.swift:402-405` + `saveCatch`.
- **Work:** add `.onSubmit { if !species.trimmed.isEmpty { saveCatch(action: .save) } }`. Empty return is a no-op.
- **Acceptance:** pressing Return on the species keyboard with non-empty text triggers a save; empty text does nothing.
- **Tests:** small unit test on the trimmed check plus a focused UI test.
- **Effort:** 0.1 day.

#### M2.4 Dynamic-type-safe stat cards (review S4, expanded)

- **Files:** `HomeView.swift:348-370` (`QuickStatCard`), `HomeView.swift:482-527` (`PersonalBestCard`), `TripsView.swift:1150-1167` (`TripStatPill`), `SpotsView.swift:341-354` (`SpotStatView`).
- **Work:**
  1. Replace fixed `width: 220` on `PersonalBestCard` with `frame(minWidth: 200, maxWidth: 280)` plus `@ScaledMetric` on the minimum width.
  2. Audit `QuickStatCard`, `TripStatPill`, `SpotStatView` for the same pattern — none of them currently force a width, but confirm their text wraps at Accessibility XL with `.fixedSize(horizontal: false, vertical: true)` on the inner `Text`.
  3. Snapshot each card at default, XL, and Accessibility XL type sizes.
- **Acceptance:** at Accessibility XL, no species headline or stat label clips or truncates in any of the four card styles.
- **Tests:** snapshot tests × 3 type sizes per card.
- **Effort:** 0.4 day.

#### M2.5 Brand-consistent color usage (review S5)

- **Files:** `HomeView.swift:262` (StartTripCTA icon), `HomeView.swift:488-492` (trophy icon), `TripsView.swift:1076-1080` (share-card gradient), `DesignTokens.swift`.
- **Work:**
  1. Replace `.teal.opacity(0.6)` with `.appAccent.opacity(0.55)`.
  2. Add a `appTrophy` token in `DesignTokens.swift` bound to `.appWarning` (already defined, #FF9F0A) and use it for the trophy icon + its circle background.
  3. Replace the share-card gradient with `LinearGradient(colors: [.catchbookSky.opacity(0.6), .catchbookAqua.opacity(0.2), Color(.systemBackground)], startPoint: .topLeading, endPoint: .bottomTrailing)` and verify the species title remains legible at 88pt bold rounded on both the photo and no-photo layouts.
- **Acceptance:** no raw `.teal` / `.orange` references remain in view code; share-card preview renders with brand palette in light and dark mode.
- **Tests:** snapshot of `CatchShareCardView` for both photo-present and photo-absent cases.
- **Effort:** 0.3 day.
- **Merge coordination:** batched with M3.2 and M3.10 per PF-3.

#### M2.6 SpotsView plus button accessibility (review S6)

- **Files:** `SpotsView.swift:40-46`.
- **Work:** replace `Image(systemName: "plus")` with `Label("Add spot", systemImage: "plus").labelStyle(.iconOnly)` **and** add `.accessibilityLabel("Add spot")` for defensive coverage.
- **Acceptance:** VoiceOver announces "Add spot, button" when focused.
- **Tests:** accessibility-label unit assertion.
- **Effort:** 0.05 day.

#### M2.7 "Last Time Here" scope reconciliation (review S7) — product decision + 1-line fix

- **Decision owner:** Kashane (founder). Default recommendation: **Option A** — update `mvp-spec.md` to move the "last time here" memory surface from Build Next into the "Added to MVP" section (dated 2026-04-10), matching the code that is already shipping.
- **Rationale:** The surface is deterministic, uses only personal data, and satisfies the recall goals of the MVP. Reverting would be user-hostile and does not reduce implementation risk.
- **Work (Option A, recommended):** a single edit to `docs/products/catchbook/mvp-spec.md` adding a line under "### Added to MVP (2026-04-09)" (or a new 2026-04-10 subsection). No code change.
- **Work (Option B, fallback):** gate `LastTimeHereCard` in `HomeView.swift:133-146` behind `FeatureFlags.lastTimeHereEnabled = false` and mark the flag as "off until Build-Next decision pass."
- **Acceptance:** `mvp-spec.md` and `HomeView.swift` agree on whether this surface exists.
- **Effort:** 0.1 day (decision + edit).

#### M2.8 Locale-aware decimal parsing (review S8)

- **Files:** `TripEditingLogic.swift` (catchDraft, conditionDraft), and any call sites turned up by PF-2, new `products/catchbook-ios/Sources/Shared/LocaleDecimalParser.swift`.
- **Work:**
  1. Introduce `LocaleDecimalParser.parse(_ text: String, locale: Locale = .current) -> Double?` backed by `NumberFormatter` with `.decimal` style and `isLenient = true`. Accept both `.` and `,` separators by pre-normalizing.
  2. Replace every `Double(userInputString)` call surfaced by PF-2 with `LocaleDecimalParser.parse(...)`.
  3. Unit-test the parser with `en_US`, `de_DE`, `fr_FR`, and malformed inputs.
- **Acceptance:** logging a catch weight of "1,25" in German locale persists `1.25` on the record; logging "1.25" in US locale also works; neither locale rejects the other's separator.
- **Tests:** `LocaleDecimalParserTests` covering the four cases above plus `TripEditingLogicTests` regressions.
- **Effort:** 0.4 day (includes PF-2).

#### M2.9 Home tab / nav title alignment (review S9)

- **Files:** `HomeView.swift:202`.
- **Work:** change `navigationTitle("Logbook")` to `navigationTitle("Home")`. Keep "Catchbook" as the app display name in `Info.plist` and "Logbook" as a verbal brand element in copy only.
- **Acceptance:** tab label and nav title both read "Home"; no QA doc still references "Logbook" as the navigation title.
- **Tests:** update `docs/products/catchbook/manual-qa-pass.md` in the same PR.
- **Effort:** 0.1 day.

**M2 total: ~2.2 engineer-days.**

---

### M3 — Nice-to-Have Quality

These are all scoped tight. M3 lands alongside M2 where the file surfaces already overlap (e.g. DesignTokens batch in M2.5). Any item that would expand scope is trimmed — see review-log D3.

- **M3.1 ActiveTripStatusCard spot HStack (N1).** Move the HStack at `LogView.swift:728-734` inside the `if let spot` binding so nothing is reserved when the trip has no spot. Effort: 0.05 day.
- **M3.2 SuggestionChip 44pt minimum (N2).** Add `.frame(minHeight: 44)` to `DesignTokens.swift:154-163`. Effort: 0.05 day. Batched with M2.5.
- **M3.3 Remove Photo button upgrade (N3).** Replace the caption-text button at `LogView.swift:455-460` with `Button("Remove Photo", role: .destructive) { ... }.buttonStyle(.bordered).controlSize(.small)`. Effort: 0.05 day.
- **M3.4 Catch delete confirmationDialog (N4).** Swap `.alert` at `TripsView.swift:934-941` for `.confirmationDialog("Delete this catch?", ...)`. Keep the same copy. Effort: 0.1 day.
- **M3.5 Locale-observant formatters (N5).** Swift has no "module init" hook, so promote `AppFormatters` from a bare `enum` of `static let` closures into an `NSObject` singleton (`AppFormatters.shared`) whose `init()` subscribes to `NSLocale.currentLocaleDidChangeNotification` and rebuilds its cached formatters under a serial queue. Touch `AppFormatters.shared` once from `CatchbookApp.init()` to guarantee first-access happens before any view body runs. Do not convert to computed properties (perf regression). Files: `Sources/Shared/Formatters.swift`, `Sources/App/CatchbookApp.swift`. Effort: 0.2 day.
- **M3.6 Unit-aware weather display (N6).** View-only change. Gate on nil explicitly — **do not** use `?? 0` because that renders a false "0°C" when the snapshot has no temperature. Pattern:
  ```swift
  if let celsius = snapshot.temperatureC {
      Text(MeasurementFormatter.temperature.string(
          from: Measurement(value: celsius, unit: UnitTemperature.celsius)))
  }
  ```
  The `MeasurementFormatter` sits on `AppFormatters` with `.naturalScale` + `.providedUnit` → respects the device's Measurement preference (°F vs °C) via the `.current` locale. Do NOT alter the SwiftData model or migrate existing records. Effort: 0.25 day.
- **M3.7 CatchShareCardView detail-row clipping (N7).** Add `.lineLimit(1).minimumScaleFactor(0.7)` to the detail rows at `TripsView.swift:1114-1121`. Effort: 0.05 day.
- **M3.8 ConditionPreviewRow rhythm (N8).** Merge the place/coordinate lines at `LogView.swift:266-306` into a single `Label` group, and reduce the stack from six sibling captions to four. Effort: 0.2 day.
- **M3.9 (dropped)** — see review-log D3. The review marked this as "consider"; the refactor is not worth the regression risk for a polish pass. Address post-launch if at all.
- **M3.10 Insight sample-count copy (N10).** Change the string at `DeterministicInsightCard.swift:46` from "Based on N logged samples" to a locale-aware "1 logged trip" / "N logged trips" using `AttributedString` + `inflect` or a simple singular/plural switch. Plumb a `sampleNoun` field on `DeterministicInsightCard`. Also touch `SpotRecallSummary.swift` if it generates sample-count copy consumed by the same card. Files: `Sources/Insights/DeterministicInsightCard.swift`, `Sources/Insights/SpotRecallSummary.swift` (verify). Effort: 0.35 day. Batched with M2.5.

**M3 total: ~1.1 engineer-days** (down from ~2 days after dropping M3.9).

---

## 5. Sequencing & dependencies

- PF-1 → M1.1. PF-2 → M2.8. PF-3 → anything touching `DesignTokens.swift` or shared UI. PF-4 → every snapshot-test acceptance criterion (M1.1, M2.4, M2.5, M3.1-M3.8 where snapshots apply).
- M1.1 and M1.2 are independent; land in parallel.
- **M2.8 must land after M1.2.** M1.2 removes the `temperatureC` `TextField`, which shrinks M2.8's parser scope. If M2.8 lands first, it wastes effort wiring locale parsing on a field that is about to be deleted.
- M2.7 is a 1-line product decision and blocks no engineering work. Apply Option A (spec update) by default.
- M2.5, M3.2, M3.10, and M3.6 all touch shared UI files — batch into one "design-tokens-polish" PR per PF-3 to avoid merge pain.
- M2.1 and M2.4 both touch `HomeView.swift` and its inner card structs. Land M2.1 first so M2.4 can rebase cleanly.
- M3.5 and M3.6 both touch `AppFormatters`. Land M3.5 first so M3.6's `MeasurementFormatter` can register on the same singleton.
- Everything else is independent.

## 6. Estimates

- M1: ~1 day.
- M2: ~2.2 days.
- M3: ~1.3 days (after M3.5 bump to 0.2 and M3.10 bump to 0.35).
- Pre-flight spikes: ~0.25 days (added PF-4).
- QA + snapshot pass + buffer: ~0.8 days.
- **End-to-end: ~5.55 engineer-days** for a single iOS worker with sequential merges.

## 7. Test strategy

- Unit tests for every logic change, in `products/catchbook-ios/Tests/` per `docs/ios-conventions.md`.
- Snapshot tests for every altered SwiftUI surface, captured in light and dark mode, at default / XL / Accessibility XL type sizes where dynamic type is a concern (M2.4). PF-4 determines whether "snapshot test" means `swift-snapshot-testing` or a manual screenshot-and-diff pass.
- `WeatherAttributionView` gets its own snapshot test (M1.1).
- Accessibility Inspector audit after M2 lands; fix any new findings before M3.
- Manual QA pass per `docs/products/catchbook/manual-qa-pass.md` on a physical device before the build is marked release-ready.

## 8. Rollout & approval gates

- No irreversible actions. Per `docs/engineering-flow.md`, no explicit approval gate is required.
- TestFlight build after M1 → internal smoke test.
- TestFlight build after M2 → founder review.
- App Store submission after M3 + manual QA signed off.
- Manual QA doc (`docs/products/catchbook/manual-qa-pass.md`) must be updated in the same PR as M2.9 (Home nav title rename).

## 9. Risks & mitigations

- **R1. WeatherKit API drift (M1.1).** iOS 17 and 18 differ in `WeatherAttribution` surface. Mitigation: PF-1 spike; documented fallback constants at the top of `WeatherAttributionView.swift`.
- **R2. Merge conflicts on shared UI files (M2.5 / M3.2 / M3.10 / M3.6).** Mitigation: batch into one PR per PF-3.
- **R3. Locale decimal regression (M2.8).** Mitigation: the parser accepts both separators in all locales and the test matrix covers en_US, de_DE, fr_FR. If any CSV-style internal caller breaks (e.g. `LogbookBackupExporter`), it is machine input not user input — keep it on `Double(_:)`. PF-2 lists the exact call sites.
- **R4. Dynamic type cascading breakage (M2.4).** Mitigation: snapshot test at Accessibility XL for each altered card.
- **R5. Scope creep on "Last Time Here" (M2.7).** Mitigation: default to Option A and do not pull further Build-Next surfaces forward in this lane.

## 10. Discovered but deferred

These were surfaced during planning but are out of scope for this remediation pass. Tracked here so they do not disappear.

- `LocationRecorder.swift:41` uses `print`, violating `docs/ios-conventions.md` (os.Logger required). Low-risk, one-line fix. Recommended to land in the same PR as M1.2 since it touches the same feature area. Not counted in M1 estimates.
- `HomeToolbarAction.exportLogbookBackup` is the only home toolbar action. If a second is ever added, the `.toolbar` closure at `HomeView.swift:203-211` will need to move to a `Menu`. No action now.
- The `AppFormatters.duration` elapsed-time path (M2.1) returns `nil` for zero-second spans — the current fallback string "Now" is fine but non-localized. Tracked but not addressed in M2.1 to keep the fix tight.

---

## Compound-Engineering Review Log

Applied the `document-review` skill from `docs/skills/document-review.md` to the first draft of this plan. Dispatched personas: coherence-reviewer, feasibility-reviewer, adversarial-document-reviewer, scope-guardian-reviewer, design-lens-reviewer, product-lens-reviewer, security-lens-reviewer. Findings below follow the P0/P1/P2 severity banding from the skill. Every finding rated ≥0.50 was merged into the plan above; the "Resolution" lines point at the section where the fix lives.

### P1 (high)

- **[feasibility] WeatherKit attribution API is not concretely pinned — conf 0.75**
  - Issue: first draft said "use `weather.availability` and similar" without confirming iOS 17 API surface. Blind coding against the wrong API name burns half a day.
  - Resolution: added **PF-1** pre-flight spike (§3) and renamed the concrete type to `WeatherAttribution` in M1.1 with an explicit fallback plan.

- **[scope-guardian + adversarial] Home `ScrollView → List` refactor (old M3.9) is over-scoped — conf 0.85**
  - Issue: the polish review only said "consider switching … to a List." First draft listed this as a full refactor task in M3. It would touch the entire Home hierarchy, risks regression on the horizontal `PersonalBests` scroll, and no finding required it.
  - Resolution: **dropped from scope**. Logged as "M3.9 (dropped)" in §4 and recorded here as D3 (see Dropped-scope section below).

- **[scope-guardian] Unit-aware weather (N6) was being planned as a model-level refactor — conf 0.70**
  - Issue: original scope touched `ConditionSnapshot` storage, services, and views — a feature-sized change hiding in a nice-to-have.
  - Resolution: M3.6 is scoped down to a view-only change using `MeasurementFormatter`. No model migration.

- **[design-lens] Dynamic type coverage was partial — conf 0.65**
  - Issue: draft only mentioned `PersonalBestCard` (`HomeView.swift:516`). The same risk exists on `QuickStatCard`, `TripStatPill`, and `SpotStatView`, which use fixed small fonts for stat values.
  - Resolution: M2.4 expanded to cover all four stat-card variants with snapshot tests at Accessibility XL.

- **[design-lens] Multi-line "axis: .vertical" notes fields also need keyboard dismissal — conf 0.60**
  - Issue: original M2.2 only targeted `.decimalPad`. The Notes `TextField(... axis: .vertical)` in `LogView` and `TripsView` has the same "no return key closes the keyboard" problem.
  - Resolution: M2.2 expanded to include multi-line fields and added `.scrollDismissesKeyboard(.interactively)` as a second-line dismissal path.

### P2 (medium)

- **[coherence] "if LogFeatureLogic parses numerics" was hedged — conf 0.55**
  - Issue: either it does or it doesn't; the plan should commit rather than hedge.
  - Resolution: added **PF-2** as a concrete audit step, so M2.8 starts from a known call-site list.

- **[feasibility] `AppFormatters` "computed property" suggestion would regress perf — conf 0.60**
  - Issue: first draft floated converting the static `DateFormatter`s to computed properties. `DateFormatter` allocation is non-trivial.
  - Resolution: M3.5 uses a one-time `NotificationCenter` observer on `Locale.currentLocaleDidChangeNotification` instead.

- **[adversarial] Merge-conflict risk across shared UI files — conf 0.60**
  - Issue: M2.5, M3.2, M3.6, M3.10 all touch `DesignTokens.swift` or adjacent shared UI.
  - Resolution: added **PF-3** and explicit batching guidance in §5 (Sequencing) and the per-task notes.

- **[product-lens] M2.7 "Last Time Here" was framed as engineering, not a product decision — conf 0.60**
  - Issue: the real work is a product-scope decision, not a code change.
  - Resolution: rewrote M2.7 with a recommended Option A (update `mvp-spec.md`), a fallback Option B (feature flag), and an explicit decision owner (Kashane).

- **[adversarial] Premise — do we actually need M3 for release? — conf 0.55**
  - Issue: M3 items are all review-classified nice-to-have. The plan could ship after M2 and address M3 post-launch.
  - Resolution: the user explicitly asked to address "all" findings including nice-to-have, so M3 stays in scope. Noted that any item could be deferred without risking release — captured in §8 (the M3 gate is decoupled from App Store submission in phrasing but not in practice; the user can call it).

- **[coherence] First draft estimated 6.5 days, but over-scoped items inflated M3 — conf 0.55**
  - Issue: original M3 estimate was 2 days; after dropping M3.9 and scoping M3.6 down, it should be closer to 1.1.
  - Resolution: §6 updated. End-to-end is now ~5.3 engineer-days.

### Below threshold (mentioned but not actioned)

- **[security-lens]** No new attack surfaces introduced. `coordinateSummary` remains visible in read-only form on the trip detail page; that is the user's own data, not an exposure.
- **[adversarial]** Alternative "just run `.scrollDismissesKeyboard(.interactively)`" was considered and folded into M2.2 as belt-and-braces, not a replacement.
- **[design-lens]** AI-slop check: the brand palette is already unique (ocean-to-navy blue), the share card gradient gets brought back into the palette in M2.5, no generic purple-blue-gradient issues.
- **[product-lens]** No orphan requirements introduced — every plan item maps 1:1 to a review finding.

### Dropped from scope (review-log D-series)

- **D1.** Model-layer refactor on weather units (originally part of N6). Replaced with view-only `MeasurementFormatter` usage in M3.6.
- **D2.** `LocationRecorder.swift:41` print-statement lint from `ios-conventions.md`. Not a polish-review finding. Recorded in §10 as a deferred cleanup rather than pulled into scope.
- **D3.** Home `ScrollView → List` refactor (originally M3.9). The polish review used the word "consider." A full hierarchy refactor is not justified by a nice-to-have finding. Post-launch candidate only.

### Confidence dedupe

- M3.9 over-scope flagged by **adversarial + scope-guardian** → confidence bumped to 0.85.
- M2.7 product-not-engineering flagged by **adversarial + scope-guardian + product-lens** → confidence bumped to 0.75.
- Dynamic-type partial coverage flagged by **design-lens** alone — base confidence 0.65, no bump.
