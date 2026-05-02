> Source: Life Clock Founder Pack (2026-04-27). Normalized for platform use.

# Monetization Strategy

## Recommendation

Use a Health & Fitness freemium subscription model with annual-first pricing and optional lifetime.

RevenueCat's 2026 subscription benchmarks emphasize that yearly subscriptions retain materially better than weekly and monthly subscriptions, while weekly plans have very weak long-term retention [S2]. This product should avoid weekly pricing.

## Free vs Pro Rule

Use this as the default decision rule whenever a feature could land in either tier:

- **Free = understanding**
- **Pro = depth, archive, and correction power**

Interpretation:

- Free should always let the user understand what happened today, what happened yesterday, and whether this week moved in a good or bad direction.
- Free should include the emotional core, basic trust-building, and enough context for the app to feel genuinely useful on its own.
- Pro should unlock richer breakdowns, longer history, deeper reflection, and the ability to correct or refine the model when the user cares enough to go beyond the default experience.
- Pro should almost never gate the first meaningful answer. It should gate depth, continuity, customization, and recovery/control.

Practical tests for future decisions:

- If removing the feature would make the app feel confusing or emotionally empty, it probably belongs in Free.
- If the feature helps the user revisit, audit, compare, or correct past information, it probably belongs in Pro.
- If the feature is required for trust in the basic daily loop, it belongs in Free.
- If the feature rewards power users who want more history, more explanation, or more control, it belongs in Pro.

## Pricing

### Free

- starting Life Clock
- basic HealthKit import
- today's time delta
- 3 daily quests
- 7-day trend
- basic manual habits
- enough context to understand the current trajectory without paying

### Pro Annual

Recommended: **$39.99-$59.99/year**

Unlocks:

- full time ledger
- advanced HealthKit metrics
- weekly reports
- historical archive and richer wrap-ups
- correction power through app-level overrides of past imported values
- custom quests
- deeper trend breakdown
- widgets / Lock Screen surfaces
- export/delete controls
- AI meal/photo summaries later

### Pro Monthly

Recommended: **$7.99-$9.99/month**

Useful for trial-conversion users who resist annual pricing.

### Lifetime

Recommended: **$99.99-$149.99**

Good for indie trust and anti-subscription users.

## Paywall timing

Do not show a hard paywall before first value.

Best conversion moments:

1. After first Life Clock reveal.
2. After the user taps locked detailed driver breakdown.
3. After the first weekly report preview.
4. When the user wants advanced HealthKit metrics.
5. When the user wants widget/Lock Screen surfaces.

## Trial stance

Use a 7-day trial on annual if the app has enough immediate value. Avoid a confusing 3-day trial unless analytics later prove it.

## What not to monetize in v1

- basic Apple Health import
- basic clock
- privacy/export/delete
- safety disclaimers
- basic logging

## Business logic

The clock is the activation hook. The weekly report is the retention hook. Pro should unlock deeper clarity and personalization, not block the emotional core.

Current implementation note:

- Tone modes are part of the free core experience.
- Weekly net delta stays free; deeper weekly breakdown sits behind Pro.

History/wrap-up note:

- Free should get the first meaningful reflection layer: yesterday understanding and a weekly preview.
- Pro should get browsing depth, archive access, and correction power over imported historical days.
