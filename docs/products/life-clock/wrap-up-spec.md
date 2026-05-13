# Wrap-Up Spec — Life Clock

> **Status:** Canonical product policy. Wrap-ups are the retention hook of Life Clock (per [`BUSINESS_PLAN.md`](BUSINESS_PLAN.md) — "the clock is the activation hook; the weekly wrap-up is the retention hook"). This spec governs when wrap-ups fire, what variants exist, what they show in Free vs Pro, and how they interact with the notifications constraints. Reference implementation: [`Sources/Engines/WrapUpCoordinator.swift`](../../../products/life-clock-ios/Sources/Engines/WrapUpCoordinator.swift) and [`Sources/Features/WrapUp/WrapUpSheet.swift`](../../../products/life-clock-ios/Sources/Features/WrapUp/WrapUpSheet.swift).

## One-line rule

**Wrap-ups are pull-only, in-app ceremonial moments that the user discovers on cold-launch — never push notifications, never lock-screen surfaces.** Free wrap-ups give the *first meaningful reflection layer* (signed delta + tone-aware body); Pro wrap-ups add the depth Free hints at (drivers + next-best lever).

## The two variants

| Variant | When it fires | Content |
|---|---|---|
| **Yesterday wrap-up** | Cold-launch on a new day if the user lived through yesterday and hasn't been shown a yesterday wrap-up for that day | Yesterday's signed minutes, a tone-aware heading, a ClockHandView animation (1.4s) of the minute hand sweeping |
| **Weekly wrap-up** | Cold-launch on a new week-start (default Monday) if no weekly wrap-up has been shown for that week and the week is no more than 14 days stale | The week's signed minutes, a tone-aware heading, a ClockHandView animation (2.2s) of the cumulative sweep |

Decision priority: **yesterday wins over weekly.** Never both at once. The weekly queues behind the yesterday — the next eligible cold-launch shows it.

## Coordinator contract (read-only summary; binding contract is the source)

`WrapUpCoordinator.pendingWrapUp(profile:snapshots:weeks:now:)` returns `Optional<PendingWrapUp>`. The function is pure — takes value-type DTOs (never `@Model` instances), no side effects, fully testable with a pinned clock.

Inputs:

- `ProfileSnapshot` — `onboardingCompletedAt`, `lastShownYesterdayWrapUpDay`, `lastShownWeeklyWrapUpWeek`. The first guards against ghost wrap-ups on reinstall (user must have lived through one full day post-install); the latter two prevent re-presentation.
- `[DaySnapshot]` — `date` + `hasMinimumData` (true iff at least one HK metric is non-zero AND HK auth was granted for that type at capture time).
- `[WeekSnapshot]` — `weekStart` in the configured `firstWeekday`.
- `now` — explicit, so tests pin time.

After presentation, `LifeClockStore.markWrapUpShown(_:)` advances the appropriate `lastShown…` field and clears `pendingWrapUp`. Same-day re-launches do not re-fire.

### Week-start is pinned, not locale-dependent

`Config.firstWeekday = 2` (Monday). This is a product decision — not a Calendar decision — because the wrap-up is a ceremony, not a calendar UI element. Pinning guarantees test/prod parity across US (Sunday-default) and EU (Monday-default) locales. Don't change it without a vision-question ratchet.

## Free vs Pro split

The Free/Pro rule from [`MONETIZATION.md`](MONETIZATION.md): **Free = understanding, Pro = depth, archive, and correction power.** Applied to wrap-ups:

### Free wrap-up content (must ship)

- Tone-aware heading (`toneMode.yesterdayWrapUpHeading` / `toneMode.weeklyWrapUpHeading`).
- ClockHandView animation of the minute hand sweeping (the ceremony itself).
- Signed-minutes readout (`TimeDeltaFormatter.format`).
- Tone-aware body line (`wrapUpPositiveBody / wrapUpNegativeBody / wrapUpZeroBody`).
- DismissButton (or sheet swipe-down).

Free users see the first meaningful reflection layer: *what happened, and how to feel about it.* They do not see the deeper breakdown that explains why.

### Pro wrap-up content (post-Pro layer)

Pro users see everything Free users see, **plus**:

- **Top 3 drivers** that contributed to the signed-minutes total. Same data structure that drives the Today "Why it changed" card (`driversCard`) and the History weekly summary (`HistoryView.weeklySection`).
- **Next-best lever** — the highest-leverage habit the engine recommends tomorrow (yesterday wrap-up) or next week (weekly wrap-up).
- **"See the full week" affordance** — on the weekly variant only, a tap-through that opens the History tab scrolled to the relevant week (`HistoryView` deep-link with the right `weekStart` parameter).

### Pro signal (Free-side) — pro-value-backlog Prompt 3

Free users currently see no Pro affordance on the WrapUpSheet at all. This is the most-cited gap in the pro-value audit (`pro-value-backlog-2026-05-12-standard.md` Prompt 3) — it's "best conversion moment #3" in [`MONETIZATION.md`](MONETIZATION.md) and currently fires zero signal.

The signal must:

