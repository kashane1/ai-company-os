# First implementation task cards

These tickets describe **proposed paths in the future standalone app repository**, not files already implemented in this workspace. Commands below are intended acceptance commands after project scaffolding; none is presented as a passing result today. Create a Swift package manifest for each named package with a corresponding test target, so `swift test --package-path …` is executable. Use original test fixtures only.

Work sequentially through dependencies; parallelize independent UI/domain tasks after contracts stabilize. For each logic ticket, first write its behavioral test, confirm the expected failure, implement minimally, run the narrow test and affected integration suite, and commit a coherent change. Keep purchase functionality out of this sprint.

## T00 — Establish source and scope charter

**Depends on:** founder direction. **Files:** `Docs/product-charter.md`, `Docs/adapters/source-review-template.md`, `Docs/adr/0001-mac-first.md`, `LICENSE`.

Record the initial customer/category, a specific proposed source's official access basis, permitted fields and rate limits, data/fixture redistribution rights, costs, source failure policy, and owner. Confirm proposed Apache-2.0 for original code/docs/fixtures; third-party material is separate. Record supported macOS minimum after checking Xcode/deployment needs. Reject sources without sufficient permission or usable data. If no live source works, label the project a synthetic/manual prototype rather than a restock product.

**Evidence:** dated primary-source links and a reviewed field/rate table. **Exit:** no named real retailer is enabled merely because it appeared in the reference app.

## T01 — Create isolated public project and fixture-only build

**Depends on:** T00 name/license decision. **Files:** `Apps/macOS/CollectorApp.xcodeproj`, `Apps/macOS/CollectorApp/CollectorApp.swift`, `Packages/*/Package.swift`, `.github/workflows/ci.yml`, `README.md`, `SECURITY.md`, `CONTRIBUTING.md`.

Create a fresh local project and explicitly public remote under the confirmed owner/name. Import only approved original specifications; never import this operations repo's Git history. Pin the toolchain and dependency versions. Define shared Xcode scheme `CollectorApp` and package test targets. Keep CI tests offline using fixtures.

**Verification:** `xcodebuild -list -project Apps/macOS/CollectorApp.xcodeproj` shows `CollectorApp`; `xcodebuild -project Apps/macOS/CollectorApp.xcodeproj -scheme CollectorApp -destination 'platform=macOS' build CODE_SIGNING_ALLOWED=NO` succeeds for the developer build. This is not a signed-distribution test.

## T02 — Define domain rules and unknown values

**Depends on:** T01. **Files:** `Packages/CollectorDomain/Sources/CollectorDomain/Watch.swift`, `Observation.swift`, `RuleEvaluator.swift`; `Packages/CollectorDomain/Tests/CollectorDomainTests/RuleEvaluatorTests.swift`.

Implement versioned exact-product/variant/seller/currency rules. Use integer monetary minor units; unknown stock, fee, identity, and price remain explicit. Test equal/under/over thresholds, wrong currency, wrong variant/seller, stale timestamp and missing fields. Ensure a simple item-price alert does not authorize spending.

**Verification:** `swift test --package-path Packages/CollectorDomain --filter RuleEvaluatorTests`. Expected: no match for missing or mismatched required evidence; deterministic match with an explanation for valid evidence.

## T03 — Persist watches and immutable observations

**Depends on:** T02. **Files:** `Packages/CollectorStore/Sources/CollectorStore/Database.swift`, `Migrations/001.sql`, `WatchRepository.swift`; `Packages/CollectorStore/Tests/CollectorStoreTests/StoreRecoveryTests.swift`.

Add foreign keys, schema versioning, transactional writes, revisions, durable run leases, semantic alert state and outbox. Write fault tests at transaction boundaries and reopen the database after interruption. Never assume copying only a live `.sqlite` file is a safe backup; use SQLite's backup mechanism or an appropriately coordinated snapshot. Export uses domain serialization.

**Verification:** `swift test --package-path Packages/CollectorStore --filter StoreRecoveryTests`. Expected: committed rules survive, partial transactions do not, and corrupt/unsupported schema errors are actionable without destructive auto-reset.

## T04 — Implement deterministic scheduling and pause semantics

**Depends on:** T02–T03. **Files:** `Packages/CollectorScheduler/Sources/CollectorScheduler/Scheduler.swift`, `Clock.swift`, `SourceBudget.swift`; `Packages/CollectorScheduler/Tests/CollectorSchedulerTests/SchedulerTests.swift`.

Inject clock, network availability and a fake adapter. Add bounded retry/backoff, one run lease per watch, source concurrency limits and wake staggering. Capture watch revision/source-policy generation before fetch and revalidate inside the commit transaction. Pause/edit invalidates in-flight alert eligibility.

