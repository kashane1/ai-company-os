# Life Clock — Product Docs

> Source: Life Clock Founder Pack (2026-04-27). Normalized for platform use on 2026-04-27.

Life Clock is an iPhone-first Health & Fitness app where daily behavior moves the user's projected healthspan trajectory. Wedge: **earn time back with better daily habits.** Not a death predictor, not a clinical longevity tool.

## Status

- **Phase:** pre-TestFlight
- **App Store name:** `Life Clock: habits earn time`
- **Primary App Store category:** Health & Fitness
- **Platform:** iOS 17+ (iPhone-first, iPad supported via SwiftUI adaptive layout)
- **Source tree:** `products/life-clock-ios/`

See `PHASE_STATUS.md` for current phase and next decisions.

## Read order

For the founder-level pitch:

1. `EXECUTIVE_SUMMARY.md`
2. `PRODUCT_STRATEGY.md`
3. `PRD.md`

For the implementer:

1. `EXECUTIVE_SUMMARY.md`
2. `PRD.md`
3. `HEALTH_DATA_STRATEGY.md`
4. `CLOCK_MODEL.md`
5. `UX_GAME_LOOP.md`
6. `PRIVACY_COMPLIANCE.md`
7. `TECHNICAL_ARCHITECTURE.md`
8. `CODEX_BUILD_PROMPT.md`

For consolidated reading:

- `MASTER_FOUNDER_PACKAGE.md` — single-file copy of the entire founder pack.

## Files

| File | Purpose |
|---|---|
| `EXECUTIVE_SUMMARY.md` | Founder-level summary and recommendation |
| `BUSINESS_PLAN.md` | Market, customer, positioning, monetization thesis |
| `PRODUCT_STRATEGY.md` | Wedge, principles, category, what it is / is not |
| `PRD.md` | Product requirements and MVP scope |
| `HEALTH_DATA_STRATEGY.md` | Apple Health + manual input plan |
| `CLOCK_MODEL.md` | Scoring rules, confidence system, safety bounds |
| `UX_GAME_LOOP.md` | Screens, daily loop, quests, tone controls |
| `MONETIZATION.md` | Paywall, pricing, conversion moments |
| `APP_STORE_ASO.md` | Category, name options, screenshot copy |
| `PRIVACY_COMPLIANCE.md` | HealthKit, App Review, disclaimers, data posture |
| `GTM_LAUNCH_PLAN.md` | Beta, launch channels, 90-day plan |
| `ROADMAP_METRICS.md` | Phased roadmap and success metrics |
| `TECHNICAL_ARCHITECTURE.md` | iOS architecture and data model |
| `CODEX_BUILD_PROMPT.md` | Paste-ready prompt for first implementation pass |
| `OPEN_QUESTIONS.md` | Decisions to resolve before submission |
| `SOURCES.md` | Citation appendix |
| `MASTER_FOUNDER_PACKAGE.md` | Consolidated single-file copy |
| `PHASE_STATUS.md` | Current phase + next decisions (platform-native) |

## Scope guardrails

- **Do not** claim to know a real death date.
- **Do not** provide diagnosis or treatment advice.
- **Do not** sell HealthKit data or use it for advertising.
- **Do not** require every HealthKit permission on first launch.
- **Do not** make the app emotionally punitive by default.
- Local-first SwiftData. No backend in v1.

## Current product reality

The founder pack remains the strategy source, but the app has moved beyond the original MVP skeleton. As of 2026-04-30 the shipped code includes:

- Live Apple Health reads for steps, exercise, sleep, resting heart rate, active energy, and weight.
- Local SwiftData persistence for profile, quests, check-ins, ledger entries, and weekly summaries.
- StoreKit 2 subscriptions for monthly, annual, and lifetime Pro access.
- A Daily Check-In flow, daily reminder scheduling, a Safety Net screen, and multiple color palettes.
- Two tone modes (`gentle`, `coach`). The earlier mortality-forward third mode was removed in the 2026-04-30 UX pass.

## Related platform docs

- Plan: `docs/plans/2026-04-27-002-feat-life-clock-ios-mvp-skeleton-plan.md`
- Source: `products/life-clock-ios/`
- Closest analog: `docs/products/after-plans/`, `products/after-plans-ios/`
