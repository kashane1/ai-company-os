# UX and Game Loop

## Core loop

1. Open Today.
2. See clock movement.
3. Understand top drivers.
4. Complete one quest.
5. Log one optional habit.
6. Return tomorrow for updated trajectory.

## The game mechanic

The core game currency is **time**.

Not points. Not coins. Not XP.

Time is emotionally legible and directly connected to the concept.

## Main surfaces

### Today screen

Primary elements:

- Life Clock
- Today's delta
- confidence label
- top 3 drivers
- daily quests
- quick log

Example copy:

"+42 minutes today"

"Your strongest drivers were steps, sleep, and no alcohol logged."

### Time Ledger

Purpose: make the estimate explainable.

Example entries:

- +18 min - 9,800 steps - Apple Health
- +14 min - 43 exercise minutes - Apple Health
- +10 min - 7h 38m sleep - Apple Health
- -12 min - high stress logged - Self-report

### Quests

Quest types:

- movement quest
- sleep consistency quest
- strength quest
- nutrition quality quest
- risk reduction quest
- recovery/stress quest

Example quests:

- Walk 7,500 steps today.
- Take a 10-minute walk after dinner.
- Log no alcohol today.
- Complete 2 strength sessions this week.
- Be in bed by your target window.

### Weekly report

Example sections:

- Time earned this week
- Time lost this week
- Best driver
- Biggest drag
- Next best lever
- Confidence changes

## Tone modes

### Gentle

No death-date language. Uses healthspan score, time earned, and future-self framing.

### Coach

Default. Uses Life Clock but avoids harsh language.

### Firm/Direct (formerly "Memento Mori")

More dramatic. Uses direct countdown language, but still avoids medical certainty. Shipped enum identifier is `firmDirect` (see `Sources/App/ToneMode.swift`). The "Memento Mori" name lives only in this April 2026 founder-pack snapshot — see `vision.md` Decided constraints and the unnumbered `UX_GAME_LOOP.md` for the canonical name.

## Onboarding flow

1. Value screen: "Earn time back with better habits."
2. Safety screen: "Your clock is an estimate, not fate."
3. Baseline profile.
4. Tone mode.
5. Apple Health education.
6. Permission request.
7. First Life Clock reveal.
8. First quest.

## UX risk

The biggest UX risk is creating anxiety. The default should be motivating, not punishing.

Every negative delta should be paired with an actionable next step.
