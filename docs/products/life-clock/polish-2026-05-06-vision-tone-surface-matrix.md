# Polish Session — life-clock — 2026-05-06 — vision-tone-surface-matrix

## Mode

Vision-driven. Operator idea: switch tone in Profile (now a Menu picker) and walk every surface where copy lives. Build a matrix of (surface × tone) showing whether copy actually shifts across gentle / coach / firmDirect OR is hardcoded. Polish hardcoded copy that's trivially fixable; queue Stretch / Vision-questions for surfaces where tone-aware copy doesn't exist at all.

- Iteration cap: 6
- Final computer-use checkpoint: yes (mandatory in vision mode)
- Tone source-of-truth: [ToneMode.swift](../../../products/life-clock-ios/Sources/App/ToneMode.swift)
- Simulator target: iPhone 16e (already booted)
- Scheme: `LifeClock` (regenerated `LifeClock.xcodeproj` via `xcodegen` at session start)

## Tone × Surface matrix

Statuses: **TONE-AWARE** = sources copy from `tone.<key>`; **HARDCODED** = literal string baked in; **SYSTEM** = formatted from data; **DERIVED** = pulled from a model/enum.

### Today (`Features/Today/TodayView.swift` + `ReflectionCard.swift` + `Shared/SupportMomentCard.swift` + `Shared/DisclaimerBanner.swift` + `Features/Today/PlanEditorSheet.swift`)

| Element | Source | Status | Notes |
|---|---|---|---|
| Nav title | TodayView.swift:68 | TONE-AWARE | `tone.todayHeadline` |
| Headline delta prefix | TodayView.swift:175,177 | TONE-AWARE | `tone.deltaPositivePrefix` / `deltaNegativePrefix`; literal `" today"` suffix is hardcoded but trivial |
| Loading placeholder | TodayView.swift:194 | HARDCODED | `"Loading…"` |
| Toolbar Check-in button | TodayView.swift:81 | HARDCODED | `"Check in"` |
| Mascot caption | TodayView.swift:235–267 | n/a | No caption; visual + a11y label only |
| clockCard "Projected healthspan" | TodayView.swift:276 | HARDCODED | brand label |
| clockCard reference-date prefix | TodayView.swift:282 | HARDCODED | `"Reference date: "` |
| rescueLine body | TodayView.swift:422 | TONE-AWARE | `tone.todayRescueBody()` |
| supportMomentCard title/detail | SupportMomentCard.swift:12,14 | DERIVED | from `SupportMoment` model — tone variation lives in `SupportMomentPresenter` |
| driversCard heading | TodayView.swift:296 | HARDCODED | `"Why it changed"` |
| driversCard empty-state | TodayView.swift:299 | HARDCODED | `"No health data yet. Connect Apple Health…"` |
| driversCard interpretation line | TodayView.swift:303,335-343 | TONE-AWARE | `tone.todayInterpretation*` |
| driversCard rows | TodayView.swift:309,311 | DERIVED+SYSTEM | driver titles/deltas |
| dietContextLine positive | TodayView.swift:398 | HARDCODED | `"Your meals supported today's progress."` |
| dietContextLine negative | TodayView.swift:400 | HARDCODED | `"A rough food day is feedback, not failure. One better meal can help tomorrow feel steadier."` |
| questsCard header | TodayView.swift:436 | HARDCODED | `"Today's Plan"` |
| questsCard sub-line | TodayView.swift:456 | HARDCODED | `"One small thing to notice or do."` |
| questsCard rows | TodayView.swift:467,468 | DERIVED | from `QuestEngine` |
| quickLogCard primary | TodayView.swift:150 | HARDCODED | `"Save today's check-in"` / `"Update today's check-in"` |
| quickLogCard sub-line | TodayView.swift:152 | HARDCODED | `"Fuel, extras, recovery, strength, nicotine. About 30 seconds."` |
| monthlyLoggingBanner primary | TodayView.swift:361,362 | HARDCODED | `"{N} day(s) logged so far · {month}"` |
| monthlyLoggingBanner secondary (neutral) | TodayView.swift:388 | TONE-AWARE | `tone.monthlyLoggingNeutralLine` |
| monthlyLoggingBanner secondary (milestone) | TodayView.swift:382 | TONE-AWARE | `tone.monthlyLoggingMilestoneLine(...)` |
| DisclaimerBanner | DisclaimerBanner.swift:8 | DERIVED | `LifeClockConfiguration.medicalDisclaimer` |
| ReflectionCard heading | ReflectionCard.swift:22 | TONE-AWARE | `tone.reflectionHeading` |
| ReflectionCard "Saved. Tap to edit." | ReflectionCard.swift:32 | HARDCODED | |
| ReflectionCard "Reflect" CTA | ReflectionCard.swift:42 | HARDCODED | |
| ReflectionSheet copy | ReflectionSheet.swift:33,48,99,112 | DERIVED+HARDCODED | prompt is derived, frame copy is literal |
| PlanEditorSheet intro | PlanEditorSheet.swift:19 | HARDCODED | `"One pick per category. Resets tomorrow."` |
| PlanEditorSheet reset / nav title / done | PlanEditorSheet.swift:31,39,43 | HARDCODED | `"Reset to defaults"`, `"Edit today's plan"`, `"Done"` |
| PlanEditorSheet empty-variants | PlanEditorSheet.swift:59 | HARDCODED | `"No options today — already covered."` |

