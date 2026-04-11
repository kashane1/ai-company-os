# Manual QA Pass: Catchbook v1.0

Structured test scenarios for manual QA before App Store submission. Run these on a physical iPhone via TestFlight.

Last updated: 2026-04-09

---

## Test Environment

- Device: iPhone running iOS 17.0+
- Network: Test both with WiFi/cellular AND in Airplane Mode
- Location: Test with location services ON and OFF
- Photos: Test with photo access granted AND denied

---

## 1. First Launch

| # | Scenario | Expected | Pass? |
|---|----------|----------|-------|
| 1.1 | Fresh install, launch app | App launches without crash, shows Home tab | |
| 1.2 | Location permission prompt appears | Alert with "Capture trip locations privately..." message | |
| 1.3 | Deny location permission | App continues to work, location fields show fallback text | |
| 1.4 | Grant location permission | Location populates in condition preview | |

## 2. Waterbody & Spot Creation

| # | Scenario | Expected | Pass? |
|---|----------|----------|-------|
| 2.1 | Create waterbody (lake, "Test Lake") | Saves, appears in picker | |
| 2.2 | Create waterbody with very long name (50+ chars) | Saves, truncates gracefully in UI | |
| 2.3 | Create spot under waterbody | Saves, linked to correct waterbody | |
| 2.4 | Create spot with coordinates | Coordinates display in spot detail | |

## 3. Trip Logging Flow

| # | Scenario | Expected | Pass? |
|---|----------|----------|-------|
| 3.1 | Start trip with waterbody selected | Trip starts, conditions captured, weather enrichment attempted | |
| 3.2 | Start trip in Airplane Mode | Trip starts successfully, weather fields show "Weather data unavailable" | |
| 3.3 | Start trip with location denied | Trip starts with fallback coordinates from waterbody/spot | |
| 3.4 | Verify weather data populates (online) | Temperature, wind, cloud cover, precipitation shown | |

## 4. Catch Logging

| # | Scenario | Expected | Pass? |
|---|----------|----------|-------|
| 4.1 | Log catch with all fields (species, weight, length, lure, method, note) | All fields persist correctly | |
| 4.2 | Log catch with only species | Saves without crash, optional fields show as empty | |
| 4.3 | Log catch with photo | Photo saves, thumbnail displays in catch detail | |
| 4.4 | Log catch, deny photo access | Photo picker unavailable, catch still saves without photo | |
| 4.5 | Log multiple catches in one trip | All catches appear in trip detail | |
| 4.6 | Quick-catch flow | Saves immediately, confirmation banner appears | |

## 5. Trip End

| # | Scenario | Expected | Pass? |
|---|----------|----------|-------|
| 5.1 | End trip with catches | Outcome shows "Caught", summary shows catch count | |
| 5.2 | End trip with zero catches | Outcome shows "Skunked" | |
| 5.3 | End trip summary displays | Duration, top species, conditions shown | |

## 6. History & Browsing

| # | Scenario | Expected | Pass? |
|---|----------|----------|-------|
| 6.1 | View Trips tab | Past trips listed, most recent first | |
| 6.2 | Filter by waterbody | Only trips at selected waterbody shown | |
| 6.3 | Filter by species | Correct trips surface | |
| 6.4 | Filter by season | Correct seasonal grouping | |
| 6.5 | View Spots tab | All spots listed with waterbody info | |
| 6.6 | Spot detail shows history | Trip count, catch count, recent catches display | |

## 7. Insights

| # | Scenario | Expected | Pass? |
|---|----------|----------|-------|
| 7.1 | View insights after 3+ trips | Deterministic insight cards appear | |
| 7.2 | Insight cards cite data correctly | Best time, top lure, seasonal patterns match logged data | |
| 7.3 | No speculative or AI-generated advice | All insights traceable to user's own data | |

## 8. Share Card

| # | Scenario | Expected | Pass? |
|---|----------|----------|-------|
| 8.1 | Export share card from catch detail | Card renders with species, size, photo | |
| 8.2 | Share card omits location by default | No spot name, waterbody, coordinates visible | |
| 8.3 | Share card export works offline | Generates from local data | |

## 9. Backup/Export

| # | Scenario | Expected | Pass? |
|---|----------|----------|-------|
| 9.1 | Export backup from Home toolbar | .flbackup file created, share sheet appears | |
| 9.2 | Backup includes all entities | Waterbodies, spots, trips, catches, photos in package | |

## 10. Edge Cases

| # | Scenario | Expected | Pass? |
|---|----------|----------|-------|
| 10.1 | Empty state (no waterbodies) | Helpful empty state with "Add your first water" prompt | |
| 10.2 | Kill app during active trip, relaunch | Active trip persists, can resume or end | |
| 10.3 | Rapidly tap "Start Trip" twice | Only one trip created (no duplicates) | |
| 10.4 | Rotate device (if supported) | UI doesn't break (portrait-locked is fine) | |
| 10.5 | Dark mode | All text readable, brand colors appropriate | |
| 10.6 | Dynamic Type (large text) | UI remains usable at largest text size | |
| 10.7 | Low storage warning | App handles gracefully (SwiftData write failures) | |

---

## Sign-Off

| Role | Name | Date | Result |
|------|------|------|--------|
| QA tester | | | |
| Developer | | | |
