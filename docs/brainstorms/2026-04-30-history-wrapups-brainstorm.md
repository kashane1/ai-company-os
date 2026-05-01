---
date: 2026-04-30
topic: history-wrapups
---

# History, Daily Wrap-Ups, and Historical Overrides

## What We're Building

We are evolving the current `Weekly` tab into a broader `History` surface. This becomes the permanent home for yesterday summaries, weekly summaries, and past-day reflection instead of treating wrap-ups as one-off moments with no place to revisit them.

The product should show a lightweight Yesterday Wrap-Up on first open of a new day when the prior day has enough data, then allow the user to find that same summary later inside `History`. The weekly summary follows the same pattern: it can appear as the higher-level periodic reflection moment, but it also lives inside `History` as something the user can revisit.

This is also the right place for a Pro feature that imports and surfaces past days of data. V1 should focus on the most recent 90 days. Free users get a meaningful but limited view. Pro users get browsing depth and editing power.

## Why This Approach

We considered keeping a narrow `Weekly` screen and adding Yesterday Wrap-Up elsewhere, but that would scatter reflection across the app. Turning the tab into `History` gives wrap-ups a clear long-term home and makes the tab useful every day, not just once a week.

We also considered making daily wrap-ups purely inline on Today, but that makes them easier to miss and gives them less emotional weight. The better middle ground is a brief, skippable first-open presentation plus a stable home in `History`.

For historical editing, we considered changing Apple Health data directly, but that creates trust and platform-boundary problems. The better approach is app-level overrides: Life Clock can score using corrected values without pretending to rewrite Apple Health.

## Key Decisions

- Rename `Weekly` to `History`: This screen becomes the archive and reflection surface, not just a weekly report.
- Use a first-open wrap-up moment plus permanent archive: Yesterday's Wrap-Up should appear briefly on first open of a new day when data exists, then remain available in `History`.
- Free tier gets `Yesterday + weekly preview`: Free users should feel complete, but not deep. They can see Yesterday's Wrap-Up and a weekly preview only.
- Pro unlocks depth: Pro users can browse all days from the current week, recent weekly summaries, and the rolling 90-day historical import in V1.
- Keep the emotional core free: Users should not need Pro to understand whether yesterday or this week moved them forward or backward.
- Historical import window is 90 days for V1: This is enough to feel substantial without overcomplicating the first pass.
- Pro can override HealthKit-derived values inside Life Clock: These edits affect Life Clock scoring and summaries, but do not rewrite Apple Health.
- Free can edit only local/manual signals: This preserves a meaningful paid distinction without making free unusable.
- Show `Adjusted` when an override exists: The default surface should show the corrected value. The original HealthKit value appears only when the user taps the `Adjusted` affordance for details.
- Preserve trust in the UI: Life Clock should clearly communicate that adjusted values are app-level corrections, not edits to Apple's Health database.

## Animation Direction

The strongest fit is a minimal clock animation tied to wrap-ups, not a constantly animated Today screen.

Recommended animation behavior:

- Daily wrap-up: a short clock-hand motion from 12:00 to the signed minute change for yesterday.
- Positive day: hands move clockwise.
- Negative day: hands move counterclockwise.
- Weekly wrap-up: same idea, but for the weekly net effect and with slightly more ceremony.
- If a value was adjusted, the motion should still feel calm and exact, not flashy or gamified.

This keeps animation meaningful, brandable, and easy to understand: the motion is the score.

## Non-Goals For This Slice

- Editing Apple Health directly.
- Unlimited historical import on V1.
- Heavy, full-screen ritual transitions everywhere in the app.
- Complex charts before the wrap-up and history model is proven.

## Next Steps

→ `/prompts:ce-plan` for implementation planning across navigation, data model, free-vs-Pro gating, wrap-up presentation, and override storage.
