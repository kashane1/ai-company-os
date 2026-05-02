# Life Clock — New Claude Instance Handoff

> Paste the section below ("Pasteable handoff prompt") into the first
> message of a fresh Claude Code chat to onboard the new instance with
> zero ramp time. The full reference further down is for humans.

---

## Pasteable handoff prompt

```
You're picking up the Life Clock iOS app — an iPhone-first Health & Fitness
healthspan habit-tracking app built on this repo. The wedge is "earn time
back with better daily habits." The app is in pre-TestFlight state.

CODE LIVES HERE
- Repo: /Users/simons/ai-company-os (main branch is current)
- Life Clock worktree: /Users/simons/ai-company-os-life-clock on feat/life-clock-mvp-skeleton
  (merged into main, kept as a worktree for ongoing work)
- After Plans is a separate product on /Users/simons/ai-company-os-after-plans
  — do NOT touch After Plans from this chat; that's a different parallel chat

EVERY BASH COMMAND must start with `cd /Users/simons/ai-company-os-life-clock &&`
because the shell cwd resets between calls. Skipping this lands edits on the
wrong worktree.

READ FIRST (in this order)
1. docs/products/life-clock/PHASE_STATUS.md         — single source of truth
2. docs/products/life-clock/MVP_VS_FOUNDER_PACK_AUDIT_2026-04-28.md  — what shipped vs spec
3. docs/products/life-clock/ASC_CHECKLIST.md        — App Store Connect setup walkthrough
4. docs/products/life-clock/legal/README.md         — privacy/ToS hosting plan
5. docs/products/life-clock/CODEX_BUILD_PROMPT.md   — original founder-pack build prompt
6. docs/plans/2026-04-28-001-feat-life-clock-live-healthkit-plan.md
7. docs/plans/2026-04-28-002-feat-life-clock-persistence-plan.md
8. docs/plans/2026-04-28-003-feat-life-clock-storekit-paywall-plan.md
9. CLAUDE.md (repo root) — platform conventions

HARD CI GREP GATES (must stay clean — verify before every commit)
- HKHealthStore() may only appear in LiveHealthKitService.swift
- Date(), Date.now, Calendar.current, TimeZone.current may only appear in
  EngineClock.swift (everything else takes an injected EngineClock)
- diagnose / prescribe / guarantee — zero hits in user-facing copy
- iCloud / cloudKitDatabase — only the explicit `cloudKitDatabase: .none`
  reference; HealthKit-derived data must NEVER iCloud-sync
- @Model mutations only inside a ModelContext (no transient @Model writes)

ENGINEERING INVARIANTS
- All engines (ClockEngine, QuestEngine, ConfidenceModel, DietStreakCalculator,
  AgeGate, HealthKitAggregator) are pure functions over EngineClock + injected
  state. Tests pin time via EngineClock.fixed(date)
- LifeClockStore is @MainActor @Observable. Mutations go through ModelContext
- LifeClockSchemaV1: VersionedSchema + LifeClockMigrationPlan exist for V1.
  Any @Model field edit needs a MigrationStage in V2
- iOS 17+ deployment target. SwiftUI + SwiftData + StoreKit 2 + HealthKit
- Brand-prone strings live in LifeClockConfiguration. Don't hardcode
  "Life Clock" elsewhere
- Founder pack rules: agency over fear, no calorie/macro tracking, no medical
  claims, no doom default. Tone-mode default is "coach"; the older
  mortality-forward third mode was removed in the 2026-04-30 UX pass

WHAT'S DONE
- Founder pack ingested into docs/products/life-clock/ (18 files)
- Six SwiftUI screens: Onboarding, Today, Time Ledger, Quests, Weekly Report,
  Profile + Quick Log sheet + Paywall sheet + Safety Net sheet
- Two tone modes (gentle/coach) wired through the current product
- Live HealthKit (HKStatisticsCollectionQuery + sleep HKSampleQuery, honest
  authorization model — never claims "Connected"/"Denied" since reads are
  silent)
- SwiftData persistence (cold-start state survival for profile, habits, ledger)
- StoreKit 2 paywall (annual $49.99 / monthly $7.99 / lifetime $129.99)
  + Products.storekit for local sim testing
- Diet quality elevated as first-class clock driver; DietStreakCalculator
  on Today; QuickLogSheet for coarse daily habits
- Age-gated UI for under-18 users (AgeGate.isAdult); 12+ App Store rating
- SafetyNetView (988 + Crisis Text Line + hide-the-clock toggle + switch
  to Gentle tone)
- PrivacyInfo.xcprivacy with CA92.1 + C617.1 reasons
- Tests: ClockEngineTests, QuestEngineTests, ConfidenceModel,
  HealthKitAggregator, DietStreakCalculator, AgeGate, LifeClockStore,
  SubscriptionStore (SKTestSession), LifeClockE2ETests (full daily loop +
  cold restart + reset)

WHAT'S PENDING — founder-side (cannot be done from code)
- Apple Developer Program enrollment ($99/yr) — see ASC_CHECKLIST Phase 0
- Fill the remaining placeholders in docs/products/life-clock/legal/
  (*.md) with the real publisher name, support email, and governing-law
  details; the app already points at the GitHub Pages URLs
- App Store Connect: app record, IAP products matching Products.storekit
  IDs (com.lifeclock.pro.{monthly,annual,lifetime}), age-rating
  questionnaire (answers in ASC_CHECKLIST Phase 4 → 12+)
- App icon (1024x1024 + standard sizes) into AppIcon.appiconset/
- Six App Store screenshots
- Sandbox tester credentials for App Review notes

WHAT'S PENDING — code (small, optional, not blocking submission)
- Trend-vs-prior-week in WeeklyReportView (TODO comment outlines impl;
  needs ≥2 weeks of TestFlight data to validate)
- Real-device HealthKit smoke test (simulator HK is limited)
- iPad visual layout audit (.readableColumn() handles full-bleed cards;
  the rest needs a booted iPad simulator)
- Localizable.xcstrings extraction (if/when shipping non-English)

PRINCIPLES FOR THE NEXT SLICE
- Read PHASE_STATUS first; it's the source of truth for what's resolved
- For new features, write a plan under docs/plans/ first
  (`/workflows:plan` skill works well)
- Run grep gates and full test suite before every commit
- Keep tone-aware copy when adding any new user-facing text
- Don't add calorie/macro/named-diet vocabulary anywhere — see the
  diet-alignment commit for the centerpiece reasoning

If you're unsure where to start, ask me: "What's the next slice?"
```

