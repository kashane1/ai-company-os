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

- Starting Life Clock and onboarding reveal
- Basic Apple Health import (steps, exercise minutes, active energy, resting heart rate, sleep, body mass)
- Today's time delta and tone-aware framing
- 1–3 Today's Plan actions per day, auto-generated from your activity
- Recent History view (a few days; older rows paywall-fogged) and weekly net delta
- Yesterday + weekly wrap-ups (in-app sheets on cold-launch; pull-only, never push)
- QuickLog manual logging
- Tone modes (gentle / coach / firmDirect) and palette pickers
- Enough context to understand the current trajectory without paying

### Pro Annual

Recommended range: **$39.99–$59.99/year**. **As shipped: $49.99/year.** See [§ As shipped](#as-shipped-2026-05) below.

Unlocks (v1, shipped):

- **Full daily history** — every past day, drillable in History
- **Weekly drivers + next-best lever** — the deeper weekly breakdown in History
- **Correction power** — override imported Apple Health values you know are wrong
- **Custom Today's Plan** — pick the daily-plan actions that fit your life (Plan Editor)
- **Deeper trend breakdown** — what's actually shaping your trajectory, including the Future-tab What-If Simulator

Planned (post-v1; do not promise on the paywall as shipped Pro value):

- Advanced HealthKit metrics _(v1.1 — currently no concrete advanced-HK deliverable beyond basic reads)_
- Widgets / Lock Screen surfaces _(v1.2 — no WidgetKit target in v1)_
- AI meal/photo summaries _(v2+)_

### Pro Monthly

Recommended range: **$7.99–$9.99/month**. **As shipped: $7.99/month.**

Useful for users who resist annual pricing or want to evaluate Pro before committing.

### Lifetime

Recommended range: **$99.99–$149.99**. **As shipped: $129.99 one-time.**

Good for indie trust and anti-subscription users.

## As shipped (2026-05)

The shipped SKUs in `products/life-clock-ios/Sources/Services/Products.storekit`:

- `com.lifeclock.pro.monthly` — **$7.99 / month**
- `com.lifeclock.pro.annual` — **$49.99 / year**
- `com.lifeclock.pro.lifetime` — **$129.99 one-time**

Founding-offer introductory pricing on `pro.annual` for new subscribers is still pending in App Store Connect (see `PHASE_STATUS.md`). All other strategy docs that quote pricing should link to this section rather than restate the recommended ranges.

## Paywall timing

Do not show a hard paywall before first value.

Best conversion moments:

1. After first Life Clock reveal. **Wired** (onboarding terminal `PaywallPrimaryView`).
2. After the user taps a locked detailed driver breakdown. **Wired** (History fog stack + Future-tab What-If slider locked thumb).
3. After the first weekly wrap-up preview. **Planned** — currently the WrapUpSheet has no Pro signal; see Pro-value backlog (2026-05-12) Prompt 3.
4. When the user wants advanced HealthKit metrics. **Deferred to v1.1** — no concrete advanced-HK deliverable in v1.
5. When the user wants widget / Lock Screen surfaces. **Deferred to v1.2** — widgets not in launch build.

## Trial stance

**v1 ships without an introductory trial.** `Products.storekit` has `"introductoryOffer": null` for both monthly and annual subscriptions, and the paywall does not claim a trial. This is deliberate: any trial language in paywall copy that isn't backed by an actual App Store Connect introductory offer is a value-claim mismatch and an App Review rejection vector.

Provisioning a 7-day annual trial in App Store Connect — and updating `PaywallSheet` / `PaywallPrimaryView` to surface it — is on the v1.1 candidate list; the call depends on analytics from the trial-free launch. A confusing 3-day trial is rejected.

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
