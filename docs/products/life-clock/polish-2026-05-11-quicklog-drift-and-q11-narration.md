# Polish Session — life-clock — 2026-05-11 — quicklog-drift-and-q11-narration

## Mode

`freeform-polish`. Tier: **drift + vision-question #11**.

Observer lenses:
- **(a) Q11 per-string classification** — for every visible string in `QuickLogSheet.swift`, decide whether it should be tone-keyed, stay neutral, or be escalated as a sub-question.
- **(b) Q3 friction read** — note any picker / section that feels like friction without earned signal. Q3 is a vision-tier question; I do not propose changes here, only observations.
- **(c) Lighting / a11y carryover** — confirm the sheet is internally consistent on header traits, a11y identifiers, picker accessibility values (the May 9 Profile sweep + May 11 SafetyNet sweep both seeded patterns the rest of the app is now expected to honor).
- **(d) Pro/Free divergence** — brief lists `LIFECLOCK_SIMULATOR_PRO_DISABLED={0,1}` as a knob; confirm whether it materially affects this surface.

**Operator brief — corrections up front.**

1. The brief states `git log --since=2026-04-26 -- products/life-clock-ios/Sources/Features/QuickLog/ returns zero commits`. It returns **one**: `c2b098e7` (2026-05-02, "feat: diet rhythm + whole-food anchor + life-impact framing + tone copy pass") — the commit that added Rhythm + Whole-food sections and the existing `"No calories, no judgment. Just rhythm."` caption. That was a feature + copy pass, not a polish-log drift audit. The brief's underlying point still holds: **there is no QuickLog-specific polish-log session** in the 14-day window (no `polish-*-quicklog*.md` or `polish-*-daily-checkin*.md` exists). The 2026-05-06 vision-tone-surface-matrix entry catalogued QuickLog's strings as HARDCODED but did not decide which to tone-key — Q11 is that decision.

2. **`LIFECLOCK_SIMULATOR_PRO_DISABLED={0,1}` is irrelevant to QuickLogSheet.** Grepped the file: zero `isProEntitled` / `isPro` / `paywall` references. The only branching in this sheet is `store.isAdultUser` (gates Rhythm + Nicotine sections at lines 67 and 143). So the "Pro and Free" leg of the matrix collapses to a no-op; the meaningful divergence is **adult vs. under-18**. Documenting here so the next operator doesn't burn iterations seeding `PRO_DISABLED` expecting copy to shift.

3. **The 3-tone visual walk is uninformative *pre-keying*.** Every string in the file is currently a literal — gentle, coach, and firmDirect render byte-identical pixels. Capturing 3-tone × 2-scheme × XXL screenshots before the decision matrix decides which strings *should* shift is theater. The right sequence is: (i) decide which strings move; (ii) implement; (iii) then capture the 3-tone walk to verify the keys actually render distinct copy. This session ships (i). The simctl recipe is queued for the follow-up implementation pass; success criteria here is the decision matrix + asks (per brief).

Iteration cap (per operator addendum): **8**. Final computer-use checkpoint (per operator addendum): **yes — three-tone QuickLog screenshot grid + XXL pass**. Iterations used: **7** (1 recon, 1 vision-Q11 read, 1 ToneMode key-budget read, 1 decision-matrix write, 1 fixture-knob ship, 1 build, 1 screenshot grid).

**Computer-use checkpoint reframe.** The decision-matrix write (original session) closed with "3-tone walk pre-keying is uninformative theater — capturing pre-keying byte-identical pixels has no Q11 value." The operator addendum re-opened the checkpoint, which forced me to think about what *else* the capture proves:

- **Baseline visual record** — QuickLog has zero prior polish-log screenshots. Even if the 3 tones render byte-identical pre-keying, the grid is the "before" reference the implementation PR will diff against. That's the value.
- **Empirically verify the friction observations** — the original log called out "Rhythm picker likely truncates at XXL." The screenshot capture upgrades that from speculation to **fact at *default* size** (`"Skipped, then over"` → `"Skipped…"` at the baseline content_size, not just XXL — see Ask 5 update below).
- **Confirm the byte-identicality claim** — `gentle-dark.png` and `firm_direct-dark.png` are visually identical (236KB ± 1KB; status-bar clock variance only). The "pre-keying theater" claim is now itself verified, not just asserted.

So the checkpoint paid for itself, but not for the reason the original framing implied. Documenting here so the next operator who reads "checkpoint: yes" on a pre-keying surface understands the value comes from the baseline + the friction-verify, not from observing tone variance that doesn't exist yet.

## Iterations

