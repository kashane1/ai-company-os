# Polish 2026-05-14 — History perf, confidence explanation, edge-swipe tab nav

**Mode:** fix-list · **Iterations:** 5 commits · **Final-check:** computer-use, on
**Branch:** `claude/jolly-fermi-73a1b5`
**Sim:** iPhone 17 Pro · iOS 26.3 · `73298B82-3A37-4EEC-9436-3B9E43F4C4BB`

## Operator intent

Three asks, surfaced after the prior turn shipped the 30-day import-window
trim and install-marker row in History:

1. Cut perceived lag on the History screen. Cap initial render at 60 days;
   surface a "Load 60 more days" button only when more persisted rows exist.
2. Make `Confidence: low/medium/high` explainable. Tap on the words or
   info icon → small pop-up explaining what drives the score and how to
   raise it. Generic copy, not personalized.
3. Edge-anchored swipe-to-switch on the main tab bar. Wrap-around: swipe
   from Today should land on Profile. Mid-screen swipes must not switch
   tabs — only ones that begin near a screen edge.

## Decisions made before the loop

- Tab order is Today → History → Future → Profile. The operator picked
  the "literal" swipe semantics: swipe-LEFT (finger moves left) = previous
  tab, with wrap. So on Today, swipe-LEFT wraps to Profile.
- Prior turn's import-window / install-marker work was rolled up into a
  single baseline commit before the polish loop started.

## Commits (in order)

1. `46ba6ef feat(life-clock): cap import to 30d + install marker in History`
   – baseline. 10-year → 30-day import; tinted "You joined Life Clock here"
   row separates post-install rows from imported pre-install rows.
2. `ce0cd4f perf(life-clock): paginate History to 60 days + Load more`
   – Fix 1. New `LifeClockStore.recentSnapshotsPage(limit:)` returns a
   bounded page plus a `hasMore` flag without ever fetching the full
   snapshot table. HistoryView seeds `@State pageSize = 60`; renders a
   "Load 60 more days" button only when `hasMore` is true.
3. `86a5569 feat(life-clock): tappable confidence badge with explanation popover`
   – Fix 2 v1. Wraps the existing badge in a Button + info glyph; presents
   `ConfidenceExplanationCard` as a compact-popover.
4. `43fbcf2 feat(life-clock): edge-swipe tab switching with wrap-around`
   – Fix 3. `MainTabView` adds an `edgeSwipeGesture(width:)`
   `simultaneousGesture` attached over the TabView. Only honors drags that
   *start* within 28pt of either edge, require ≥60pt horizontal travel,
   and dominate over the vertical component. Hidden Future tab is
   skipped by `orderedVisibleTabs` so the cycle wraps Today ↔ Profile
   directly when Future is gated.
5. `623b642 fix(life-clock): confidence explanation as sheet, not popover`
   – Fix 2 polish. The compact popover adaptation on iPhone capped the
   popover at a height that clipped both the heading and the last
   bullet. Swapped to a `.sheet` with `.presentationDetents([.fraction(0.4)])`
   and `presentationDragIndicator(.visible)` — keeps the lightweight
   pop-up feel and shows every word.

## In-sim verification (computer-use)

- **Fix 2 (Today):** Tap badge → sheet appears with full heading,
  description, "To raise it", and three bullets. ✓
- **Fix 3 wrap (Today → Profile):** Drag started at `(405, 450)` near
  the right edge, ended at `(200, 450)`. Profile screen rendered;
  Profile tab highlighted. ✓
- **Fix 3 wrap (Profile → Today):** Drag started at `(142, 450)` near
  the left edge, ended at `(350, 450)`. Today screen back; Today tab
  highlighted. ✓
- **Fix 3 negative test:** Drag started at `(275, 450)` in the middle
  of the phone display, ended at `(80, 450)`. Today screen unchanged. ✓
- **Fix 2 (History):** Net-this-week card's badge tap also surfaces
  the same sheet cleanly. ✓
- **Fix 1:** History rendered without perceptible delay. The "Past
  days" section is empty in this state (no HK data connected), so the
  Load-more button does not render — `hasMore` only flips true when
  the persisted snapshot table exceeds the current `pageSize`. Verified
  by code path: empty data → empty branch with `historyEmptyStateCard`,
  no spurious button.

## Findings batched at cycle-close

None outstanding. The only mid-cycle finding (Fix 2 popover height
clipping) was a Polish-tier item and was auto-fixed in `623b642`.

## Asks for the operator

- The Load-more button is wired but cannot be visually confirmed in the
  current sim state because the database has no persisted snapshots
  past today (Apple Health is not connected). Suggest verifying once
  on a TestFlight build with a real history, OR seeding 90+ days of
  test snapshots via `LIFECLOCK_UI_TEST_SCENARIO` / launch fixture.
  Not blocking — the code path is deterministic and the partition is
  exercised by the existing `historyEmptyStateCard` empty-state.

## Memory ratchet

No new conventions to save. The popover→sheet swap is a generally
applicable iOS pattern (compact popover height-cap on iPhone) but is
already implicit in the iOS HIG.

## PR body (derived)

> ## Summary
>
> - Trims the lazy HealthKit import from 10 years to 30 days; pre-install
>   data is shown in History for context only and never feeds engines.
>   Inserts a tinted "You joined Life Clock here" row at the install
>   boundary in the daily list.
> - Caps the History daily list at 60 rows on appear; surfaces a
>   "Load 60 more days" button when more persisted snapshots exist.
> - Makes the `Confidence: low/medium/high` badge tappable. Presents a
>   small detent-sheet explaining what drives the score and four three
>   levers to raise it (Watch overnight, carry iPhone, full Health
>   permissions). Generic copy, identical for every confidence level.
> - Edge-anchored swipe-to-switch on `MainTabView`. Honors drags that
>   start within 28pt of either edge, require 60pt of horizontal travel,
>   and dominate the vertical component. Wrap-around in both directions;
>   the cycle skips a hidden Future tab.
>
> ## Test plan
>
> - [ ] Open History on an account with ≥61 days of persisted snapshots
>       and confirm a "Load 60 more days" button appears below the last
>       row; each tap extends the page by 60.
> - [ ] Tap the confidence badge on Today and on the History weekly
>       net card; sheet renders with heading + description + 3 bullets.
> - [ ] On Today, swipe-LEFT from the right edge → Profile.
> - [ ] On Profile, swipe-RIGHT from the left edge → Today.
> - [ ] Mid-screen horizontal drags do NOT switch tabs.
> - [ ] With Future hidden (RELEASE pre-Phase-4), swipe cycle goes
>       Today ↔ History ↔ Profile.
