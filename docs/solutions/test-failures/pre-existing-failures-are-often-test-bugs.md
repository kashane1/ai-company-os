---
title: "\"Pre-existing test failures\" in a PR handoff comment were all test bugs, not production bugs"
category: test-failures
date: 2026-04-14
tags:
  - triage
  - test-expectations
  - handoff
  - catchbook-ios
  - xctest
  - calendar-grid
  - wind-cardinal
  - seasonal-nudge
  - ux-stability
module: products/catchbook-ios
symptom: "A comment on a prior PR flagged three failing tests (`SeasonalNudgeCardTests.testSeasonalSpotFiresWithThreeOrMoreProductiveTrips`, `TripBrowseLogicTests.testMonthGridPadsLeadingAndTrailingCells`, `WeatherKitServiceTests.testDegreesToCardinalNegativeDegrees`) as 'pre-existing bugs in seasonal logic, calendar grid rendering, and wind cardinal conversion' that should be triaged separately. On investigation all three were wrong assertions in the tests themselves, not production defects."
root_cause: "Tests were committed in `d2779c1` with expectations derived from a mental model that didn't match what production actually computed. Because the navigation-restructure commit broke test compilation, the full suite was never run between the bad tests being written and the comment being filed — so nobody ever verified the expectations against production output. When the suite finally compiled, the failures surfaced and were reported upstream as production bugs without re-deriving the correct answers."
---

# "Pre-existing test failures" in a PR handoff comment were all test bugs, not production bugs

A handoff comment on a `catchbook-ios` PR flagged three failing tests as
pre-existing production bugs — "seasonal logic, calendar grid rendering,
and wind cardinal conversion" — and asked for them to be triaged in a
separate issue. Triaging found all three were test-side defects. Fixed
at commit `2d35df6` on `main`, alongside one genuine UX improvement
(min-5-row calendar policy) that the investigation surfaced as worth
doing anyway.

## Symptom

Running the Catchbook test suite produced three failures:

```
SeasonalNudgeCardTests.swift:159: XCTAssertTrue failed
  testSeasonalSpotFiresWithThreeOrMoreProductiveTrips

TripBrowseLogicTests.swift:54: XCTAssertEqual failed: ("28") is not equal to ("35")
  testMonthGridPadsLeadingAndTrailingCells

WeatherKitServiceTests.swift:76: XCTAssertEqual failed: ("N") is not equal to ("NNW")
  testDegreesToCardinalNegativeDegrees
```

The failures had been blaming production functions: `seasonalSpotCards`,
`TripBrowseLogic.monthGrid`, and `WeatherKitService.degreesToCardinal`.

## Investigation

Derived the correct answer for each assertion from first principles
rather than trusting either the test or the existing production code.

### 1. Wind cardinal — `-10° → "NNW"`

Test comment said `// -10 degrees should normalize to 350 degrees (NNW)`.
A 16-point compass has 22.5° sectors: N is centered at 0° and spans
348.75°–11.25°. So 350° is in the **N** sector, not NNW. The test
expectation (and its own comment) was wrong. Production was correct.

### 2. Calendar grid — Feb 2026 grid expected 35 cells, got 28

Test hardcoded February 2026 as the displayed month. With a
Sunday-first Gregorian calendar, Feb 1 2026 is a Sunday and February
has 28 days, so the month fits exactly in 4 rows. Production's rule at
the time was "round up to the nearest whole week," yielding 28 cells.

The test expected 35 (i.e. at least 5 rows). The only way to satisfy
it is to add a minimum-row policy to production. That's a UX decision,
not a bug fix — but it was the right call anyway because a 4-row
February would cause the surrounding layout to jitter when paging
between months. Adopted the min-5-row policy.

### 3. Seasonal spot — asserted spot name in card `body`

Test asserted:

```swift
XCTAssertTrue(seasonalCards.first?.body.contains("River Bend") ?? false)
```

Production produces a card with:

- `title`: `"Spring at River Bend"`
- `body`:  `"Spring has been your strongest season there — 3 productive trips."`

The spot name lives in the title by design. The assertion was targeting
the wrong field. Production was correct.

## Root Cause