| Time | Commit-like | Type | Tier | Surface | Result |
|---|---|---|---|---|---|
| 07:18 | (recon) | — | — | QuickLogSheet | Static read of 52 visible strings; classified into Q11 buckets |
| 07:19 | (recon) | — | — | vision.md Q11 + Q3 | Re-read both, mapped per-string candidates against Q11's ≥14-key threshold |
| 07:20 | (recon) | — | — | ToneMode.swift | Read existing tone keys (~30) to anchor voice for the pool drafts |
| 07:22 | (write) | docs | Drift+Q11 | polish-2026-05-11-quicklog-drift-and-q11-narration.md | Per-string decision matrix + 5 operator asks + 4 tone-pool drafts shipped |
| 07:25 | (knob) | feat | Polish | [LifeClockLaunchConfiguration.swift](../../../products/life-clock-ios/Sources/App/LifeClockLaunchConfiguration.swift), [TodayView.swift](../../../products/life-clock-ios/Sources/Features/Today/TodayView.swift) | Added `LIFECLOCK_FORCE_QUICK_LOG=1` (DEBUG-only, mirrors `forceSafetyNet`); 12 LOC across 2 files |
| 07:26 | (build) | — | — | LifeClock | `xcodegen generate` + `xcodebuild ... build` → `** BUILD SUCCEEDED **` |
| 07:32 | (capture) | — | — | QuickLog | 3-tone × 2-scheme grid + XXL captured into `screenshots/2026-05-11-quicklog/` |
| 11:33 | (apply) | feat | Q11 | [ToneMode.swift](../../../products/life-clock-ios/Sources/App/ToneMode.swift), [QuickLogSheet.swift](../../../products/life-clock-ios/Sources/Features/QuickLog/QuickLogSheet.swift) | Operator approved all 5 asks. Added `quickLog{IntroHeadline,IntroSubheadline,RhythmCaption,ClearFooter}` properties + `quickLogSaveCTA(hasExistingHabits:)` function (4 keys + 1 state-branched function, 15 pool entries). Wired 5 call sites. Switched Rhythm picker to `.menu`. Added the neutrality-lock doc-comment enumerating section labels / 7 question prompts / picker options / destructive label / nav title / Cancel |
| 11:40 | (test) | test | Q11 | [ToneModeTests.swift](../../../products/life-clock-ios/Tests/ToneModeTests.swift) | 5 new test cases: 1 literal pin (gentle headline) + 4 property assertions (no-calorie anchor × 2, Health reference, state-branch distinctness). `xcodebuild test` → 20/20 green in 0.24s |
| 11:44 | (capture) | — | — | QuickLog | Post-keying grid captured → caught menu picker duplicating its prompt inline (subheadline + picker-label-as-row-title) |
| 11:45 | (fix) | fix | Polish | [QuickLogSheet.swift](../../../products/life-clock-ios/Sources/Features/QuickLog/QuickLogSheet.swift) | Added `.labelsHidden()` to the Rhythm menu picker; preserves the existing section visual cadence (standalone subheadline `Text` carries the question) while keeping the menu's accessibility label for VoiceOver |
| 11:46 | (capture) | — | — | QuickLog | Re-captured post-keying grid + XXL into `screenshots/2026-05-11-quicklog/post-keying/`. All 3 tones diverge visually; Rhythm picker clean |

## Recon — the strings in scope

Walked [QuickLogSheet.swift](../../../products/life-clock-ios/Sources/Features/QuickLog/QuickLogSheet.swift) top-to-bottom and bucketed every user-visible literal.

Total visible strings: **52**.

Buckets:
- Intro pair: 2 (Q11 named).
- Section labels: 7 (Q11 names; "probably should stay neutral").
- Question prompts: 7 (one per section, repeated as `Text` caption + `Picker` accessibility title — Q11 silent).
- Picker option labels: 23 across all sections (3+5+4+4+3+2+2).
- Section-level captions: 2 (Rhythm + Extras — Q11 silent).
- Clear footer block: 2 strings (destructive button label + footer body — Q11 names the footer body).
- Toolbar + nav: 4 (`Cancel`, `Update Life Clock`, `Daily Check-In`, ProgressView spinner has no string).
- `DisclaimerBanner` body: derived from `LifeClockConfiguration.medicalDisclaimer` — not in scope here.

## Per-string decision matrix

Statuses: **TONE-KEY** = ship 3 pool entries; **NEUTRAL** = keep as-is, lock the choice with a doc-comment; **ESCALATE** = operator pick required, draft entries provided below.

### Header pair (Q11 named candidates)

| String | Source | Decision | Reasoning |
|---|---|---|---|
| `"A few quick signals help your Life Clock stay honest."` | QuickLogSheet.swift:47 | **TONE-KEY** (recommend YES) | Named by Q11. Reads as narration, not utility. Gentle could lean toward "listen better"; firmDirect could lean toward "the clock can't read what you don't tell it." Coach keeps the current line. |
| `"No calorie counting. No judgment."` | QuickLogSheet.swift:49 | **TONE-KEY** (recommend YES) | Named by Q11. Currently carries one register's worth of reassurance ("No judgment") that *helps* gentle and is *neutral-positive* for coach but reads slightly soft for firmDirect, where "Just signals." carries the same anti-shame load without the soft hedge. |

### Section labels

| String | Source | Decision | Reasoning |
|---|---|---|---|
| `"Fuel"` | :54 | **NEUTRAL** | Single-word category anchor; tone-shifting risks creating navigation confusion across modes (a user who switched tone would see the picker rename, breaking memory of the surface). |
| `"Rhythm"` | :68 | **NEUTRAL** | Same. Plus the V1.2.0 schema field is literally `dietAmountRhythm` — keeping the label co-located with the field name is the right move. |
| `"Whole food"` | :87 | **NEUTRAL** | Same. |
| `"Extras"` | :101 | **NEUTRAL** | Same. The label is intentionally non-pejorative; firmDirect-keying it to "Vices" or similar would be cruelty disguised as register. |
| `"Recovery"` | :118 | **NEUTRAL** | Same. |
| `"Strength"` | :131 | **NEUTRAL** | Same. |
| `"Nicotine"` | :144 | **NEUTRAL** | Same. Adult-gated label; clinical wording is correct across modes. |

