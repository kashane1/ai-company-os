# Life Clock — Founder Brief

> One-pager. For partners / investors / new collaborators who need the shape in 60 seconds. For the canonical product story, see [`EXECUTIVE_SUMMARY.md`](EXECUTIVE_SUMMARY.md). For the operating ledger of decisions, see [`vision.md`](vision.md).

## What it is

Life Clock is an iPhone-first Health & Fitness app that translates daily behavior into the most intuitive unit possible: **time**. Apple Health + a transparent rules engine compute "today's habits moved your projected healthspan by ±N minutes" — not a death-date prediction, an agency-led trajectory mirror. Three tone modes (gentle / coach / firm-direct) let users pick how dramatic the framing feels.

## Where we are (2026-05-13)

**Pre-TestFlight.** April 28 → May 13 build sprint shipped the full MVP scope plus material additions beyond the original founder-pack plan:

- 4-tab IA (Today / History / Future / Profile) with a ~29-screen reveal-onboarding escalator.
- Two clock engines — `ClockEngine` (additive minutes ledger) + `HealthspanEngine` (years projection with bounded ±5y healthspan dial, 14 coefficients, smoking dominance, +14y cap).
- StoreKit 2 paywall (monthly $7.99 / annual $49.99 / lifetime $129.99) with proven entitlement gates and lifecycle states.
- Local-first SwiftData (V1.7, `cloudKitDatabase: .none`); HealthKit read-only on six core types.
- Sensitive-consent block (PSS-10 perceived stress + UCLA-3 loneliness; vision Q9 Decided 2026-05-12).
- Under-13 hard block in onboarding; 13+ App Store rating (Apple deprecated 12+ in July 2025).
- SafetyNet (988 + Crisis Text Line + hide-the-clock + switch to Gentle tone).
- One opt-in daily reminder, evening-clamped; wrap-ups are pull-not-push.

## Why now

- **Apple Health saturation is real, interpretation is missing.** Step counts and sleep scores live in dashboards no one revisits. Translating them into "what did today do to my time?" creates emotional legibility a single number can't.
- **The category is validated and the leader is over-clinical.** Death Clock: The Life Lab proves willingness to pay at $40–$100 ARPU [S1], but leans on AI/bloodwork/diagnostic framing. There's an opening for a more elegant, more game-like, more App-Store-safe interpretation.
- **Apple's privacy stance is a moat.** Local-first with `cloudKitDatabase: .none` is a credible privacy posture in a category where everyone else collects everything.

## What's distinctive

- **Two-engine math, fully transparent.** `healthspan-coefficients.md` is the single-source-of-truth coefficient table; the engine source matches it line-for-line. No black-box AI.
- **Tone as a first-class concern.** "Drama, not cruelty" is a ratcheted vision constraint. The firm-direct register is opt-in; default is coach; gentle hides the clock entirely. Reveal escalator pulls back on softer registers when the sensitive-consent signal indicates risk (Q9).
- **Wrap-ups are pull-only.** Weekly + yesterday wrap-ups present as in-app sheets on cold-launch, never as push notifications. No re-engagement notifications, period.

## Where to dig in next

| You want to understand… | Read |
|---|---|
| The product story | [`EXECUTIVE_SUMMARY.md`](EXECUTIVE_SUMMARY.md) |
| The decision ledger (what's settled vs open) | [`vision.md`](vision.md) |
| Tab-by-tab spec | [`PRD.md`](PRD.md), [`UX_GAME_LOOP.md`](UX_GAME_LOOP.md) |
| The math | [`CLOCK_MODEL.md`](CLOCK_MODEL.md), [`healthspan-coefficients.md`](healthspan-coefficients.md) |
| The Pro story | [`MONETIZATION.md`](MONETIZATION.md), [`pro-value-rule.md`](pro-value-rule.md) |
| Engineering shape | [`TECHNICAL_ARCHITECTURE.md`](TECHNICAL_ARCHITECTURE.md) |
| Compliance posture | [`PRIVACY_COMPLIANCE.md`](PRIVACY_COMPLIANCE.md), [`AGE_COMPLIANCE.md`](AGE_COMPLIANCE.md), [`legal/`](legal/) |
| What's blocking TestFlight | [`PHASE_STATUS.md`](PHASE_STATUS.md), [`ASC_CHECKLIST.md`](ASC_CHECKLIST.md) |
| Premium-feel + Pro-value gap analysis | [`premium-bar.md`](premium-bar.md), latest `premium-feel-backlog-*.md`, latest `pro-value-backlog-*.md` |

## What's next (next 30 days)

1. Close pro-value submission-blockers (in-app cancel pointer; paywall header rewrite from MONETIZATION § Pro Annual).
2. Land elevation-vocabulary artifacts (`Motion.Duration` enum, extended `Lighting` modifier, shared `LifeClockSpinner` / `EmptyStateView`) from the premium-feel backlog.
3. App Store Connect record + Phase 4 age-rating questionnaire re-run on the 4+/9+/13+/16+/18+ tiers.
4. Fill remaining legal placeholders (publisher name, support email, jurisdiction).
5. TestFlight.

Build by Kashane Brigham. Compound-engineering with Claude Code; orchestration via `ai-company-os` platform.
