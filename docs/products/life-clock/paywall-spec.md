# Paywall Spec — Life Clock

> **Status:** Canonical product policy. Consolidates the paywall behavior the [`pro-value-rule.md`](pro-value-rule.md) audit walks (Discoverability / Justification / Perceived depth / Friction-to-trial / Upsell moments / Trust / Value-claim accuracy) into a single doc the code can point at. Implementation: [`Sources/Features/Paywall/PaywallSheet.swift`](../../../products/life-clock-ios/Sources/Features/Paywall/PaywallSheet.swift) + [`Sources/Features/Onboarding/Screens/PaywallPrimaryView.swift`](../../../products/life-clock-ios/Sources/Features/Onboarding/Screens/PaywallPrimaryView.swift) + [`SubscriptionStore.swift`](../../../products/life-clock-ios/Sources/Services/SubscriptionStore.swift).

## One-line rule

**The paywall earns the upgrade by quoting MONETIZATION.md § Pro Annual verbatim. Every claim maps to a shipped surface; every shipped surface maps to a claim; trust signals (restore, cancel, no-trial honesty) are surfaced where Apple's reviewers will look.**

## The two paywall surfaces

The app has **two** paywall surfaces, intentional, with different jobs:

| Surface | File | Job |
|---|---|---|
| **`PaywallPrimaryView`** | `Sources/Features/Onboarding/Screens/PaywallPrimaryView.swift` | First-impression paywall at the end of the reveal escalator. Single-tier (annual). Pre-selected. One CTA. Skip path lands the user on Today as Free. |
| **`PaywallSheet`** | `Sources/Features/Paywall/PaywallSheet.swift` | Reachable paywall throughout the app. Three tiers (monthly / annual / lifetime), annual pre-selected. Restore + manage-subs surfaced. Supports scroll-to anchors (`.top`, `.whatIfSimulator`, `.restore`) so call sites can land the user on the relevant section. |

Both surfaces consume `SubscriptionStore` for products + entitlements. Auto-dismissal on `isPro == true` flip is handled by both.

## Header contract (binding — sources from MONETIZATION.md)

The `PaywallSheet` header carries the title + the **5 shipped Pro Annual bullets** sourced verbatim from [`MONETIZATION.md`](MONETIZATION.md) § Pro Annual:

1. **Full daily history** — every past day, drillable
2. **Weekly drivers + next-best lever** — the deeper breakdown in History and richer weekly wrap-ups
3. **Correction power** — override imported Apple Health values you know are wrong
4. **Custom Today's Plan** — pick the daily-plan actions that fit your life
5. **Deeper trend breakdown** — the Future-tab What-If Simulator

The header subhead reads "**Pro unlocks the depth Free hints at:**" + the bullets + "**Your free experience keeps working either way.**" footer. **Do not edit copy in the header without updating MONETIZATION.md in lockstep** — the App Review value-claim guard requires marketing copy to match what the app actually delivers.

Aspirational bullets (advanced HealthKit, widgets, AI meal/photo) live in MONETIZATION.md § Pro Annual "Planned (post-v1)" and **do not appear in the paywall header** until they ship.

## Visual-signal vocabulary (binding — two-glyph convention)

Pro signaling across surfaces uses **two glyphs with different jobs**:

| Glyph | Job | Color treatment | Used by |
|---|---|---|---|
| `sparkles` (SF Symbol) | **Pitch / discovery** — invites the user to consider Pro. Forward-looking. | `.foregroundStyle(.tint)` (full accent) | Profile "Upgrade to Pro" row, WrapUp weekly Pro signal, the only-Pro feature card affordance |
| `lock.fill` (SF Symbol) | **Gate / state** — marks a surface as Pro-only at this moment. Stateful. | `.foregroundStyle(.tint)` with `.opacity(0.5)` when on the locked surface itself; full `.tint` when in an upsell badge | History fog overlays, Today Plan-Editor chip, Future What-If slider thumb (when `!isPro`) |

Plus the active-Pro indicator on Profile (`checkmark.seal.fill` + `.tint`) — distinct because it's not a Pro pitch, it's an *active-state acknowledgment*.

**Rules:**