**Q11 alignment.** Q11 says "section labels probably should stay neutral — they're option labels, not narration." Confirmed for all 7. Lock this with a doc-comment.

### Question prompts (subheadline-style `Text` under each section)

These read as narration adjacent to the picker, not as picker option labels. Q11 is silent on them — the question is whether the seven prompts behave like the intro pair (tone-keyed) or like the section labels (neutral).

| String | Source | Decision | Reasoning |
|---|---|---|---|
| `"How did food go today?"` | :55, :58 | **ESCALATE** (recommend NEUTRAL) | Functional prompt; very short; the warmth lives in the picker options ("Great / Okay / Rough"). Tone-keying gains little ("How was food today?" for gentle, "How'd you eat?" for firmDirect) and triples the surface area to maintain. |
| `"How much did you eat for your body's needs?"` | :69, :72 | **ESCALATE** (recommend NEUTRAL) | Same. The May 2 framing was carefully chosen ("for your body's needs" anchors away from calorie thinking) — breaking that into three variants risks losing the anchor. |
| `"At least one solid whole-food meal today?"` | :88, :91 | **ESCALATE** (recommend NEUTRAL) | Same. "Solid whole-food meal" is the diagnostic phrase; rewording per tone risks dilution. |
| `"Any treats, drinks, or heavier choices?"` | :102, :105 | **ESCALATE** (recommend NEUTRAL) | Same. "Heavier choices" already lands as a generous euphemism — neither softening nor sharpening would improve it. |
| `"How stressed did today feel?"` | :119, :122 | **ESCALATE** (recommend NEUTRAL) | Same. Stress wording is clinical-neutral by intent. |
| `"Did you train today?"` | :132, :135 | **ESCALATE** (recommend NEUTRAL) | Same. |
| `"Any nicotine today?"` | :145, :148 | **ESCALATE** (recommend NEUTRAL) | Same. |

**Pattern.** The seven prompts behave as a group. The recommended call is **NEUTRAL for all 7**, treated as a single block with a single doc-comment explaining why. If the operator wants any of them tone-keyed, the group should move together — splitting (e.g. tone-keying "How stressed did today feel?" while leaving "Did you train today?" neutral) creates an inconsistency the user would feel as randomness, not register.

### Picker option labels

| Section | Options | Decision |
|---|---|---|
| Fuel | `Great / Okay / Rough` | **NEUTRAL** |
| Rhythm | `Right / Too much / Too little / Skipped, then over / Irregular` | **NEUTRAL** |
| Whole food | `Yes / Almost / No / —` | **NEUTRAL** |
| Extras | `None / One / A few / A lot` | **NEUTRAL** |
| Recovery | `Low / Medium / High` | **NEUTRAL** |
| Strength | `Not today / Completed` | **NEUTRAL** |
| Nicotine | `None / Used` | **NEUTRAL** |

All 23 option labels are picker semantics — they're keyed into `HabitLog` via the literal raw tags ("great", "okay", "rough", etc.). Tone-shifting these would either decouple display from the storage value (introducing a presentation layer the schema deliberately avoids) or risk silently breaking the engine's switch statements on `dietQuality / dietAmountRhythm / wholeFoodMeal / alcoholLevel / stressLevel`. **Reject categorically; lock with a doc-comment.**

### Captions (Q11 silent — close reads)

| String | Source | Decision | Reasoning |
|---|---|---|---|
| `"No calories, no judgment. Just rhythm."` | :82 | **ESCALATE** (recommend YES) | Mini-narration immediately adjacent to a coarse picker. Echoes the intro subheadline's "No calorie counting. No judgment." — if the intro pair gets keyed but this stays static, the surface develops a register split mid-screen. Coupling them is the consistent move. |
| `"Examples: dessert, drinks, late snack, or an extra-heavy meal."` | :114 | **ESCALATE** (recommend NEUTRAL) | This is concrete example text, not narration. The list itself is what tells the user "these are the things we mean." Tone-shifting "Examples:" to "Things like" / "Examples:" / "Count these:" is variance without payoff. |

### Clear footer block

| String | Source | Decision | Reasoning |
|---|---|---|---|
| `"Clear today's check-in"` | :162 | **NEUTRAL** | Destructive button label; iOS HIG pattern uses verb-noun. Tone-shifting buttons in destructive role risks softening firmDirect's "Wipe today" into ambiguity or hardening gentle's wording into anxiety territory. |
| `"Removes today's manual signals. Your Life Clock will recompute from HealthKit signals only."` | :167 | **TONE-KEY** (recommend YES) | Named by Q11. Two-sentence narration. Gentle and firmDirect both have clean variants that preserve the essential information ("recomputes from HealthKit only") while shifting the register. Coach is the existing line. |

### Toolbar + nav

