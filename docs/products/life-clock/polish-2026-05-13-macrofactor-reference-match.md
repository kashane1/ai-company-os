# MacroFactor — Pro-Value Reference-Match

> **Skill:** none (pro-value-audit follow-through; resolves [pro-value-backlog-2026-05-13-standard.md § P6](pro-value-backlog-2026-05-13-standard.md)).
> **Reference anchor:** [vision.md § References — Decided 2026-05-13](vision.md). Match the craft, reject the model.
> **Source material:** [App Store listing](https://apps.apple.com/us/app/macrofactor-smart-food-logger/id1553503471) (id `1553503471`) — fetched via WebFetch 2026-05-13.
> **In-app comparison:** Life Clock at commit `79a10fe` (post-Sprint-D + Sprint-E close-out + Option-A Pro-perks copy retraction).
> **Capture method:** text-only (App Store description, pricing structure, subtitle, philosophy paragraph). Visual paywall comparison deferred to operator (see § Limitations).
> **Author:** Claude (single-pass synthesis).

---

## Why this reference

MacroFactor is the operator-anchored pro-value reference per `vision.md § References` (Decided 2026-05-13). It sits in the **same App Store category** (Health & Fitness), targets a similarly-disciplined audience (people who want depth, not gamification), and has shipped at a paywall-craft level that the longevity-tracker category aspires to (4.8★ on 14K+ ratings).

The binding rule from `vision.md`:

> **"Match the craft, reject the model."** Life Clock's freemium + no-trial stance is binding; MacroFactor's premium-only / 7-day-trial patterns do not transfer.

This document scores craft we may import and explicitly enumerates the model patterns we will NOT.

## Reference material captured

From the App Store listing (verbatim from `WebFetch 2026-05-13`):

- **Subtitle:** "Calorie, Nutrition, Food, Diet"
- **Description lead:** "combines innovative coaching algorithms with proven nutrition and behavioral science to help users reach diet goals and achieve 'empowering, sustainable results.' The app uses a dynamic algorithm to adapt to metabolic changes and personalize macro plans."
- **Philosophy paragraph (verbatim — high gold value):**
  > *"Unlike other nutrition coach apps, you don't have to eat like a robot or perfectly adhere to your macro targets to receive coaching adjustments. The app avoids 'warnings, red numbers, or shaming' and aims to 'empower you with guidance and tools' without rigidity or stress."*
- **Feature claims (excerpts):**
  - "Energy expenditure calculation that detects metabolism changes"
  - "Smart algorithms personalize calorie and macro targets"
  - "Weekly check-ins track progress"
  - "Fastest macro tracker with barcode scan and custom foods"
  - "Verified food database"
  - "Custom macro programs"
  - "Micronutrient breakdowns"
  - "Period tracker, habit tracker, data insights, dark mode"
  - "Science-backed macro plan for weight loss, maintenance, or gain"
  - "Timeline-style food log without meal restrictions"
  - "Best-in-class expenditure estimate"
  - "Weight Trend insight feature"
  - "Apple Health integration"
- **Pricing (premium-only, no free tier):**
  - $11.99 / month
  - $47.99 / 6 months (≈ $8/mo equivalent)
  - $71.99 / year (≈ $5.99/mo equivalent)
  - Plus a bundle: $89.99 / year (Workouts add-on)
  - Free trial offered (duration not specified in description)
- **Reception:** 4.8 stars / 14,000+ ratings
- **Latest update:** Version 5.7.8, "Improved AI workflows" and "Bug fixes and performance improvements"

## Scoring matrix (3 axes — pro-value-rule.md categories)

### Axis 1 — Justification depth

| Surface | MacroFactor | Life Clock (current) | Gap & importable craft | What we WILL NOT import |
|---|---|---|---|---|
| App Store description | Justifies premium with concrete dimensions: "metabolic adaptation detection," "weekly check-ins," "verified food database," "best-in-class expenditure estimate." Each claim names what the algorithm does, not what the user gets to feel. | Post-Option-A `ProPerks` list: "Full daily history" / "Weekly drivers + next-best lever — the deeper breakdown in History" / "Correction power" / "Custom Today's Plan" / "Deeper trend breakdown — the Future-tab What-If Simulator." Five concrete bullets with title + detail couplet. | MacroFactor's claims read **algorithmic-specific** (what computation runs). Life Clock's read **feature-specific** (what surface unlocks). Both work, but MacroFactor's framing earns trust by being checkable. Ratchet candidate: consider whether one or more Life Clock bullets could be reframed to name the *engine* not the surface — e.g., "Weekly drivers + next-best lever" → could include an algorithmic descriptor like "compound-effect breakdown" if the engine warrants. Low priority. | MacroFactor's claim density (algorithmic precision + scientific positioning). Life Clock's [vision.md § Tone](vision.md) reads "terse over chatty, confident over hedged" — claim-stacking that overpromises clinical precision conflicts with Decided 2026-05-04 "Confidence is shipped, not hidden." |
| Paywall justification copy | (Inferred — App Store description sets the register.) Likely follows the "what Pro adds" + "how the algorithm works" pattern, with feature names paired to outcomes. | PaywallSheet header at `PaywallSheet.swift:117` post-Sprint-A renders title "Unlock the full Life Clock" + subhead "Pro adds depth:" + five `proBullet` rows + footer "Your free experience keeps working either way." Sourced verbatim from `Shared/ProPerks.swift` (single source of truth). | MacroFactor's paywall is the *justification*; Life Clock's PaywallSheet header is similarly structured + matches via the verbatim-from-MONETIZATION pattern shipped in commit `82d12cf`. **No ratchet needed here.** Sprint A2 + Sprint C2 + Sprint E close-out already brought Life Clock's paywall to this bar. | None — Life Clock's paywall justification is now structurally at parity. |

### Axis 2 — Pricing presentation

| Element | MacroFactor | Life Clock (current) | Gap & importable craft | What we WILL NOT import |
|---|---|---|---|---|
| Tier ladder | 3 visible SKUs ($11.99/$47.99/$71.99) + bundle add-on. Annual is the value-anchor at ≈$5.99/mo equivalent. | 3 SKUs per [MONETIZATION.md § As shipped](MONETIZATION.md): monthly $7.99 / annual $49.99 / lifetime $129.99. Annual pre-selected per Sprint A1 + the equal-prominence guard. | MacroFactor has 6-month *as a middle tier*. Life Clock skips the 6-month and offers lifetime instead. Both are valid v1 ladders; the 3-SKU shape is correct. **No ratchet.** The Sprint A1 "Save ~48%" badge + "$4.17 / month equivalent" caption already match MacroFactor's annual-anchoring craft. | MacroFactor's 6-month tier. Adding it would fragment the SKU set + dilute annual-first per Decided 2026-05-04. Life Clock's lifetime tier serves the "anti-subscription user" + "indie trust" purposes the 6-month would in MacroFactor's model. |
| Trial framing | Free trial offered (length not specified in App Store description; reviews + ASC mention 7-day on annual). Trial is *the* on-ramp to the premium-only model. | No trial in v1 per [MONETIZATION.md § Trial stance](MONETIZATION.md). `Products.storekit` has `"introductoryOffer": null` for both subscriptions; paywall does not claim a trial. | **NOT a gap.** Vision Decided constraint + MONETIZATION.md's explicit rationale (any trial claim must be backed by an ASC provisioned offer; mismatched trial language is an App Review rejection vector). MacroFactor's premium-only model makes the trial essential; Life Clock's freemium model already gives the user "first value" without a trial commitment. | A trial that isn't backed by an ASC introductory offer. Any "Try Pro free" CTA without the matching StoreKit configuration. The premium-only conversion funnel that makes a trial necessary in the first place. |
| Pricing presentation craft | Per-month-equivalent computation displayed on multi-month tiers ($5.99/mo on annual). Annual is anchored visually. | Sprint A1 shipped "Save ~48%" badge on annual + "$4.17 / month equivalent" caption under "Auto-renews yearly". Math verified: $49.99/12 = $4.17 (rounding correct); 47.86% savings vs $7.99×12 (rounded to ~48% display). Best-value badge on lifetime per smoke-test. | Life Clock's pricing-clarity craft is **at or above MacroFactor's** as of Sprint A1. No ratchet needed. | None. |

### Axis 3 — Adherence-neutral copy register

| Surface | MacroFactor | Life Clock (current) | Gap & importable craft | What we WILL NOT import |
|---|---|---|---|---|
| Philosophy framing | Verbatim from description: **"Unlike other nutrition coach apps, you don't have to eat like a robot or perfectly adhere to your macro targets to receive coaching adjustments. The app avoids 'warnings, red numbers, or shaming' and aims to 'empower you with guidance and tools' without rigidity or stress."** This is **the gold-standard adherence-neutral register** for the longevity / health-behavior category. | [vision.md § Tone](vision.md): "Default: motivating, elegant, direct, slightly dramatic." Decided 2026-05-04: "Default is motivating, not punishing. Drama is allowed; cruelty is not." Decided 2026-05-07/2026-05-10 (Q1 bad-day pools): "Drama-not-cruelty applies in BOTH directions: firmDirect must not accuse, gentle must not platitude, coach must not presuppose adherence on a negative day." | Life Clock's adherence-neutral framing is **already at parity** with MacroFactor's, expressed differently (drama-not-cruelty rule for Life Clock; rigidity-and-stress refusal for MacroFactor). Both reject shaming; both keep the engine empathetic. **No ratchet needed in vision.** Ratchet candidate at the *surface* level: review whether any in-app copy currently uses "warning," "red numbers," "should," "failed," etc. — these are MacroFactor's explicit reject list and good antagonists to grep for. Quick win check below. | MacroFactor's specific phrasings ("empowering, sustainable results," "without rigidity or stress") — these are MacroFactor's voice. Life Clock's voice is "earn time" + the three tone modes; copying register words from MacroFactor would dilute the time-currency framing. |
| Negative-day handling | Inferred from philosophy paragraph + reviews: MacroFactor's algorithm rebases targets on what the user actually did, not what they should have done — algorithmic forgiveness. | Bad-day pools per polish-2026-05-10 + Decided 2026-05-06 (calendar-month count, no streak resets). Drama-not-cruelty rule across all three tones. Quest-completion payoff (Decided 2026-05-13) layered A+B+C — celebrates without shaming the absent. | MacroFactor's craft: the *algorithm itself* is forgiving (rebase on actuals). Life Clock's craft: the *copy + the streak design* is forgiving. Both valid — Life Clock can't import the rebase-on-actuals pattern (its engine doesn't have a target-vs-actual loop — the engine reads passive HealthKit + manual logs and projects trajectory). **No ratchet possible here**; orthogonal model. | The "rebase-on-actuals" target adjustment pattern (Life Clock doesn't have targets). Any "you fell short" / "you missed your goal" language — alien to Life Clock's no-targets vision. |

### Quick grep: anti-signal antagonists from MacroFactor's reject list

```
"warning|should|red number|fail|fell short" in products/life-clock-ios/Sources/**/*.swift (case-insensitive)
```

Recommended as a one-shot follow-up grep before App Store submission — verify the binding adherence-neutral register holds at the leaf-string level. Not run in this audit because the audit is read-only-against-rubrics; can be run in a focused polish session if the operator wants a clean confirmation.

## Concrete ratchet recommendations

Three changes worth scoping. None requires source change in *this* prompt — recommendations feed into specific simulator-driven-polish or pricing-doc sessions.

### 1. Verify Pro perks list reads with MacroFactor-style claim density (Polish-tier check)

Compare the post-Option-A `ProPerks` list against MacroFactor's claim style:

- **MacroFactor:** algorithmic-specific ("smart algorithms personalize calorie and macro targets") — names the computation.
- **Life Clock:** surface-specific ("Weekly drivers + next-best lever — the deeper breakdown in History") — names the destination.

Both are legitimate. The recommendation: **hold the surface-specific framing** because it matches Life Clock's "trajectory, not prediction" vision (we don't promise the engine is doing something smarter than it is). The claim-density check is a thumbs-up, not a thumbs-down. Logged as a deliberate non-ratchet.