- Never use `lock.fill` for a pitch (it reads as restrictive, not invitational).
- Never use `sparkles` for a gate (it reads as celebratory on a surface the user can't reach).
- Never mix glyphs on a single surface. A surface either pitches (`sparkles`) or signals gating (`lock.fill`) — not both.
- The chevron-right (`chevron.right`) at the trailing edge of a row is the universal "tap to go" affordance — applies to both pitch rows and gate rows when the tap routes somewhere.

## Discoverability touchpoints

Per [`pro-value-rule.md`](pro-value-rule.md) Pro touchpoint inventory, these surfaces signal Pro to Free users:

| Touchpoint | Signal | Routes to |
|---|---|---|
| **Today** | Plan Editor "Edit" chip locks for Free; tap → paywall | `PaywallSheet(scrollTo: .top)` |
| **History** | Older-row fog stack; weekly cards Pro-section locked | `PaywallSheet(scrollTo: .top)` |
| **Future tab** | What-If Simulator slider thumb locked for Free | `PaywallSheet(scrollTo: .whatIfSimulator)` |
| **WrapUp** | Weekly Free wrap-up shows a tone-aware "see more with Pro" row AFTER ceremony lands (per [`wrap-up-spec.md`](wrap-up-spec.md) § Pro signal) | `PaywallSheet(scrollTo: .top)` |
| **Profile** | Subscription section shows "Upgrade to Pro" button for Free, "Manage subscription" row for active Pro | `PaywallSheet(scrollTo: .top)` or iOS `.manageSubscriptionsSheet` |
| **PaywallSheet itself** | Reachable from all surfaces above | — |
| **Settings / subscription management** | Same as Profile (Subscription section) | — |

A Pro touchpoint not on this list = inventory drift → `pro-invisible` audit prompt. Adding a Pro gate requires adding a discoverability signal here.

## Justification: claim ↔ delivery

Every paywall claim must map to a shipped surface. The audit checks this directly.

| Paywall claim | Shipped surface | Gate code path |
|---|---|---|
| "Full daily history — every past day, drillable" | `HistoryView` fog stack lifts; `DayDetailView` accessible | `HistoryView.swift:227–276` |
| "Weekly drivers + next-best lever" | `HistoryView.weeklySection` Pro branch (drivers + lever cards); WrapUp Pro variant | `HistoryView.swift:337–352` |
| "Correction power — override imported Apple Health values you know are wrong" | `OverrideSheet` from History day-detail; `applyOverride` / `revertOverride` Pro-gated | `OverrideService.swift:36`, `EntitlementGatedWritesTests.swift:33` |
| "Custom Today's Plan — pick the daily-plan actions that fit your life" | `PlanEditorSheet` Pro-gated edit chip on Today | `LifeClockStore.swift:794` (`selectPlanQuest` `.notEntitled` throw) |
| "Deeper trend breakdown — the Future-tab What-If Simulator" | `FutureView` + `WhatIfSlider` Pro-only thumb | `WhatIfSlider.swift:148`, `FutureView.swift:206` |

Removing a Pro feature without updating the paywall (and MONETIZATION) = `value-claim-unjustified` audit prompt → submission-blocker.

## Friction-to-trial

The paywall is reachable without account creation, without analytics opt-in, without anything beyond a tap. Specifically:

- **Onboarding skip path** preserves Free state — user can skip `PaywallPrimaryView` via `onClose` and land on Today as Free.
- **Throughout-app paywall** is one tap from any Pro touchpoint.
- **Annual pre-selected** to nudge toward better retention (RevenueCat 2026 benchmark) but every tier is one tap to pick.
- **Restore** is a toolbar button on PaywallSheet + a separate row in Profile Subscription. Both surface a three-state outcome (restored / nothing-to-restore / failed-with-error).
- **No "create account" gate.** The app has no account.
- **No "verify email" gate.** The app has no server.

## Trust signals (binding — submission-blocker if absent)

Every PaywallSheet renders these at the bottom:

- Auto-renew disclosure: "Subscriptions auto-renew until cancelled in iOS Settings → [your name] → Subscriptions. Cancel any time." (Apple § 3.1.2 requirement, see `legal/terms-of-use.md` § Auto-Renewal Disclosure)
- Terms of Use link to `legal/terms-of-use.md`.
- Privacy Policy link to `legal/privacy-policy.md`.
- Restore button visible in toolbar.
- Error surface in fineprint when subscription operations fail.

Plus, on Profile Subscription section for active Pro users:

- **Manage subscription** row that opens iOS-native `.manageSubscriptionsSheet`. Closes the "buried cancel" trust-gap risk. **Submission-blocker if missing.**

Per [`subscription-lifecycle-spec.md`](subscription-lifecycle-spec.md), the app never:

- Caches `isPro` to UserDefaults.
- Blocks app startup on entitlement load.
- Surfaces a "Cancelled" badge.
- Re-prompts the paywall when entitlement disappears.
- Erases historical data on demote.

## Trial stance (binding — vision 2026-05)

**v1 ships without an introductory trial.** `Products.storekit` has `"introductoryOffer": null` for both monthly and annual subscriptions. The paywall copy makes no trial claim. **Adding any trial language without provisioning an actual App Store Connect introductory offer = App Review rejection vector.** Re-evaluation is a v1.1 candidate based on trial-free launch analytics.

## Upsell moments (binding — sourced from MONETIZATION.md § Best conversion moments)

The five moments are annotated with wiring status in MONETIZATION.md. As of 2026-05-13:

1. After first Life Clock reveal. **Wired.** (Onboarding terminal `PaywallPrimaryView`.)
2. After tapping a locked detailed driver breakdown. **Wired.** (History fog + Future-tab What-If slider lock.)
3. After the first weekly wrap-up preview. **Wired** (this commit — `wrap-up-spec.md` § Pro signal).
4. When the user wants advanced HealthKit metrics. **Deferred to v1.1.**
5. When the user wants widget / Lock Screen surfaces. **Deferred to v1.2.**

When a moment moves from "Deferred" to "Wired," the paywall header and the discoverability touchpoint table both update in the same commit.

## Anti-patterns (binding refusals)

- **Do not promise a feature on the paywall that doesn't ship.** Value-claim-unjustified = submission-blocker.
- **Do not claim a trial that isn't in App Store Connect.** Same submission-blocker risk.
- **Do not interrupt the wrap-up ceremony with a Pro signal.** The signal renders after the animation lands; ceremony has primacy ([`wrap-up-spec.md`](wrap-up-spec.md)).
- **Do not fire a Pro signal on yesterday wrap-ups.** Daily reflection ≠ upsell moment.
- **Do not auto-present the paywall on every cold-launch.** Re-engagement-prompt patterns are the dark-pattern adjacency that gets called out in App Review.
- **Do not gate the close-paywall affordance.** Drag-to-dismiss + Close button + system swipe-down all work; verified by the 2026-05-10 gestural final-check.
- **Do not show a "Cancelled" status anywhere.** Apple owns the cancellation surface.

## Cross-references

- Source: paywall implementations + `SubscriptionStore`
- Free/Pro rule: [`MONETIZATION.md`](MONETIZATION.md) (the spec quotes MONETIZATION.md as the source of truth for header copy)
- Pro touchpoint inventory: [`pro-value-rule.md`](pro-value-rule.md)
- Lifecycle states: [`subscription-lifecycle-spec.md`](subscription-lifecycle-spec.md)
- Wrap-up Pro signal: [`wrap-up-spec.md`](wrap-up-spec.md) § Pro signal
- Trust + cancel: [`pro-value-rule.md`](pro-value-rule.md) § Trust
- Pro-value audit findings: `pro-value-backlog-2026-05-12-standard.md`
- App Store Connect setup: [`ASC_CHECKLIST.md`](ASC_CHECKLIST.md)

## Validation

The paywall is on-spec when ALL of the following hold:

1. PaywallSheet header bullets match MONETIZATION.md § Pro Annual verbatim (5 v1 bullets; planned items not in the header).
2. Every shipped Pro gate has a paywall-claim row in the table above.
3. Every paywall-claim row has a verified shipped surface.
4. All 7 Pro touchpoints in `pro-value-rule.md` § Touchpoint inventory have a discoverability signal routing to PaywallSheet.
5. Restore returns one of three terminal outcomes (restored / nothing-to-restore / failed-with-error).
6. Profile Subscription section shows the Manage subscription row when `isPro == true`.
7. No trial copy exists anywhere in the paywall (until an ASC introductory offer is provisioned).
8. Trust signals (auto-renew disclosure, terms, privacy, restore) are present on every PaywallSheet render.

When (1)–(8) hold, the pro-value-readiness flag's paywall preconditions are met.