| String | Source | Decision | Reasoning |
|---|---|---|---|
| `"Daily Check-In"` (nav title) | :176 | **NEUTRAL** | Surface anchor. Renaming per tone would break user memory and accessibility breadcrumbs. |
| `"Cancel"` (toolbar) | :179 | **NEUTRAL** | iOS standard. |
| `"Update Life Clock"` (confirmation CTA) | :186 | **ESCALATE** (recommend YES, with caveat) | The CTA carries narrative weight — it's the moment-of-action language. Tone-keying it would mirror what `wrapUpDismissCTA` already does (`Got it / Continue / Next`). Caveat: the button shows different text depending on whether `store.todayHabits` exists (the surrounding sheet treats it as "save once, edit later" semantically), and "Update Life Clock" doesn't differentiate first-save from re-save. The right move is to tone-key AND state-branch in a single pass, not to tone-key the literal as-is. **Sub-question for operator: should we also state-branch (Save vs. Update) while we're in here, or keep the single-CTA shape?** |
| (loading) `ProgressView()` | :186 | **n/a** | No string. |

### Tally

- **TONE-KEY (recommend YES):** 3 strings — intro headline, intro subheadline, clear footer body.
- **TONE-KEY candidate via ESCALATE (recommend YES):** 2 strings — Rhythm caption, "Update Life Clock" CTA (the latter coupled to a state-branch decision).
- **NEUTRAL (recommend lock):** 47 strings — 7 section labels, 7 question prompts (recommended as a group), 23 picker options, "Examples:" caption, "Clear today's check-in" destructive label, nav title, "Cancel".

If the operator accepts all four YES candidates: **4 new tone keys**, each with 3 pool entries → 12 new strings. Below the Q11 "≥14 new tone keys" threshold by 2. If the operator also flips the 7-question-prompt group to tone-keyed: **11 new tone keys** total, 33 pool entries — that's the threshold case, and the operator should make that call deliberately.

## Q3 friction observations (note-only, no proposals)

Q3 asks: *"What is the minimum daily manual log that feels useful but not annoying?"*

Walked the sheet as a friction read:
- **Adult user sees 7 sections.** That's 7 segmented pickers + 2 sub-captions + 1 intro pair + 1 disclaimer = a tall sheet. On the iPhone 16e baseline (already booted in recent polish sessions), the sheet starts with intro + Fuel visible and the user scrolls through the rest. Recovery + Strength + Nicotine + clear footer + disclaimer are below-fold on a portrait phone.
- **Under-18 user sees 5 sections** (no Rhythm, no Nicotine). The shape is markedly lighter; the "minimum daily manual log" Q3 asks about is closer to what an under-18 user already gets.
- **Default values lean toward "no change."** All 7 fields default to a meaningful neutral (`dietQuality="okay"`, `dietAmountRhythm="right"`, `wholeFoodMeal="unknown"`, `extrasLevel="none"`, `stressLevel="medium"`, `strengthCompleted="notToday"`, `nicotineUsed="none"`). A user who taps Save without touching anything writes 7 defaults to `HabitLog` — the engine treats defaults as zero contribution (per the May 2 commit body), so this is harmless, but the *cost* the user perceives is "7 things to look at" even on a no-change day.
- **Rhythm picker has 5 segmented options — and `"Skipped, then over"` truncates at the *default* content size, not just XXL.** Computer-use checkpoint confirms: every captured screenshot ([quicklog-coach-light.png](screenshots/2026-05-11-quicklog/quicklog-coach-light.png) is representative) shows the segmented control rendering `"Right | Too much | Too little | Skipped… | Irregular"` — the third option is already ellipsized on the iPhone 17 Pro at the *baseline* text size. Segmented controls degrade past 4-5 options; this picker is already past the degradation threshold on the default device. The May 2 commit shipped this and it hasn't been polish-walked. **This is now a confirmed polish issue, not a Q3 friction observation.** The right fix is in Ask 5 below.

Q3 is vision-tier. I do not propose a section to drop or merge; that requires founder-pack alignment with `06_UX_GAME_LOOP.md`. The empirical observation worth keeping is: **the adult sheet's 7-section shape is the maximally-loaded version; the under-18 sheet's 5-section shape is the minimum the schema currently asks for.** Q3 lives in the gap between those two.

## Tone-pool drafts (for the recommended YES candidates)

If the operator approves, the additions to `ToneMode.swift` look like the entries below. Voice anchored against the existing keys (`todayInterpretation*`, `wrapUp*Body`, `historyLongAbsenceBody`, `monthlyLogging*`) so QuickLog reads consistent with Today and History.

### `quickLogIntroHeadline` (new)

```swift
var quickLogIntroHeadline: String {
    switch self {
    case .gentle:     return "A few quick signals help your Life Clock listen better."
    case .coach:      return "A few quick signals help your Life Clock stay honest."
    case .firmDirect: return "Log the day. The clock can't read what you don't tell it."
    }
}
```

### `quickLogIntroSubheadline` (new)

```swift
var quickLogIntroSubheadline: String {
    switch self {
    case .gentle:     return "No calorie counting. Nothing to prove."
    case .coach:      return "No calorie counting. No judgment."
    case .firmDirect: return "No calorie counting. Just signals."
    }
}
```

### `quickLogClearFooter` (new)