### History (`Features/History/HistoryView.swift` + `DayDetailView.swift`)

| Element | Source | Status | Notes |
|---|---|---|---|
| Yesterday card heading | HistoryView.swift:59 | TONE-AWARE | `tone.yesterdayWrapUpHeading` |
| longAbsenceCard heading + body | HistoryView.swift:91,93 | TONE-AWARE | `tone.historyLongAbsenceHeading/Body` |
| Weekly empty state | HistoryView.swift:118 | TONE-AWARE | `tone.weeklyEmptyState` |
| Past-days header | HistoryView.swift:130,149 | HARDCODED | `"Past days"` |
| importStatusBanner | HistoryView.swift:185,192 | HARDCODED | progress + Cancel |
| Fogged paywall heading/body/CTA | HistoryView.swift:242,245,252 | HARDCODED | full hardcoded paywall block |
| Weekly paywallTeaser heading/body/CTA | HistoryView.swift:298,300,306 | HARDCODED | `"See what shaped this week"` etc. |
| Weekly netCard label | HistoryView.swift:322 | HARDCODED | `"Net this week"` |
| Weekly driversCard heading | HistoryView.swift:342 | HARDCODED | `"What shaped the week"` |
| Weekly leverCard heading + caption | HistoryView.swift:357,362 | HARDCODED | `"Next best lever"` + `"Small, repeatable wins compound. Don't try to fix everything."` |
| Day row date / summary | HistoryView.swift:391,399-402 | SYSTEM | dates + counts |
| DayDetailView no-data | DayDetailView.swift:40 | HARDCODED | `"No data persisted for this day yet."` |
| DayDetailView Reflection heading | DayDetailView.swift:75 | HARDCODED | `"Reflection"` (note: ReflectionCard heading IS tone-aware — divergence) |
| DayDetailView adjusted chip | DayDetailView.swift:139 | TONE-AWARE | `tone.adjustedChipLabel` (uniform across modes by design) |
| DayDetailView "From Health: " prefix | DayDetailView.swift:125 | HARDCODED | |

### Profile (`Features/Profile/ProfileView.swift`)

| Element | Source | Status | Notes |
|---|---|---|---|
| Tone description (Menu picker option detail) | ProfileView.swift:29 | TONE-AWARE | `tone.description` |
| All section headers | ProfileView.swift:15,34,94,100,132,156,177,221,324 | HARDCODED | `"Tone"`, `"Appearance"`, `"Daily reminder"`, `"Apple Health"`, `"Subscription"`, `"Privacy"`, `"About"`, `"Height & weight"`, `"Completion badges"` |
| Tone picker label | ProfileView.swift:16 | HARDCODED | `"Tone mode"` |
| Reminder footer (denied / default) | ProfileView.swift:412,414 | HARDCODED | long help blocks |
| HK rationale | ProfileView.swift:115 | DERIVED | `LifeClockConfiguration.healthKitRationale` |
| HK help line | ProfileView.swift:121 | HARDCODED | iOS Settings deep-link guidance |
| Pro / Upgrade / Restore CTAs | ProfileView.swift:138,141,149 | HARDCODED | |
| Safety-net entry footer | ProfileView.swift:173 | HARDCODED | `"Switch to Gentle tone, hide the clock, or get crisis-resource phone numbers…"` |
| Nav title | ProfileView.swift:193 | HARDCODED | `"Profile"` |

### SafetyNet (`Features/SafetyNet/SafetyNetView.swift`)

| Element | Source | Status | Notes |
|---|---|---|---|
| All copy (intro + 3 numbered sections + crisis rows) | SafetyNetView.swift:30-120 | HARDCODED | **By design** — single soft register, anti-shame, crisis-safe. Should NOT become tone-aware. |
| Closing line | SafetyNetView.swift:120 | DERIVED | `LifeClockConfiguration.safetyNetClosing` |