The three tests were committed in `d2779c1` (`Add calendar gallery and
catch map browsing to Catchbook`). In the same commit window, a
navigation restructure (`d08cf6e`) broke test compilation by removing
symbols the test target still referenced. Because the suite never
compiled, these three always-wrong tests were never exercised —
they shipped as latent test debt.

When a later commit (`658c787`) fixed the compilation breakage, these
three started reporting failures for the first time. The PR author
saw unfamiliar failing tests, assumed they were pre-existing production
bugs in "seasonal logic, calendar grid rendering, and wind cardinal
conversion," and deferred them via a comment.

The flawed step was attribution without verification: once a test and
production disagree, you cannot tell which side is wrong without
deriving the correct answer from first principles. In all three cases
the comment named the production component as the culprit; in all
three cases production was right.

## Fix

Three test corrections and one production policy improvement.

### 1. `Tests/Services/WeatherKitServiceTests.swift`

```swift
func testDegreesToCardinalNegativeDegrees() {
    // -10 degrees normalizes to 350 degrees, which falls in the N sector
    // (N covers 348.75°–11.25°).
    XCTAssertEqual(degreesToCardinalHelper(-10), "N")
}
```

### 2. `Tests/Features/Home/SeasonalNudgeCardTests.swift`

```swift
let seasonalCards = cards.filter { $0.kind == .seasonalSpot }
XCTAssertEqual(seasonalCards.count, 1)
// Spot name lives in the title ("Spring at River Bend"), season in the body.
XCTAssertTrue(seasonalCards.first?.title.contains("River Bend") ?? false)
XCTAssertTrue(seasonalCards.first?.body.contains("Spring") ?? false)
```

### 3. `Sources/Features/Trips/TripBrowseLogic.swift` — min-5-row policy

```swift
// Pad to a whole number of weeks, with a minimum of 5 rows so the
// calendar height stays stable month-to-month. A 28-day February that
// starts on a Sunday would otherwise render as 4 rows and cause the
// surrounding layout to jump when paging between months.
let minimumCells = 35
let weekAligned = cells.count.isMultiple(of: 7) ? cells.count : cells.count + (7 - cells.count % 7)
let targetCount = max(weekAligned, minimumCells)
let trailingCount = targetCount - cells.count
```

After the changes, all 307 tests pass.

## Prevention

### Process: never trust a bug attribution without re-deriving the answer

When a comment or handoff note says "this test is failing due to a bug
in X," treat that as a hypothesis, not a finding. Before filing or
deferring the issue:

1. Compute the correct answer from first principles (in this case: what
   does a 16-point compass say about 350°? what does Feb 2026 look like
   on a Sunday-first calendar? what does the production card actually
   render?).
2. Compare the correct answer against BOTH the test expectation and
   the production output.
3. Fix whichever side is wrong.

A "pre-existing failure" framing often encodes an assumption that
production is to blame, because test bugs in committed code should have
been caught by the original PR. That assumption is wrong whenever the
suite hasn't been green recently — in which case the first full run
after a compilation fix will flush out test debt that looks like a
production regression.

### Process: run the full suite before attributing failures in handoff comments

The navigation restructure broke test compilation, and the immediate
fix (`658c787`) patched the compilation-blocking tests only. That was
the right shortest-path move to unblock the refactor, but the
follow-up comment should have been "three tests newly exercised by the
compilation fix are failing — needs triage," not "three pre-existing
production bugs in modules X/Y/Z." The framing drove incorrect
downstream assumptions.

### Code: document why fixed grid sizes exist

Calendar widgets commonly pad to a minimum row count for layout
stability, but it's easy to forget why. The production comment now
explains the Feb-2026-starts-on-Sunday edge case inline so the next
reader doesn't delete the padding as apparently-dead code.

## Related

- `658c787` — previous test fix commit that patched compilation-blocking
  tests from the navigation restructure (but left these three
  latent-failing tests untouched because they still compiled).
- `d2779c1` — commit that introduced the three bad test expectations
  alongside the original calendar-gallery / catch-map feature.
- `d08cf6e` — navigation restructure that broke test compilation and
  kept the suite red until `658c787` landed.
- `ae043cd` — `docs/solutions/partial-refactor-gate-anti-pattern.md`
  captures the adjacent lesson about partial refactors shipping with
  broken tests.