```swift
var quickLogClearFooter: String {
    switch self {
    case .gentle:
        return "Clears today's check-in. Your clock will lean on Apple Health for the rest of today."
    case .coach:
        return "Removes today's manual signals. Your Life Clock will recompute from HealthKit signals only."
    case .firmDirect:
        return "Wipes today's manual log. Clock runs on Health data only."
    }
}
```

### `quickLogRhythmCaption` (new — escalated, draft only)

```swift
var quickLogRhythmCaption: String {
    switch self {
    case .gentle:     return "No calories, no judgment — just the shape of the day."
    case .coach:      return "No calories, no judgment. Just rhythm."
    case .firmDirect: return "No calorie math. Just the rhythm."
    }
}
```

### `quickLogSaveCTA(hasExistingHabits:)` (new — escalated, draft only; couples with the Save-vs-Update state-branch sub-question)

```swift
func quickLogSaveCTA(hasExistingHabits: Bool) -> String {
    switch (self, hasExistingHabits) {
    case (.gentle, false):     return "Save today's signals"
    case (.gentle, true):      return "Update today's signals"
    case (.coach, false):      return "Save check-in"
    case (.coach, true):       return "Update Life Clock"
    case (.firmDirect, false): return "Log it"
    case (.firmDirect, true):  return "Update the log"
    }
}
```

## Lock-in doc-comment (for NEUTRAL strings)

If the operator approves any keying, the file should also gain a top-of-file doc-comment locking the neutrality of section labels + question prompts + picker options, mirroring the rationale block now in [SafetyNetView.swift](../../../products/life-clock-ios/Sources/Features/SafetyNet/SafetyNetView.swift) (added 2026-05-11):

> **Tone-key surface for narration only.** The intro pair, the Rhythm caption, the clear-footer body, and the save CTA route through `tone.quickLog*` keys. Section labels (Fuel / Rhythm / Whole food / Extras / Recovery / Strength / Nicotine), the seven question prompts under each section, and all picker option labels (`Great / Okay / Rough`, etc.) are **intentionally neutral**. The picker tags are persisted into `HabitLog` and consumed by `ClockEngine` switch statements; tone-shifting them decouples display from storage. Section labels are anchored on schema fields (`dietAmountRhythm` ↔ "Rhythm"). Question prompts read as picker affordances, not narration. Do not wire any of these through `ToneMode`.

## Asks

### Resolved this session

**Operator approved all 5 asks 2026-05-11 with "go with your recommendations and best judgment. apply those fixes."** All Q11 keys + the Rhythm picker fix shipped in the same pass.

| Ask | Decision | Diff |
|---|---|---|
| **1 — 3 Q11-named tone keys** | YES | `quickLogIntroHeadline`, `quickLogIntroSubheadline`, `quickLogClearFooter` added to [ToneMode.swift](../../../products/life-clock-ios/Sources/App/ToneMode.swift); wired in [QuickLogSheet.swift](../../../products/life-clock-ios/Sources/Features/QuickLog/QuickLogSheet.swift) |
| **2 — Rhythm caption tone-keying** | YES | `quickLogRhythmCaption` added; wired |
| **3 — Save-vs-Update + tone-key CTA combo (Option A)** | YES | `quickLogSaveCTA(hasExistingHabits:)` added with 6-cell pool (3 tones × 2 states); wired at toolbar confirmation Button against `store.todayHabits != nil`. Toolbar `"Cancel"` kept literal (iOS HIG) |
| **4 — 7 question prompts stay NEUTRAL** | YES (lock) | File doc-comment on `QuickLogSheet` enumerates the neutral surfaces (section labels, question prompts, picker options, destructive label, nav title, Cancel) with the rationale per category. No source-string diff |
| **5 — Rhythm picker truncation (Option B)** | YES (Option B) | Rhythm `Picker` switched from `.pickerStyle(.segmented)` to `.pickerStyle(.menu).labelsHidden()`. The `.labelsHidden()` modifier was added because the menu style would have duplicated the prompt inline alongside the existing subheadline `Text` (verified by capture during the implementation pass); without it the surface read the question twice |

**Tests added** in [ToneModeTests.swift](../../../products/life-clock-ios/Tests/ToneModeTests.swift) — 5 new test cases, 20 total (was 15), all green:

- `testQuickLogIntroHeadline_GentlePinsListenBetter` — pins the gentle headline ("listen better") since that's the highest-leverage anti-shame variant.
- `testQuickLogIntroSubheadline_AllTonesPreserveNoCalorieAnchor` — guards the founder-pack "no calorie counting" anchor across all three tones. Any rewrite that drops the phrase regresses.
- `testQuickLogRhythmCaption_AllTonesPreserveNoCalorieAnchor` — same anchor for the Rhythm caption (echoes the subheadline).
- `testQuickLogClearFooter_AllTonesReferenceHealth` — every tone's clear-footer must reference Health / HealthKit as the recompute source (the load-bearing fact, not the register).
- `testQuickLogSaveCTA_StateBranchProducesDistinctLabelsPerTone` — guards the state-branch from collapsing into one label per tone (firstSave ≠ reSave for all three modes).

