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

- [16:43] pre-flight — regenerated `LifeClock.xcodeproj` via `xcodegen`. Working tree clean. Vision read. Tone × surface matrix built (above).
- [16:50] `4980d49` — `feat(life-clock): tone-aware Today drivers + plan headings` — Polish — Today. Adds 4 keys to `ToneMode`: `todayDriversHeading`, `todayDriversEmptyState`, `todayPlanHeading`, `todayPlanSubline`. Coach copy preserved verbatim; gentle softens, firmDirect sharpens. Wired up at `TodayView.swift:296,299,436,456`.
- [16:51] `e461b9e` — `feat(life-clock): tone-aware History weekly headings` — Polish — History. Adds 4 keys to `ToneMode`: `historyWeeklyNetLabel`, `historyWeeklyDriversHeading`, `historyNextLeverHeading`, `historyNextLeverCaption`. Wired up at `HistoryView.swift:322,342,357,362`.
- [17:02] `e310b3b` — `docs(life-clock): append vision Open Questions 9-13 from tone matrix` — Vision-questions queued for surfaces where tone-awareness needs an operator decision (reveal escalator, onboarding lead-in, QuickLogSheet narration, paywall voice, Day-detail/Reflection heading divergence).
- [17:14] `215e409` — `chore(life-clock): LIFECLOCK_SEED_TONE env-var + onboardingV2 seed flag` — Polish/test-infra. Two deterministic-launch knobs: `SIMCTL_CHILD_LIFECLOCK_SEED_TONE=gentle|coach|firm_direct` overrides the seeded `UserProfile.toneMode`; the onboarded scenario now also sets `onboardingV2CompletedAt`. Without this fix, fresh installs landed on the V2 cold-open (gate is `profiles.isEmpty`, but onboarding routing reads `onboardingV2CompletedAt`). Compounds across future polish runs.
- [17:16] verification — captured Today goldens for all three tones at `products/life-clock-ios/.polish/goldens/today_{gentle,coach,firm_direct}.png` (gitignored). Visual diff confirms three distinct headings, delta prefixes, drivers heading. New keys land correctly:
  - gentle → `"Today"` / `"Progress gained today"` / `"What helped today"`
  - coach (control) → `"Today's progress"` / `"Progress today"` / `"Why it changed"`
  - firmDirect → `"Today's reckoning"` / `"Banked today"` / `"What moved the needle"`

## Stretch decisions (operator review)

None this session — every commit is Polish-tier (drop-in tone variant or test-infra seed knob). No layout changes, no animation timing, no copy rewrites of substance.

## Asks

### Resolved this session

- Where do the bulk of tone-aware copy keys live, and which surfaces still ship a single hardcoded register? → matrix (above) → no commit, just documentation.
- Can a polish run flip tone deterministically without driving the Profile picker? → `LIFECLOCK_SEED_TONE` env-var → `215e409`.

### Outstanding (cycle-end batch)

