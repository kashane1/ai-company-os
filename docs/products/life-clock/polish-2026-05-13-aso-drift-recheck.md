# ASO Drift Re-Check — 2026-05-13

> **Skill:** none (pro-value-audit follow-through; resolves [pro-value-backlog-2026-05-13-standard.md § P7](pro-value-backlog-2026-05-13-standard.md)).
> **Inputs:** [APP_STORE_ASO.md](APP_STORE_ASO.md) ↔ in-app state at commit `79a10fe` (post-Sprint-D + smoke-test).
> **Author:** Claude (single-pass walk).

## Scope

Walk every claim or feature mention in `APP_STORE_ASO.md` and identify the post-Sprint-D in-app surface that delivers it. Catches: stale claims, screenshot drift, marketing↔UI mismatch.

## Walk

| ASO surface | ASO claim | In-app source-of-truth | Verdict |
|---|---|---|---|
| App Store listing name (30-char) | "Life Clock: habits earn time" | `LifeClockConfiguration.appTagline = "Habits earn time."` + Decided 2026-05-11 onboarding lead-in headline `WelcomeView.headline = "Earn time with better habits."` | ✅ delivered |
| In-app display name | "Life Clock" | `Info.plist` `CFBundleDisplayName` + `LifeClockConfiguration.appName` | ✅ delivered |
| Tagline | "Habits earn time." | `LifeClockConfiguration.appTagline` | ✅ delivered |
| App Store subtitle constant | "See how habits move your life" | `LifeClockConfiguration.appStoreSubtitle` | ✅ delivered |
| Subtitle option 1 | "Earn time with better habits" | `WelcomeView.headline` ([LeadInScreens.swift](../../../products/life-clock-ios/Sources/Features/Onboarding/Screens/LeadInScreens.swift)) — Decided 2026-05-11 | ✅ delivered |
| Subtitle option 4 | "Turn healthy habits into time" | Conceptually rendered across Today (clock + delta) + onboarding ReactiveSliderView ("Drag to see how habits move your clock.") | ✅ delivered |
| Description sentence | "Life Clock turns your Apple Health data and daily habits into a simple time-based game." | HealthKit ingestion (`HealthKitService`) + 1–3 daily quests (`QuestEngine`) + Time-currency Decided constraint 2026-05-04 | ✅ delivered |
| Description claim | "See what moved your healthspan trajectory today" | Today drivers section + `ToneMode.profileUpgradeSubline` references "drivers" | ✅ delivered |
| Description claim | "complete small quests" | Today's Plan 1–3 quests + Plan Editor (Pro) | ✅ delivered |
| Description claim | "build a longer, stronger future one day at a time" | Future tab projection + daily-delta loop | ✅ delivered |
| Screenshot 1 — "See your Life Clock" | Today screen with mascot + clock + headline delta | `TodayView` post-Sprint-A1 (typography numeric-display exception locked) + Sprint-B1 (`cardLighting` on 6 cards) | ✅ delivered. **Screenshot likely needs regeneration** — pre-Sprint-A1 captures lack the Save ~48% badge in any paywall-adjacent crop, and pre-Sprint-B1 captures lack the visual lift on Today cards. |
| Screenshot 2 — "Earn time with healthy habits" | Onboarding "Earn time with better habits." headline OR quest-completion payoff | Decided 2026-05-13 quest-completion payoff (A+B+C layered) is the canonical "earn time" moment in-app | ⚠️ delivered; **screenshot likely needs regeneration** to reflect the layered payoff (mascot pulse + clock-hand advance + tone-aware micro-copy) shipped in commits `75f7cc3` → `19cf222`. |
| Screenshot 3 — "Apple Health updates your progress" | HealthKit-auth Profile state | `ProfileView` health-auth row | ✅ delivered |
| Screenshot 4 — "Find what is costing you time" | History drivers + Today drivers (negative-day path) | `HistoryView` weekly net + drivers cards | ✅ delivered |
| Screenshot 5 — "Complete daily longevity quests" | Today's Plan | `TodayView` plan section | ✅ delivered |
| Screenshot 6 — "Track your healthspan trend" | History trajectory + Future projection | `HistoryView` + `FutureView` | ✅ delivered |
| Keywords | longevity, healthspan, habit tracker, Apple Health, life expectancy, wellness, sleep tracker, fitness tracker, self improvement, health score | All terms map to existing in-app features; no removed/renamed feature that would invalidate a keyword | ✅ no drift |
| App Review posture | "Marketing must match the UI. Do not claim medical accuracy or diagnosis." | Every post-Sprint-A–D copy change (PaywallSheet 5 bullets, Profile tone-aware subline, PaywallPrimaryView "richer wrap-up", Pro Perks recap on Profile) checked against this rule | ✅ no medical claims introduced |
| App Review posture | "Keep the app clearly in wellness / fitness / behavior-change territory." | Vision Decided 2026-05-04 "Trajectory, not prophecy" enforced across all copy; no "predict your death" / "you will live X years" claims anywhere | ✅ aligned |

## Findings

**Zero text drift** between ASO copy and post-Sprint-D in-app state. Every claim in `APP_STORE_ASO.md` § Naming / Subtitle / Description / Keywords / App Review posture is still delivered by a current source-tree surface, and no Sprint-A-through-D copy change introduces a claim that the app cannot deliver.

**Two operator-side actions surfaced:**

1. **Regenerate Screenshot 1 (Today)** — if the screenshot pre-dates Sprint B1 (commit `14205c6`), it lacks the visible `cardLighting()` lift on the 6 Today cards. Subtle but a reviewer comparing the screenshot against the actual app will notice the depth difference.
2. **Regenerate Screenshot 2 (Earn time / quest-completion)** — Decided 2026-05-13 layered the quest-completion payoff (A mascot pulse + B clock-hand advance + C tone-aware micro-copy). If Screenshot 2 captures the pre-2026-05-09 quest-completion behavior, it shows the old single-card payoff rather than the new layered moment. The new visual IS the screenshot 2 sell.

Operator action: rerun the App Store screenshot capture pipeline against branch `claude/thirsty-golick-bf34df` HEAD (or `main` after merge). All other screenshots (3, 4, 5, 6) are post-Sprint-D-compatible at the surface level — no UI breaking changes that would invalidate them.

## What was NOT checked

- **Paywall screenshot in App Store Connect** — separate from ASO.md. If a paywall screenshot is uploaded to ASC, it needs regeneration after Sprint A1 ("Save ~48%" badge + "$4.17 / month equivalent" caption) and Sprint C2 ("Pro adds depth:" subhead + 5 verbatim bullets) and Sprint D3 (PaywallPrimaryView body copy fix). This audit walks `APP_STORE_ASO.md` only — separate doc covers paywall screenshot in `paywall-spec.md`.
- **Localized ASO copy** — v1 is English-only per founder pack; no other localizations to drift-check.

## Cross-references

- [APP_STORE_ASO.md](APP_STORE_ASO.md) — the ratchet target (unchanged by this audit)
- [pro-value-backlog-2026-05-13-standard.md § P7](pro-value-backlog-2026-05-13-standard.md) — the audit prompt
- [pro-value-rule.md § Value-claim accuracy](pro-value-rule.md) — the rubric
- [smoke-test-2026-05-13.md](smoke-test-2026-05-13.md) — the underlying state verification
- Sprint commits walked: `82d12cf`, `0840154`, `4769742`, `81eee24`, `a8c8bcd`, `7ebee94`, `b65099a`
