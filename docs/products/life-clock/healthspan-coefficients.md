# Healthspan modelling note

**Type:** modelling spec (not clinical)
**Status:** v0 — `TODO: refine after beta`
**Owner of code:** `products/life-clock-ios/Sources/Engines/HealthspanEngine.swift`
**Authored:** 2026-05-11
**Plan reference:** [docs/plans/2026-05-11-feat-future-tab-history-summary-plan.md](../../plans/2026-05-11-feat-future-tab-history-summary-plan.md) §Phase 0

## What this is

The numerical choices behind the Future-tab projection. Each dimension is one slider; each slider maps a personal-current 14-day rolling value to a healthspan delta in years. This doc is the human-readable record of *why we picked the numbers*; the numbers themselves live inline as `private let` constants in `HealthspanEngine.swift` with `// Source: <citation>` comments.

This is a modelling tool for a what-if slider, not a clinical decision aid. The Decided constraint *trajectory not prophecy, confidence shipped* applies. Every coefficient is approximate; every projection is bounded.

## The output

`HealthspanEngine.currentProjection(snapshots:, habits:, baseline:, clock:)` returns

```
Projection {
    healthspanYears: Double   // baseline + sum-of-dimension-deltas, clamped
    confidence: Double         // 0..1, scaled by sample density
    perDimensionDelta: [Dimension: Double]  // for narrative attribution
}
```

The headline number the user sees is `healthspanYears`. The chart reads from `weeklyTrajectory`. Cap and floor are applied at the engine layer; the UI never sees an unclamped value.

## Dimensions

Six. The slider rows in `WhatIfSlider`. Each has a coefficient that turns a per-week value (or per-day, where natural) into a years-of-healthspan delta. Each coefficient is paired with a soft per-dimension cap so a single lever cannot dominate the projection.

| Dim | Personal anchor (per `WhatIfSlider`) | Max benefit (years) | Max drag (years) | Curve | Why |
|---|---|---|---|---|---|
| `sleep` | 14-day avg hours/night | +1.5 | −2.0 | U-curve, optimum 7–8h | Cai 2025 GeroScience 79-cohort meta — both <6h and >9h elevate mortality. Asymmetric: too-little is more punitive than too-much. |
| `dietQuality` | days/wk with whole-food meal | +2.5 | 0 (no penalty below 0) | linear, saturates at 5 days/wk | Mediterranean diet, JAMA Net Open 2024 — +4 to +9y at high adherence (we take the conservative lower end and split across two surfaces). |
| `steps` | 14-day avg steps/day | +3.0 | −1.5 | log-linear, plateau at 10k | Paluch 2022 Lancet PH — HR 0.47 at 8–10k vs <4k. Stops earning past 10k. |
| `exerciseMinutes` | 14-day weekly MVPA total | +2.0 | 0 | linear, saturates at 300 min/wk | Moore 2012 PLOS Med — +3.4y at 150–300 min/wk MVPA. We take roughly 60% of the literature mid because exercise overlaps with `steps`. |
| `extras` | alcohol-or-sweets days/wk | 0 | −2.5 | linear from 3+ days/wk | GBD 2020 Lancet 2022 + WHO 2023 — no safe level; we treat extras as drag-only. Below 3 days/wk is the resting baseline (no benefit, no penalty). |
| `nicotine` | smoking/vaping days/wk | 0 | **dominant** | step at >0 days/wk | Jha 2013 NEJM — quit-by-40 +10y; any nicotine use caps the projection (see Smoking dominance below). |

**Sum of max benefits:** +9.0y. **Sum of max drags:** −6.0y (excluding nicotine which dominates differently). The cap at +14y from baseline absorbs the upside; the floor at `max(currentAge+1, demographicFloor)` absorbs the downside.

Citations live as inline comments in `HealthspanEngine.swift`:

```swift
// Source: Cai 2025 GeroScience, sleep U-curve, 79-cohort meta
private let sleepOptimumHours: Double = 7.5
private let sleepMaxBenefitYears: Double = 1.5
private let sleepMaxDragYears: Double = -2.0
```

`TODO: refine after beta` — the coefficients above are first-pass. Telemetry-driven calibration (see Future considerations in the plan) feeds back here.

## Cap and floor

```
projection = clamp(baseline + sum(perDimDeltas), floor, cap)

cap   = baseline + 14.0
floor = max(profile.currentAge + 1.0, demographicFloor(for: profile))
```