---

## Full reference (for humans)

This document has more depth than the pasteable prompt because the new
chat doesn't need it but a returning founder might. Skip this section
when copying to Claude.

### Repo layout (Life Clock-specific)

```
/Users/simons/ai-company-os-life-clock/                  # worktree root
├── docs/
│   ├── plans/2026-04-28-00{1,2,3}-feat-life-clock-*.md  # the three plans
│   └── products/life-clock/
│       ├── PHASE_STATUS.md                              # source of truth
│       ├── MVP_VS_FOUNDER_PACK_AUDIT_2026-04-28.md      # gap analysis
│       ├── ASC_CHECKLIST.md                             # ASC walkthrough
│       ├── CODEX_BUILD_PROMPT.md                        # original spec
│       ├── CLAUDE_HANDOFF.md                            # this file
│       ├── legal/
│       │   ├── privacy-policy.md
│       │   ├── terms-of-use.md
│       │   └── README.md                                # GH Pages setup
│       └── (15 other founder-pack files)
└── products/life-clock-ios/
    ├── Sources/
    │   ├── App/                # LifeClockApp, Store, Container, ToneMode, AppTab
    │   ├── Engines/            # ClockEngine, QuestEngine, ConfidenceModel,
    │   │                       # EngineClock, DietStreakCalculator, AgeGate
    │   ├── Models/             # LifeClockSchema (VersionedSchema + 7 @Model types)
    │   ├── Services/           # HealthKit (Live + Mock + Aggregator + Config),
    │   │                       # SubscriptionStore, PaywallProductID,
    │   │                       # LifeClockConfiguration, Products.storekit
    │   ├── Features/           # Onboarding, Today, TimeLedger, Quests,
    │   │                       # WeeklyReport, Profile, QuickLog, Paywall,
    │   │                       # SafetyNet
    │   └── Shared/             # DesignTokens (incl. .readableColumn()),
    │                           # ConfidenceBadge, DisclaimerBanner,
    │                           # TimeDeltaFormatter
    ├── Tests/                  # 9 test files; LifeClockE2ETests is the
    │                           # smoke test that walks the full loop
    ├── project.yml             # XcodeGen config
    ├── Info.plist              # NSHealthShareUsageDescription declared
    ├── PrivacyInfo.xcprivacy   # CA92.1 + C617.1 declared
    ├── LifeClock.entitlements  # HealthKit entitlement
    └── README.md
```

### Useful one-liners

```bash
# Confirm gates clean
cd /Users/simons/ai-company-os-life-clock && \
  grep -rn "HKHealthStore()" products/life-clock-ios/Sources/ | grep -v LiveHealthKitService.swift && \
  grep -rn "Date()\|Date\.now\|Calendar\.current\|TimeZone\.current" products/life-clock-ios/Sources/ | grep -v EngineClock.swift | grep -v "// " && \
  grep -rni "diagnose\|prescribe\|guarantee" products/life-clock-ios/Sources/Features/ products/life-clock-ios/Sources/Shared/ products/life-clock-ios/Sources/App/

# Generate Xcode project (regenerate after any project.yml change)
cd /Users/simons/ai-company-os-life-clock/products/life-clock-ios && xcodegen generate

# Run all unit tests
cd /Users/simons/ai-company-os-life-clock/products/life-clock-ios && \
  xcodebuild test -project LifeClock.xcodeproj -scheme LifeClock \
  -destination 'platform=iOS Simulator,name=iPhone 15'

# Run with mock HealthKit (default on simulator)
LIFECLOCK_USE_MOCK_HEALTH=1
```

### Key commits on main (most recent first)

- `22064ca` Merge feat/after-plans-context-refactor into main *(unrelated)*
- `d1a3e30` Merge feat/life-clock-mvp-skeleton (PR #14) into main ← Life Clock arrives
  - `bff518a` close remaining code-side gaps (PrivacyInfo, brand strings, iPad, tone-mode coverage, E2E test)
  - `6b4193b` founder decisions — name, age-gate, safety net
  - `f0aa3c4` diet logging streaks
  - `0f4e211` elevate diet quality as first-class clock lever
  - `de8d80c` StoreKit 2 paywall (Plan 3)
  - `91644f0` SwiftData persistence (Plan 2)
  - `00ec949` + `b527ebe` Live HealthKit (Plan 1) + review fixes
  - `c6ea3eb` original PR #14 review fixes (todos 020–024)
  - `328b4a8` initial skeleton + founder pack ingestion

### Open questions log

See `PHASE_STATUS.md` for the current resolved decisions, blockers, and
product gaps. The older founder-pack question list is still useful for
historical context, but `PHASE_STATUS.md` is now the operational source
of truth.
