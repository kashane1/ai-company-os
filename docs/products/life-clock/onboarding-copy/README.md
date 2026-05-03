# Life Clock — onboarding copy versions

This folder is the canonical archive of every shipped version of Life
Clock's onboarding copy. Each `v{N}.md` is a frozen snapshot of the
titles, body text, options, and button labels for every onboarding
screen as they were shipped during a specific date range.

The point is to be able to answer, six months from now: *"What copy
were users seeing in March, and how did it convert vs. what we shipped
in May?"* That requires knowing the exact strings, not just diffs in
git.

## Conventions

- One file per version: `v1.md`, `v2.md`, `v3.md`, …
- Each file has YAML frontmatter with `version`, `start_date`,
  `end_date` (or `current` if it's the live version), and a one-line
  `summary` of what changed vs. the previous version.
- Body is in screen-flow order, with the screen ID in a heading and
  the user-visible copy verbatim. Use `[mascot animation here]` (or
  similar) for non-text elements that shouldn't be quoted.
- When you ship a new version, set the previous version's `end_date`
  to the day before the new one's `start_date`. Do not edit prior
  versions otherwise — they're history, not docs.

## How to use this with conversion data

When analyzing a conversion experiment, link back to the version file
that was live during the analysis window. The `start_date` /
`end_date` fields make it cheap to filter analytics by which copy a
user actually saw.

## Source of truth

The Swift code in `products/life-clock-ios/Sources/Features/Onboarding`
is the runtime source of truth. These files are the human-readable
mirror — they should match the code at any moment, but the code wins
if they ever drift.