Convention followed: the existing `testTodayRescueBody_GentleReturnsLogItAndMoveOn` test pins literal gentle copy; the new headline test mirrors it. The other four use *property* assertions (anchor preservation, distinctness) rather than literal pins — this keeps the tests resistant to copy iteration on coach/firmDirect while still catching the regression cases that matter.

### Asks as originally proposed (all resolved per table above — preserved for institutional context)

#### **Ask 1 — Approve the 3 named-by-Q11 tone keys (operator yes/no)**

`quickLogIntroHeadline`, `quickLogIntroSubheadline`, `quickLogClearFooter`. Pool drafts above.

- **Yes** → I add the three keys + wire the call sites in [QuickLogSheet.swift](../../../products/life-clock-ios/Sources/Features/QuickLog/QuickLogSheet.swift) (3 edit points) + add a `ToneModeTests` block covering the 3 keys × 3 tones (9 assertions, ~30 LOC) + capture the 3-tone × 2-scheme × XXL screenshot grid that the brief originally requested. Single PR, well below the Q11 "≥14 new tone keys" threshold.
- **No** → Lock the strings as NEUTRAL with the file doc-comment described above; close Q11 the other way (intro pair + footer kept literal, accepted as the surface's first-impression voice).

#### **Ask 2 — Approve or escalate the Rhythm caption (operator yes/no/sub-question)**

`"No calories, no judgment. Just rhythm."` at QuickLogSheet.swift:82.

- **Yes** (recommend) → Couple with Ask 1; if the intro pair gets keyed, the Rhythm caption should follow so the surface doesn't carry a register-split mid-screen.
- **No** → Keep it literal. Note that the intro subheadline still echoes "No calorie counting. No judgment." — if Ask 1 ships and this stays literal, the gentle/firmDirect users will hear three echoes of the same neutral-coach line on a sheet that just shifted register. Risk: low. Cost of saying yes: 1 extra key + 3 pool entries.

#### **Ask 3 — Approve, escalate, or punt the Save-vs-Update + tone-key CTA combo (operator yes/no, plus a sub-question)**

`"Update Life Clock"` at QuickLogSheet.swift:186 currently renders the same string whether the user is saving for the first time today or updating an existing log. The right fix is **both** tone-keying AND state-branching (`hasExistingHabits` flag from `store.todayHabits != nil` — the same predicate that already controls the Clear button's visibility).

- **Option A — Tone-key + state-branch in one pass.** Ship `quickLogSaveCTA(hasExistingHabits:)`. 1 new function, 6-cell pool, single edit in `QuickLogSheet`. Recommended.
- **Option B — State-branch only, no tone keys.** Two literal CTAs: "Save check-in" / "Update Life Clock". Half the work; loses the register coupling.
- **Option C — Punt.** Keep the literal as-is. Note: "Update Life Clock" reads slightly odd on first save (the clock is not being *updated* from a prior value; it's being *given* a value). Wording correctness argues against C.

Sub-question riding along: should the **toolbar `"Cancel"`** stay literal (recommend yes; iOS HIG) or shift per tone? `WrapUpSheet` uses `tone.wrapUpDismissCTA` for its dismiss action — but Cancel and Dismiss are semantically different (Cancel implies abandonment of unsaved work; Dismiss implies acknowledgement). Recommend keeping Cancel literal even if the save CTA gets keyed.

#### **Ask 4 — Approve the 7-question-prompt block stays NEUTRAL (operator yes/no/escalate-group)**

Recommend yes. The seven prompts read as picker affordances, not narration, and tone-keying them would either (a) split the group and create a register-randomness feel, or (b) move all 7 and push Q11's total tone-key count from 3-4 (sub-threshold) to 10-11 (threshold-case, "needs operator pick before adding ≥14 keys" per Q11 body).

- **Yes** → Lock all 7 with the file doc-comment; no diff to source strings.
- **Escalate** → Add a fifth ask: which of the seven prompts (if any) merit tone-keying, and is the operator OK with the 30+ new pool entries that come with the group move?

#### **Ask 5 — Rhythm picker truncation at default size (chore, confirmed by capture)**

`"Skipped, then over"` is the longest Rhythm option label. **Confirmed at default content size on iPhone 17 Pro:** the segmented picker renders `"Skipped…"`. See [quicklog-coach-light.png](screenshots/2026-05-11-quicklog/quicklog-coach-light.png) and every other capture in the grid. This is no longer hypothetical; it's a regression slot that's been live since the May 2 commit. Fix options:

- **Option A — Shorten the label.** "Skipped, overate" (preserves both events without the comma-then), or "Skip → over", or "Skipped + over." ~1 line change in [QuickLogSheet.swift:76](../../../products/life-clock-ios/Sources/Features/QuickLog/QuickLogSheet.swift). The picker reads/writes the rawValue `"skipBinge"`, unaffected. Test impact: zero.
- **Option B — Switch the Rhythm picker from `.segmented` to `.menu`.** Five options is already past segmented's clean-rendering range on any phone. Menu picker handles long labels gracefully and the spec is honest. ~3 line change.
- **Option C — Defer.** Document the truncation as known, ship Q11 first, fold into the next polish run.

**Recommend B.** A is a workaround; B is the fix. Five-option segmented pickers on a phone are misuse of the control regardless of label length. C defers a visible polish defect.

## Stretch decisions (operator review)

- **`LIFECLOCK_FORCE_QUICK_LOG=1` fixture knob auto-shipped.** Classified as Polish-tier; mirrors the existing `forcePaywall` and `forceSafetyNet` patterns. DEBUG-only, 12 LOC across [LifeClockLaunchConfiguration.swift](../../../products/life-clock-ios/Sources/App/LifeClockLaunchConfiguration.swift) (knob declaration + DEBUG/release init paths) and a 4-line `.onAppear` addition in [TodayView.swift](../../../products/life-clock-ios/Sources/Features/Today/TodayView.swift) (the existing `hasFiredOnce` guard already gates it correctly). Justification: the brief addendum requires the 3-tone screenshot grid; without the knob, every capture iteration needs a cliclick tap on the Today toolbar. Toolbar Buttons ARE reachable via cliclick (only Form/List rows fail per the 2026-05-11 SafetyNet polish), but the forced-sheet pattern is deterministic, race-free, and shaves the visual-stabilization wait. Compounds for future QuickLog polish runs.

- **Did NOT add a `LIFECLOCK_SEED_MINOR=1` knob for the under-18 variant.** The QuickLog sheet's only meaningful divergence is adult (7 sections) vs. under-18 (5 sections, no Rhythm + no Nicotine). Capturing the under-18 variant would need a knob that overrides the hardcoded `Date(timeIntervalSince1970: 631_152_000)` (1990 birth date) in `LifeClockLaunchConfiguration` to a post-2010 date. Scope decision: out of this session. Flagged for a follow-up audit specifically targeting under-18 surface coverage (Q3 lands closest to that question — the under-18 sheet is closer to the schema's current "minimum" answer).

- **Did NOT attempt below-fold scroll captures.** The QuickLog sheet uses a `Form` (SwiftUI List under the hood). Per the 2026-05-11 SafetyNet polish, cliclick scroll on Form rows is unreliable on iOS 26 Simulator. The visible-window captures cover the intro pair + the truncating Rhythm picker — the two highest-value findings. The clear footer at the bottom of the sheet would only verify the literal string already in source (`"Removes today's manual signals…"`), and Q11's classification doesn't depend on the rendered shape — it depends on the register decision. Deferred to the implementation-pass capture.

- **`.labelsHidden()` on the Rhythm menu picker — caught by the post-keying capture, not anticipated by the original Ask 5.** When Ask 5 was originally written as "switch to `.menu`," I assumed dropping `.segmented` would just fix the truncation. The capture showed the menu style displays its accessibility label inline (as a row title with the value + chevron right-aligned). With the existing standalone subheadline `Text("How much did you eat for your body's needs?")` immediately above, the surface read the prompt twice. `.labelsHidden()` is the SwiftUI affordance that suppresses the visible label while preserving it for VoiceOver — keeps a11y intact, keeps the section cadence consistent with the other (segmented) sections. Compounds: any future polish that switches a Form-section Picker from `.segmented` to `.menu` should check whether the sibling subheadline duplicates the label, and apply `.labelsHidden()` if so.

## Captured artifacts

`docs/products/life-clock/screenshots/2026-05-11-quicklog/`:

- [quicklog-gentle-light.png](screenshots/2026-05-11-quicklog/quicklog-gentle-light.png)
- [quicklog-gentle-dark.png](screenshots/2026-05-11-quicklog/quicklog-gentle-dark.png)
- [quicklog-coach-light.png](screenshots/2026-05-11-quicklog/quicklog-coach-light.png)
- [quicklog-coach-dark.png](screenshots/2026-05-11-quicklog/quicklog-coach-dark.png)
- [quicklog-firm_direct-light.png](screenshots/2026-05-11-quicklog/quicklog-firm_direct-light.png)
- [quicklog-firm_direct-dark.png](screenshots/2026-05-11-quicklog/quicklog-firm_direct-dark.png)
- [quicklog-firm_direct-light-XXL.png](screenshots/2026-05-11-quicklog/quicklog-firm_direct-light-XXL.png) — `accessibility-extra-extra-large` content_size; nav title intact, intro pair wraps over 4 lines, no clipping, only intro + Fuel above the fold

`screenshots/2026-05-11-quicklog/post-keying/` (after the 5-ask implementation pass):

- [post-keying/quicklog-gentle-light.png](screenshots/2026-05-11-quicklog/post-keying/quicklog-gentle-light.png) — headline `"… listen better."`, sub `"No calorie counting. Nothing to prove."`, Rhythm caption `"… just the shape of the day."`, CTA `"Save today's signals"`, Rhythm menu picker shows just `"Right ⇕"` with the prompt above as subheadline (no truncation, no duplicate label)
- [post-keying/quicklog-gentle-dark.png](screenshots/2026-05-11-quicklog/post-keying/quicklog-gentle-dark.png)
- [post-keying/quicklog-coach-light.png](screenshots/2026-05-11-quicklog/post-keying/quicklog-coach-light.png) — headline `"… stay honest."`, sub `"No calorie counting. No judgment."`, Rhythm caption `"… Just rhythm."`, CTA `"Save check-in"`
- [post-keying/quicklog-coach-dark.png](screenshots/2026-05-11-quicklog/post-keying/quicklog-coach-dark.png)
- [post-keying/quicklog-firm_direct-light.png](screenshots/2026-05-11-quicklog/post-keying/quicklog-firm_direct-light.png) — headline `"Log the day. The clock can't read what you don't tell it."`, sub `"No calorie counting. Just signals."`, Rhythm caption `"No calorie math. Just the rhythm."`, CTA `"Log it"`
- [post-keying/quicklog-firm_direct-dark.png](screenshots/2026-05-11-quicklog/post-keying/quicklog-firm_direct-dark.png)
- [post-keying/quicklog-firm_direct-light-XXL.png](screenshots/2026-05-11-quicklog/post-keying/quicklog-firm_direct-light-XXL.png) — firmDirect headline wraps over 5 lines at `accessibility-extra-extra-large`; sub over 3 lines; nav title + toolbar (`Cancel` / `Log it`) intact; no clipping

**Pre→post file-size delta confirms divergence.** Pre-keying dark trio was 236-236-236KB (byte-identical). Post-keying dark trio is 254-280-239KB across gentle/coach/firmDirect — each tone now renders distinct copy. Identical pattern for light trio.

**Verified by capture:**

1. **`"Skipped, then over"` truncates to `"Skipped…"` at *default* content size** (see Recon-gotcha 3 below; Ask 5 updated).
2. **Byte-identicality across tones pre-keying.** `gentle-dark.png` (236KB), `coach-dark.png` (236KB), `firm_direct-dark.png` (236KB) are visually identical modulo status-bar clock. Confirms the "pre-keying theater" framing and establishes the diff baseline for the implementation PR.
3. **`FORCE_QUICK_LOG` fires deterministically.** Sheet presents on cold launch via the modified `.onAppear`; works across all tone × scheme combinations once the launch-race gotcha is handled (see Recon-gotcha 2 below).
4. **Nav title + toolbar render correctly at XXL.** Nav title `"Daily Check-In"` does not truncate at `accessibility-extra-extra-large`. Toolbar Buttons (`Cancel`, `Update Life Clock`) remain readable.

## Recon gotchas caught this session (compounds for next polish)

> Three more to document, additive to the 2026-05-09 (`SIMCTL_CHILD_`) and 2026-05-11 SafetyNet (snake-case rawValue + `SEED_STREAK` gating) lists.

1. **`xcrun simctl launch` is async w.r.t. UI mount.** A bare `sleep 2` after `xcrun simctl launch` captures Today mid-load (status: `"Loading…"` headline visible, `quickLogPresented` not yet flipped). Got two blank-Today screenshots in the first capture loop. Bumping to `sleep 4-5` resolved it. Compound: every polish session that uses `simctl launch` + screenshot should default to **`sleep 4`** at minimum, not `sleep 2`.
2. **`xcrun simctl terminate` is also async.** Between iterations of the capture loop, terminating the previous app and immediately launching with new env vars caused the new launch to inherit the previous process's env vars in some cases (saw a `firm_direct-light` capture rendering Today with the coach `"Today's progress"` headline). Polling `launchctl print` for `state = run` to disappear before re-launching fixed it. Compound: in capture loops, wait for terminate to drain before launching. The pattern that worked:
   ```bash
   xcrun simctl terminate $DEV $BID 2>/dev/null
   while xcrun simctl spawn $DEV launchctl print "gui/$(id -u)/UIKitApplication:$BID" 2>/dev/null | grep -q "state = run"; do sleep 0.3; done
   ```
3. **`Picker(.segmented)` with 5 options truncates middle labels at default size.** Confirmed: `"Skipped, then over"` → `"Skipped…"` on iPhone 17 Pro at baseline content_size. The May 2 commit added the 5-option Rhythm picker; this regression has shipped for 9 days unflagged because no polish run had captured the sheet. Compound: any future addition that pushes a `.segmented` Picker past 4 options on a phone should be reviewed for the same; the right control past 4 options is `.menu` or `.wheel`.

---

**Bottom line.** Q11 resolved. All 5 operator asks shipped in a single pass: 4 new tone keys + 1 state-branched function (`quickLogIntroHeadline`, `quickLogIntroSubheadline`, `quickLogRhythmCaption`, `quickLogClearFooter`, `quickLogSaveCTA(hasExistingHabits:)`) — 15 new pool entries, below Q11's ≥14-keys threshold by 1 (the state-branch adds 6 cells across 1 key, not 3); the 47 NEUTRAL strings are locked with a file doc-comment on `QuickLogSheet`; the Rhythm picker switched from `.segmented` (which truncated `"Skipped, then over"` at default size) to `.menu.labelsHidden()` (clean, prompt visible above as subheadline). One `LIFECLOCK_FORCE_QUICK_LOG=1` fixture knob compounds for future polish. Five new `ToneModeTests` assertions pin the no-calorie anchor, the Health/HealthKit reference, the state-branch distinctness, and the gentle headline. Total: 5 source files, +203/−8 LOC, 7 + 7 screenshots (pre-keying baseline + post-keying verification), 20/20 ToneModeTests green. Three recon gotchas documented for the next polish run. The brief's `LIFECLOCK_SIMULATOR_PRO_DISABLED` knob remains a no-op for this surface.