- **Cap.** +14y above baseline — Li 2018 Circulation ceiling from 5 healthy lifestyle factors at age 50. We use the same ceiling regardless of baseline age (conservative for older users, generous for younger).
- **Floor.** Whichever is larger: `currentAge + 1` (the slider can never project death) or a demographic-floor lookup. For v1, `demographicFloor` returns `currentAge + 1` flat — i.e. floor = `currentAge + 1`. Demographic refinement deferred (`TODO: refine after beta`).
- **Near-cap chart compression.** When projection is within 2y of cap, the chart's Y-domain compresses to `[projection − 5, cap]` and surfaces `Near projection ceiling — chart compressed.`. Prevents an age-80 user with all-max sliders from seeing a visually flat chart.

Display strings for cap/floor are single neutral strings (no per-tone variants):

- Cap: `Projection capped at 105 years.`
- Floor: `Projection at minimum.`

Both are rendered inline next to the projection number; no separate explainer view.

## Smoking dominance

Nicotine is non-linear. The math:

```swift
if smokingDaysPerWeek > 0 {
    perDimensionDelta[.nicotine] = -10.0   // dominates
    perDimensionDelta[other dims] = each scaled by 0.3
} else {
    perDimensionDelta[.nicotine] = 0
}
```

Effect: any positive smoking value caps the achievable projection regardless of every other lever. The slider can move, the other deltas compute, but the projection sits well below baseline until smoking drops to zero. Mirrors the literature: smoking is by far the dominant single lever, and modelling it linearly would mislead users into thinking sleep gains can offset smoking.

`TODO: refine after beta` — the 0.3 scaling factor is a first-pass guess; the qualitative shape (smoking dominates, others muted) is the load-bearing decision.

## Confidence scaling

The `confidence` field returned by `currentProjection` scales the chart line opacity and the narrative's hedging language:

```
confidence = min(1.0, sampleDays / 14.0)
```

Where `sampleDays` is the count of days in the last 14 with at least one HK or QuickLog signal across any dimension. At `sampleDays >= 14`, full confidence (opacity 1.0). At `sampleDays <= 3`, fades to 0.4. The narrative engine reads `confidence` to choose between firm and hedged phrasing.

`TODO: refine after beta` — sample-density may need to be per-dimension rather than aggregate; will know after we see real beta data shapes.

## Per-dimension attribution (for narrative)

`perDimensionDelta` powers the free narrative line (`<Lever> has been your strongest lever…`) and the Pro long-form. Attribution is the absolute value of each dimension's delta, sorted desc. The top entry is the "dominant driver"; bottom entries are "drags" if negative.

This is mechanical, not statistical — we don't claim causation, just "this dimension contributed N% of your delta." The narrative copy frames it accordingly (`been your strongest lever`, not `caused your healthspan to rise`).

## What this doc deliberately does not do

- **Cite at peer-reviewed-paper rigor.** Each coefficient gets one rationale sentence; the citations are inline in code. A user disputing the numbers should be answered with "we'll refine from beta data," not with a literature defense.
- **Distinguish HALE vs LE vs DALY.** v1 conflates healthspan with healthy-life-expectancy. The chart is honest enough about uncertainty (`Updated daily from your last 14 days`, cap copy, confidence opacity) that the framework conflation doesn't mislead.
- **Account for age-specific coefficient shifts.** A 30-year-old and a 60-year-old see the same coefficients. Age-stratification deferred.
- **Touch demographic floors with real data.** v1 floor is `currentAge + 1` flat. The floor exists to prevent the chart from projecting death; precision below that bar isn't user-facing in v1.

## References

- Li et al., Circulation 2018 — 5 healthy lifestyle factors, ceiling +14y at age 50
- Paluch et al., Lancet Public Health 2022 — daily steps and all-cause mortality
- Jha et al., NEJM 2013 — 21st-Century Hazards of Smoking
- Doll & Peto, BMJ 2004 — quit-at-50/60 ladder
- Moore et al., PLOS Med 2012 — MVPA dose-response
- Cai et al., GeroScience 2025 — sleep U-curve, 79-cohort meta
- GBD 2020 alcohol, Lancet 2022 — no safe level
- WHO 2023 — alcohol consensus
- Mediterranean diet, JAMA Network Open 2024 — high-adherence effect size
- HALY/QALY/DALY unifying framework, ScienceDirect 2022
