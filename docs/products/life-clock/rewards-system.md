# Life Clock Rewards System

## What Exists Today

- Daily delta in minutes
- Top driver list
- A small set of daily actions
- Progress log entries for completed actions
- Diet logging streaks

## What Was Missing

- A clear immediate reinforcement moment after good actions
- A visible cumulative summary tying today's actions together
- More supportive wording around reward estimates
- Durable completion state across refresh and relaunch
- A calmer split between celebratory moments and reflective moments

## Recommendation

### Reward types

- Immediate support moments
- Daily momentum summary
- Visible action completion count
- Progress-log proof
- Weekly trend reflection

### Triggers

- onboarding completion
- saving a daily check-in
- completing a planned action
- strength-training logs
- streak continuation

### Frequency

- Immediate support moments: once per meaningful action
- Momentum summary: always visible on Today
- Weekly reflection: once per weekly visit

### Tone

- Calm by default
- Brief celebration only when the user actually did something beneficial
- Never imply certainty or overclaim outcomes

### Immediate vs cumulative

- Immediate: support card, saved check-in confirmation, action completion feedback
- Cumulative: momentum count, progress log, streaks, weekly pattern review

### Celebratory vs calm

- Celebratory: positive check-in changes, completed planned actions, strength training logs
- Calm: onboarding completion, neutral check-in saves, undo states, no-data guidance

## Changes To Ship Now

- Replace game-like copy with supportive progress language
- Show a support moment card on Today
- Add a momentum summary card on Today
- Persist completed action state across refresh and relaunch
- Use "Potential +X min" instead of bare reward numbers
- Reduce repeated disclaimer friction in primary flows

## Later-Phase Additions

- Weekly milestone summaries
- Trend-based encouragement based on sustained improvement
- Better distinction between "you logged" and "Health detected"
- Thoughtful milestone copy for streaks and consistency thresholds
- Optional visual regression coverage for high-value screens

## Guardrails

- Do not add badges for their own sake.
- Do not celebrate every tap equally.
- Do not present rewards as medical truth.
- Do not punish rough days; pair them with a next-step suggestion.