### WrapUpSheet (`Features/WrapUp/WrapUpSheet.swift`)

| Element | Source | Status | Notes |
|---|---|---|---|
| Heading (yesterday + weekly) | WrapUpSheet.swift:18,19 | TONE-AWARE | `tone.yesterdayWrapUpHeading`, `tone.weeklyWrapUpHeading` |
| Body (positive / negative / zero) | WrapUpSheet.swift:25,27,29 | TONE-AWARE | full tone coverage |
| Dismiss CTA | WrapUpSheet.swift:64 | TONE-AWARE | `tone.wrapUpDismissCTA` |

### QuickLogSheet (`Features/QuickLog/QuickLogSheet.swift`)

Section structure: 7 sections (Fuel / Rhythm / Whole food / Extras / Recovery / Strength / Nicotine) + intro + clear footer.

| Element | Source | Status | Notes |
|---|---|---|---|
| Intro headline + sub | QuickLogSheet.swift:47,49 | HARDCODED | `"A few quick signals help your Life Clock stay honest."` + `"No calorie counting. No judgment."` |
| Section labels + options | QuickLogSheet.swift:54-155 | HARDCODED | likely should stay neutral — they're option labels, not narration |
| Clear footer | QuickLogSheet.swift:167 | HARDCODED | `"Removes today's manual signals…"` |
| Cancel / Update CTA | QuickLogSheet.swift:179,186 | HARDCODED | `"Update Life Clock"` |

### OverrideSheet (`Features/History/OverrideSheet.swift`)

| Element | Source | Status | Notes |
|---|---|---|---|
| notEntitled error | OverrideSheet.swift:72 | TONE-AWARE | `tone.overrideNotEntitledMessage` |
| Other errors / Save / Cancel / nav title | OverrideSheet.swift:41,45,48,65,74,76,78 | HARDCODED | mostly utility |

### PaywallSheet (`Features/Paywall/PaywallSheet.swift`)

| Element | Source | Status | Notes |
|---|---|---|---|
| Header headline + body | PaywallSheet.swift:61,63 | HARDCODED | full paywall narration |
| Period labels | PaywallSheet.swift:111-114 | HARDCODED | `"Auto-renews yearly"` etc. |
| Continue / Restore / Close | PaywallSheet.swift:33,37,130 | HARDCODED | |
| Fineprint | PaywallSheet.swift:143 | HARDCODED | **legally bounded — leave alone** |

### Onboarding (legacy `OnboardingView.swift`, V2 `OnboardingCoordinator` + `Screens/*`)

| Surface | File | Status | Notes |
|---|---|---|---|
| Legacy 7-step | OnboardingView.swift | HARDCODED throughout | `mode.description` is the only tone-aware element (the tone picker step) |
| EntryView | OnboardingCoordinator.swift:275 | HARDCODED | `"Almost there…"` |
| ColdOpen / Welcome / MeetClock / ReactiveSlider | LeadInScreens.swift | HARDCODED | full hardcoded narration in V2 lead-in |
| Goal / DOB / Sex / BodyComp / Smoking / Alcohol / Strength / Cardio / Sleep / Diet / SensitiveConsent / FamilyMother / FamilyFather / Stress / Social / Tone / PriorAttempts / HealthKitAuth | DataCollectionScreens.swift | HARDCODED | Every screen — title + body + CTAs are literal. The Tone picker presents `mode.displayName` (derived) and tone descriptions (tone-aware via `tone.description`). |
| Analyzing / ArchetypeReveal / LifeGridRemaining / BigNumberPenalty / RecoveryPreview | RevealEscalatorScreens.swift | HARDCODED | full reveal escalator is hardcoded |
| EngineRevealAndDial | EngineRevealAndDialView.swift | HARDCODED | clock anchor flow |
| PaywallPrimary | PaywallPrimaryView.swift | HARDCODED | full hardcoded; legal fineprint must stay alone |

**Tone is locked to Coach during onboarding by construction** until the user reaches the ToneView pick step (DataCollectionScreens.swift:947), so most onboarding copy not having a tone variant is consistent with shipped behavior — but the BigNumberPenalty / RecoveryPreview reveal-escalator screens are dramatic by tone, and would benefit from being tone-aware once the user picks gentle (currently the `mementoMori`-style language is one-size-fits-all).

## Iterations

- [16:43] (n/a) — pre-flight: regenerated `LifeClock.xcodeproj` via `xcodegen`. Working tree clean. Vision read. Matrix built.
