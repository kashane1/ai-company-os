> Source: Life Clock Founder Pack (2026-04-27). Normalized for platform use.

# Executive Summary

## Working title

**Life Clock** is the resolved working name.

- App Store listing name: **"Life Clock: habits earn time"**
- In-app display name (`CFBundleDisplayName`): **"Life Clock"**
- Tagline (`LifeClockConfiguration.appTagline`): **"Habits earn time."**

See `APP_STORE_ASO.md` § Current implementation note for the canonical three-string set, and `PHASE_STATUS.md` "Resolved decisions" for the operator ratchet. Original April 2026 brand candidates retained below for repositioning reference only: TimeBack, Long Game, DayBank, Clockwise, Healthspan Quest.

## Concept

Life Clock is an iPhone-first Health & Fitness app where daily behavior moves a user's projected life trajectory. Instead of presenting a fixed death date, the app turns healthspan into a game: sleep, movement, workouts, nutrition, stress, alcohol, smoking, and consistency can add or subtract time from a visible clock.

## Wedge

**Earn time with better daily habits.**

This is more defensible and App Store-safe than "predict your death date." The app can still have a dramatic clock, but the product promise should be agency-based: your trajectory changes as your behavior changes. The in-app voice uses the forward-looking "earn time" phrasing (vision Decided constraint 2026-05-11); the earlier "earn time back" framing was dropped because the "back" register read as recovering-lost-time. Marketing copy aligns to the in-app voice.

## Why this is worth building

There is direct demand for the concept. Death Clock: The Life Lab is a Health & Fitness app with approximately 15K ratings at 4.8 and membership IAPs ranging roughly from $39.99 to $99.99, plus higher-ticket baseline options [S1]. That validates user curiosity and willingness to pay, but it also means a generic "death clock" app is no longer novel.

The opening is to build a more elegant, less medically risky, more game-like, Apple-native version focused on daily behavior change.

## Category recommendation

Primary App Store category: **Health & Fitness**.

Secondary positioning: **Lifestyle / habit formation / quantified self**.

Do not use Games as the primary category. The game mechanic is the retention layer; the buyer intent is health improvement.

## Founder recommendation

Build this as a **HealthKit-powered longevity game**, not a clinical longevity app and not a literal death prediction oracle.

## MVP promise

"Connect Apple Health. See today's time delta. Build a daily plan that earns time."

## MVP loop

1. User completes a short baseline (DOB with under-13 hard block, sex, body composition, smoking/alcohol/cardio/strength/sleep/diet, PSS-10 + UCLA-3 sensitive consent).
2. User grants Apple Health permissions in a single in-context sheet (six core types).
3. App calculates a starting Life Clock + healthspan projection with confidence; user sets a one-time ±5y healthspan dial.
4. Each day, passive HealthKit data and QuickLog manual inputs update the clock.
5. Today surfaces the signed delta + the top drivers ("Why it changed") + a rescue line on negative days.
6. Today's Plan suggests 1-3 supportive actions for the day (`Today` tab — not a separate quests tab).
7. A weekly wrap-up sheet (in-app, presents on Monday cold-launch via `WrapUpCoordinator`) summarizes the week's net delta and the next habit to lever; History weekly cards persist the same content for browsing. See `PHASE_STATUS.md` for shipped surfaces.

## What v1 should not do

- Do not claim to know the user's real death date.
- Do not provide diagnosis or treatment advice.
- Do not interpret bloodwork in v1.
- Do not build a calorie database in v1.
- Do not sell ads or use HealthKit data for advertising.
- Do not require every HealthKit permission on first launch.
- Do not make the app emotionally punitive by default.

## Initial monetization

Use freemium with an annual-first subscription. See [`MONETIZATION.md`](MONETIZATION.md) for the canonical Free/Pro rule, the full feature split, "best conversion moments" wiring status, and the actual shipped SKU prices.

Shipped SKUs (`MONETIZATION.md` § As shipped):

- **Free** — starting Life Clock + baseline Apple Health import + Today + Today's Plan (1-3 actions) + recent History + Yesterday/Weekly wrap-ups + QuickLog + tone modes
- **Pro Monthly** — $7.99 / month (`com.lifeclock.pro.monthly`)
- **Pro Annual** — $49.99 / year (`com.lifeclock.pro.annual`)
- **Lifetime** — $129.99 one-time (`com.lifeclock.pro.lifetime`)

v1 ships without an introductory trial (`Products.storekit` has `introductoryOffer: null` for both subscriptions); a 7-day annual trial is a v1.1 candidate. Avoid weekly pricing. RevenueCat's 2026 benchmark highlights materially stronger retention for yearly plans versus weekly/monthly plans, and Health & Fitness is a category where annual plans can support better long-term economics [S2].