These are the Vision-questions appended to vision.md (#9–#13, dated 2026-05-06):

1. **Reveal-escalator tone-awareness** (Q9, Feature-tier). The V2 reveal sequence (`AnalyzingView`, `ArchetypeRevealView`, `LifeGridRemainingView`, `BigNumberPenaltyView`, `RecoveryPreviewView`) is hardcoded in a single dramatic register — `"~{N} years on the table."`, `"This is what's still ahead."`. Tone is locked to Coach until the user reaches `ToneView`, so a user who'd self-identify as anxiety-prone never gets a softer reveal. Options: (a) keep the dramatic register on principle; (b) move `ToneView` earlier so the reveal can read `tone.*`; (c) infer a softer register when stress=Stretched + low connection on the consent screens. **Pick one before next polish pass touches onboarding copy.**
2. **Onboarding lead-in copy register** (Q10, Stretch). `WelcomeView` / `MeetYourClockView` / `ReactiveSliderView` in [LeadInScreens.swift](../../../products/life-clock-ios/Sources/Features/Onboarding/Screens/LeadInScreens.swift) are written in a single coach-default voice. Same constraint as Q9. Could be (a) accepted as the product's first-impression voice; (b) re-rendered after tone pick if the user goes back. Stretch-tier.
3. **QuickLogSheet narration** (Q11, Stretch). The intro pair `"A few quick signals…"` / `"No calorie counting. No judgment."` and the clear-footer in [QuickLogSheet.swift](../../../products/life-clock-ios/Sources/Features/QuickLog/QuickLogSheet.swift) are hardcoded. Section labels probably should stay neutral. Decision needed before adding 4–6 new tone keys here.
4. **Paywall voice** (Q12, Stretch + marketing-side review). PaywallSheet + PaywallPrimaryView headline + body share the same hardcoded value-prop copy. Should the paywall speak in the user's tone or stay in a single neutral marketing voice? App Store fineprint stays as-is regardless.
5. **DayDetailView vs ReflectionCard heading divergence** (Q13, Polish-tier — does NOT need an operator decision). `ReflectionCard` on Today uses `tone.reflectionHeading` (three variants); the Reflection section in `DayDetailView` uses a hardcoded `"Reflection"`. Cleanup target for next polish pass.

### Final computer-use checkpoint — DEFERRED

The vision-mode procedure mandates a computer-use acceptance pass before declaring done. `mcp__computer-use__request_access` was invoked three times during this session to drive Profile → flip tone → verify History; each call returned `request_access timed out after 300s`, suggesting the macOS approval dialog was unanswered. The headless simctl golden capture (above) is the substitute evidence for Today's three tones; History weekly cards use the identical `store.toneMode.*` wiring as the Today changes (same store, same tone routing) — no reason they wouldn't shift symmetrically — but a live three-tone visual verification of History was not performed.

**Operator action**: when next at the keyboard, run

```
SIMCTL_CHILD_LIFECLOCK_UI_TEST=1 \
SIMCTL_CHILD_LIFECLOCK_UI_TEST_SCENARIO=onboarded \
SIMCTL_CHILD_LIFECLOCK_SEED_TONE=firm_direct \
SIMCTL_CHILD_LIFECLOCK_HEALTH_AUTH=authorized \
  xcrun simctl launch <iPhone16e UDID> io.aicompanyos.products.lifeclock
```

…tap History, and confirm the weekly net / drivers / lever headings read in the firmDirect register. Repeat for `gentle`. If anything looks off, a follow-up polish session can adjust strings without rewiring.

## Regressions caught

- None. Only edited surfaces (Today drivers + plan, History weekly cards, ToneMode, LaunchConfiguration). Today coach screenshot matches prior coach behavior verbatim — no unintended diff.

## A11y identifiers added

- None this session. The driven elements (Profile tone picker, Today headings, History headings) already have `accessibilityIdentifier`s from earlier polish sessions.

## Vision updates

- **Open Questions appended** (5 entries): Q9 reveal-escalator tone-awareness, Q10 onboarding lead-in register, Q11 QuickLogSheet narration, Q12 paywall voice, Q13 DayDetail/Reflection divergence (non-vision Polish).
- **Decided constraints proposed**: none — every Q surfaced this session needs operator input first.

## Next pass

- Pick up Q13 (DayDetail Reflection heading) as a one-line Polish in any future life-clock session.
- After operator answers Q9 (the highest-impact Feature-tier gap), do a follow-up polish pass that either softens the reveal escalator or moves `ToneView` upstream and rewires the reveal in tone-aware copy.
- Capture History goldens and finalize the visual-regression set under `.polish/goldens/`.
- Once tone-aware coverage extends to onboarding, audit the polish at the **Tone-as-onboarding-step** moment — does the user see a meaningful preview of what each tone looks like before committing? Currently `ToneView` shows `mode.description` only; mocking up a per-tone hero line might be the right pre-pick moment.

---

## PR body (derived from session log — copy-paste into the PR description)

```
feat(life-clock): tone-aware Today + History headings + tone-seed env-var

Vision-driven polish session. Built the tone × surface matrix
(see docs/products/life-clock/polish-2026-05-06-vision-tone-surface-matrix.md)
and shipped four targeted polishes from the highest-leverage hardcoded
slots, plus a test-infra seed knob that compounds across future runs.

Commits:
- 4980d49 — feat(life-clock): tone-aware Today drivers + plan headings
  Adds todayDriversHeading, todayDriversEmptyState, todayPlanHeading,
  todayPlanSubline to ToneMode. Coach copy preserved verbatim;
  gentle softens, firmDirect sharpens.

- e461b9e — feat(life-clock): tone-aware History weekly headings
  Adds historyWeeklyNetLabel, historyWeeklyDriversHeading,
  historyNextLeverHeading, historyNextLeverCaption to ToneMode.

- e310b3b — docs(life-clock): append vision Open Questions 9-13
  Reveal-escalator, onboarding lead-in, QuickLogSheet, paywall, and
  DayDetail/Reflection divergence — all queued for operator pick.

- 215e409 — chore(life-clock): LIFECLOCK_SEED_TONE env-var
  Adds deterministic tone seeding for simulator audits, plus the
  missing onboardingV2CompletedAt seed flag.

Verification:
- Headless build green for iPhone 16e on every commit.
- Today goldens captured at all three tones via simctl with the new
  SEED_TONE knob; three distinct headings + delta prefixes + drivers
  headings render correctly. Goldens at .polish/goldens/today_*.png
  (gitignored).
- History weekly cards use identical store.toneMode.* wiring as the
  Today changes — same store, same routing. Live three-tone visual
  verification deferred to operator (mandatory computer-use access
  dialog timed out unanswered three times during this session).

Outstanding: Vision-questions Q9–Q12 are queued in vision.md; Q9
(reveal escalator tone-awareness) is the highest-impact Feature-tier
gap and should be picked next.
```