- Appear **after** the ceremony lands (don't interrupt the signed-minutes reveal animation).
- Be **non-intrusive** — a single row, not a full upsell card. The wrap-up is reflective; the Pro pitch is structural addition, not interruption.
- **Quote the Free/Pro rule honestly** — "Pro shows the drivers + the lever" maps cleanly to MONETIZATION.md's "depth" claim.
- Open `PaywallSheet(scrollTo: .top)` on tap (or a future `PaywallSheet.Section.weeklyReport` anchor when one exists).
- **Never on yesterday wrap-ups** — only on weekly. Daily reflection is not the moment to upsell; weekly retrospective is.

Suggested copy (tone-aware; pick from the existing `ToneMode` pools rather than inventing a fourth voice):

- Coach: "Pro shows the three drivers + the one habit to lever this week."
- Gentle: "Pro adds a little more — the drivers, and one gentle nudge for next week."
- Firm/Direct: "Pro: drivers, and the one lever. Now."

## Presentation rule (vision Decided 2026-05-09 — pull, not push)

Wrap-ups are **in-app `.sheet` presentations on cold-launch / foreground cycle**. They are never:

- Push notifications.
- Lock-screen widgets (no widgets ship in v1).
- "We miss you" re-engagement copy.

`WrapUpCoordinator` never calls `NotificationsService.setSchedule`. The presentation channel is `LifeClockApp.body` `.sheet(item: $store.pendingWrapUp)`. This is a binding vision-Decided constraint — see [`vision.md`](vision.md) § Decided constraints and operator memory `feedback_life_clock_notifications_constraints.md`.

Why pull-only: the wrap-up is a ceremonial reflection moment. Pushing it as a notification turns it into an interruption ("hey, look at your numbers!") which is the opposite of reflective. Reflection is a *return* — the user opening the app *and discovering* a wrap-up is on-brand; the wrap-up demanding attention is off-brand.

## Anti-patterns (binding refusals)

- **Do not push wrap-ups to the lock screen.** Hard refusal — vision Decided constraint.
- **Do not stack wrap-ups.** Yesterday and weekly never present together. If both are eligible, yesterday goes first; weekly queues for the next cold-launch.
- **Do not re-present a wrap-up on same-day re-launch.** `markWrapUpShown` advances the `lastShown…` field; honor it.
- **Do not present wrap-ups before `onboardingCompletedAt + 1 full day`.** Ghost wrap-ups on reinstall are a trust regression — the coordinator guards this and call sites must not bypass.
- **Do not present a weekly wrap-up older than 14 days** (`weeklyRecencyDays`). A user returning after a long absence should land on Today, not a stale ceremony.
- **Do not extract `WrapUpSheet` content into a reusable component** until the Pro variant adds the drivers / lever row. The current sheet is simple; preemptive abstraction makes the Pro split harder, not easier.
- **Do not interrupt the ClockHandView animation with a Pro signal.** The signal renders after the animation completes — the ceremony has primacy.
- **Do not present a Pro signal on yesterday wrap-ups.** Daily reflection ≠ upsell moment.

## How this spec interacts with related specs

- **Motion** (`motion-spec.md`): the ClockHandView durations (1.4s yesterday / 2.2s weekly) are intentionally above the `breath` tier — they are narrative beats, not motion. They were chosen via vision-question review; do not migrate them to `Motion.Duration` without re-ratcheting.
- **Lighting** (`lighting-spec.md`): the ceremony's clock face should adopt `lightingDepth(referenceSize:)` once the elevation work in premium-feel-backlog Prompt 5 lands. Today it uses ad-hoc shadow constants — a documented elevation gap.
- **Notifications** (`TECHNICAL_ARCHITECTURE.md` § Notifications constraints): wrap-ups consume zero notification budget. The "one daily reminder" notification is unrelated; do not co-schedule them.

## Telemetry

When telemetry instrumentation lands post-TestFlight (`ROADMAP_METRICS.md` § Retention metrics), wrap-up impressions are the canonical retention signal — "weekly WrapUpSheet impressions" per active user is the renamed equivalent of the old "weekly report opens" metric. Until then, no analytics events fire on wrap-up dismiss.

## Cross-references

- Coordinator implementation: [`Sources/Engines/WrapUpCoordinator.swift`](../../../products/life-clock-ios/Sources/Engines/WrapUpCoordinator.swift)
- Sheet implementation: [`Sources/Features/WrapUp/WrapUpSheet.swift`](../../../products/life-clock-ios/Sources/Features/WrapUp/WrapUpSheet.swift) + `ClockHandView.swift`
- Tone pools: `Sources/App/ToneMode.swift` (`wrapUpHeading` / body pools)
- Vision constraint: [`vision.md`](vision.md) § Decided constraints (pull-not-push 2026-05-09)
- Operator memory: `feedback_life_clock_notifications_constraints.md`
- Free/Pro rule: [`MONETIZATION.md`](MONETIZATION.md) § Free vs Pro Rule
- Pro-value gap: `pro-value-backlog-2026-05-12-standard.md` Prompt 3 (the WrapUp Pro signal)
- Sequencing source of truth: [`PHASE_STATUS.md`](PHASE_STATUS.md)

## Validation

The wrap-up surface is on-spec when ALL of the following hold:

1. Cold-launch on a new day with yesterday eligibility presents `yesterday`, not `weekly`.
2. Weekly wrap-up presents only at start-of-week (configured Monday) when no weekly has been shown for that week.
3. Same-day re-launches do not re-present.
4. `pendingWrapUp` is never set to a wrap-up older than 14 days.
5. Free users see the heading + clock-hand animation + signed minutes + tone-aware body, and nothing else.
6. Pro users see those PLUS the top 3 drivers + next-best lever + "See the full week" affordance.
7. No push notification is scheduled for wrap-ups.
8. The Pro-signal row appears only on **weekly** Free wrap-ups, after the animation, and routes to `PaywallSheet`.

When (8) ships, pro-value-readiness flag moves a step toward green (the WrapUp `pro-thin` verdict resolves).