### 2. Anti-signal-antagonist sweep (Polish-tier)

Run the grep above and verify zero residual instances of "warning," "should," "failed," "fell short," "red," "missed target," etc. in user-facing copy. MacroFactor's reject list is a useful antagonist set even if Life Clock's vision arrived at the same place via a different path.

Scope: 10-minute grep + any remediation. Operator gate: no (mechanical cleanup).

### 3. Review trial-language hygiene before submission (Submission-blocker-adjacent)

MacroFactor's trial offer is structurally essential to its premium-only model. Life Clock's vision is to NOT have a trial in v1 (Decided + MONETIZATION.md). Pre-submission, grep for any residual "trial" / "try free" / "introductory offer" language in `products/life-clock-ios/Sources/**/*.swift`:

- If ZERO results: clean; no action.
- If any results: each must either (a) be conditional on actual ASC trial provisioning + verified to render only when the offer is active, or (b) be removed.

This is in the spirit of MacroFactor's discipline — MacroFactor *uses* trial language because it has the trial; Life Clock *doesn't have the trial*, so it can't use the language. Both sides of the rule are equally important.

Scope: 5-minute grep + removal of any residuals. Operator gate: yes (touches paywall copy).

## What we are NOT importing

Binding reject-list (each maps to a `vision.md` Decided constraint or `MONETIZATION.md` rule):