**Verification:** `swift test --package-path Packages/CollectorScheduler --filter SchedulerTests`. Include pause-after-request/before-response, revision change, clock jump, expired lease, repeated failure, and wake with 100 overdue synthetic watches. No HTTP requests in these tests.

## T05 — Prevent repeated alerts and notification replay

**Depends on:** T03–T04. **Files:** `Packages/CollectorDomain/Sources/CollectorDomain/AlertEligibility.swift`, `Packages/CollectorScheduler/Sources/CollectorScheduler/NotificationDispatcher.swift`; tests `AlertEligibilityTests.swift` and `NotificationDispatcherTests.swift` in their corresponding packages.

Define semantic transition/re-arm/cooldown rules. A new observation ID alone does not justify another alert. Bind notification dedupe identifiers to a durable alert instance. Recheck current pause/consent before dispatch. A crash after delivery but before bookkeeping must not create another distinct notification.

**Verification:** run both package test suites. Required cases: 100 identical observations → one alert; false→true after explicit re-arm policy → another eligible alert; pause before dispatch → no delivery; duplicate event replay → no additional alert. Test OS-specific identifier behavior in the eventual integration test, not just a mock assumption.

## T06 — Build the watchlist and evidence inspector

**Depends on:** T02, T03; may run alongside T04–T05. **Files:** `Apps/macOS/CollectorApp/WatchlistView.swift`, `WatchEditor.swift`, `EvidenceInspector.swift`, `MonitoringStatusView.swift`; `Apps/macOS/CollectorAppUITests/WatchFlowTests.swift`.

Implement the original UI specification using synthetic content. Include empty/loading/never-checked/stale/offline/paused/unsupported states. A first-run sample must say Sample. Give browser handoff a fresh user-click requirement; do not store an open-page command in a replayable outbox. Record only a non-authoritative result after the OS open operation.

**Verification:** Xcode `CollectorApp` UI test scheme on macOS; manual keyboard and VoiceOver pass with the eight tasks in the UI specification. Wrong variant and unknown fees must remain visible at normal and enlarged text size.

## T07 — Export, privacy and redaction

**Depends on:** T03, T06. **Files:** `Packages/CollectorDiagnostics/Sources/CollectorDiagnostics/DiagnosticExport.swift`, `Redactor.swift`; `Packages/CollectorDiagnostics/Tests/CollectorDiagnosticsTests/ExportTests.swift`; `Apps/macOS/CollectorApp/DataSettingsView.swift`.

Separate user watchlist exports from diagnostics. User export may contain the user-selected product URLs; diagnostics omit URLs/product titles by default. Reject token-bearing URLs on input. Preview fields and require a chosen destination. Include key names and synthetic secret canaries in tests to verify headers/cookies/card-like fields cannot escape. Do not silently upload reports.

**Verification:** `swift test --package-path Packages/CollectorDiagnostics --filter ExportTests`; round-trip watchlist test in the store/domain suite; secret-canary export scan. No real account information in fixtures.

## T08 — Integrate one permitted real source

**Depends on:** T00, T02–T05; begins after synthetic slice passes. **Files:** `Docs/adapters/<approved-source>.md`, `Packages/CollectorAdapters/Sources/CollectorAdapters/<ApprovedSource>Adapter.swift`, source policy manifest and sanitized fixture/test files.

Replace placeholders only after a specific integration is chosen. Implement host/redirect validation, response size/deadline limits, source-specific stock semantics and timestamps. Stop on access denial or unsupported schema. Use a small consented manual pilot to compare responses to the live source; do not run CI against retail systems.

**Verification:** offline contract tests; bounded real-source observation report with timestamp, sample size, discrepancies, latency, rate-limit behavior and measured cost. This ticket is incomplete until real-source usefulness is demonstrated, even if all fixture tests pass.

## T09 — Release candidate and maintenance drill

**Depends on:** T01–T08 and pilot gates. **Files:** `Docs/releases/checklist.md`, `Docs/privacy.md`, `Docs/threat-model.md`, `Scripts/release.sh`, release CI, third-party notices and SBOM.

Complete the clean-machine install/update/export/uninstall checks, signing/notarization, supported-version policy, independent security review, source-disable drill and incident contact. Keep an unsupported-runtime block in release checks. Verify tampered update rejection for the actual chosen updater before automatic update is enabled.

**Verification:** signed artifact `codesign --verify --deep --strict`; Gatekeeper assessment; stapled notarization validation with the current Xcode tools; successful install/upgrade on supported macOS; full test suite; reproducible source-to-build instructions with any limitations stated. Exact release commands are written and tested during the signing spike rather than guessed now.

## Completion evidence template

Each ticket records: requirement IDs satisfied, changed files, tests run with exit status, manual evidence, source/permission assumptions, remaining risks, and next dependent ticket. A feature is not complete merely because its UI renders. The first public live-monitoring release requires both engineering checks and the founder-pilot/source gates.