1. **Premium-only no-free-tier model.** MacroFactor's "no free tier ever" is rejected by vision Decided 2026-05-04 ("Free tier is real, not crippled") + [MONETIZATION.md § Free](MONETIZATION.md). Life Clock's free tier — Today + basic HK import + 1-3 quests + 7-day trend — is permanent.
2. **7-day trial as the on-ramp.** Rejected by [MONETIZATION.md § Trial stance](MONETIZATION.md). v1 ships without an introductory trial because trial language must be backed by an ASC offer; v1 doesn't have one provisioned. Revisit post-launch with analytics.
3. **6-month middle SKU.** Rejected by Decided 2026-05-04 ("Annual-first pricing"). 3-SKU ladder (monthly / annual / lifetime) is the right shape; adding 6-month dilutes annual.
4. **Algorithmic-specific claim density.** MacroFactor's claims name the algorithm; Life Clock's claims name the surface. Decided 2026-05-04 ("Confidence is shipped, not hidden") + "Trajectory, not prophecy" both lean toward surface-naming over engine-naming. We don't claim the engine is doing something smarter than it can defend.
5. **MacroFactor's specific phrasings.** "Empowering, sustainable results" / "without rigidity or stress" / "energy expenditure calculation" are MacroFactor's voice. Life Clock's voice is "earn time" + tone-aware drama-not-cruelty. Importing phrasings dilutes brand voice (vision Decided 2026-05-11 onboarding lead-in voice is "earn time" — not interchangeable).
6. **Target-vs-actual macro-style coaching adjustments.** Life Clock has no daily targets to miss. Decided 2026-05-04 ("Passive first, manual second" — HealthKit is the trunk, not a target the user has to hit).
7. **"Period tracker" / "Workouts" bundle add-ons.** MacroFactor's bundle SKU is feature-add-on monetization; Life Clock's vision is single-product-per-tier (per `MONETIZATION.md § Pricing`). v1.1+ feature adds — like advanced HealthKit metrics or widgets — are bundled into the existing Pro tier, not sold as separate add-ons.

## Limitations of this audit

- **Text-only capture.** Visual side-by-side captures of the MacroFactor paywall would be a stronger comparison. Recommended operator follow-up: capture MacroFactor's paywall (App Store preview video should include it) + Life Clock's PaywallSheet under `LIFECLOCK_FORCE_PAYWALL=1` + Life Clock's PaywallPrimaryView under `LIFECLOCK_UI_TEST_SCENARIO=onboarding`. Save under `docs/products/life-clock/research/macrofactor-2026-05-13/<side>.png`.
- **Trial mechanics not visible in description.** Whether MacroFactor's trial is 7-day on annual specifically (vs another length), what conversion behavior the trial-end screen shows, and how the trial is messaged on the paywall itself are not extractable from text. Direct App Store viewing recommended for operator-side hygiene check.
- **Pricing UX presentation inferred.** Whether MacroFactor's 3 SKUs are presented as a row/grid/table is not extractable from the App Store description.

These limitations don't invalidate the model-reject guardrails (§ "What we are NOT importing") — those derive from Decided constraints and MONETIZATION.md rules and are binding regardless of capture fidelity. The 3 ratchet recommendations also stand.

## Cross-references

- [pro-value-backlog-2026-05-13-standard.md § P6](pro-value-backlog-2026-05-13-standard.md) — the audit prompt
- [pro-value-rule.md § Justification + § Perceived depth + § Friction-to-trial + § Trust](pro-value-rule.md) — the rubric axes scored here
- [vision.md § References — Decided 2026-05-13](vision.md) — the binding reference anchor + reject rule
- [vision.md § Decided constraints § Monetization](vision.md) — "Annual-first pricing" + "Free tier is real, not crippled"
- [MONETIZATION.md § As shipped](MONETIZATION.md) — the binding pricing source-of-truth
- [MONETIZATION.md § Trial stance](MONETIZATION.md) — the no-trial-in-v1 rationale
- [reference-apps.md](reference-apps.md) — operator-side reference doc
- [Shared/ProPerks.swift](../../../products/life-clock-ios/Sources/Shared/ProPerks.swift) — single source of truth for Pro feature claims, post-Option-A
- [polish-2026-05-13-wrapup-pro-depth-decision.md](polish-2026-05-13-wrapup-pro-depth-decision.md) — Option A retraction context
- Source: [MacroFactor on the App Store](https://apps.apple.com/us/app/macrofactor-smart-food-logger/id1553503471)
