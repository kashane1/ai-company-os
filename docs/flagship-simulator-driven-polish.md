# Flagship workflow: simulator-driven polish → App Store

This is one concrete, traced workflow end to end — the canonical example
of what the system actually does. Every file referenced here exists in the
repo; the Life Clock session logs cited at the end are real output from
this loop running, not illustrations.

The flow: **discover/define a product → build it for the simulator →
iteratively polish it against reference apps using screenshots →
hand off to an approval-gated App Store lane.**

## 1. The product and its intent

`life-clock-ios` is a health/longevity app the system produced. Its design
intent is pinned in `docs/products/life-clock/` (vision, briefs) and its
competitive bar is codified — not vibes — in
[`docs/products/life-clock/reference-apps.md`](products/life-clock/reference-apps.md):

- **Premium-feel reference:** *Death Clock: The Life Lab* — studied for
  reveal-animation timing and dramatic pacing.
- **Pro-value reference:** *MacroFactor* — studied for paywall hierarchy and
  adherence-neutral copy.

Crucially this file also encodes **binding refusals**: "match the craft,
reject the framing" — do not import Death Clock's mortality lexicon, do not
adopt MacroFactor's hard paywall. Reference learning with explicit
anti-patterns is the difference between studying a competitor and cloning
one.

## 2. Build for the simulator (deterministic state)

- [`scripts/preflight_xcode.sh`](../scripts/preflight_xcode.sh) verifies the
  `xcodebuild`/`xcodegen` chain from the daemon context and blocks the iOS
  lane on failure instead of failing deep in a run.
- [`scripts/test_ios.sh`](../scripts/test_ios.sh) auto-selects the newest
  available iPhone simulator (`xcrun simctl … | jq`), runs
  `xcodebuild test … -enableCodeCoverage YES`, then reports coverage.
- The polish loop can land on *any* reachable UI state deterministically
  via the seed harness in
  [`products/life-clock-ios/Sources/App/LifeClockLaunchConfiguration.swift`](products/life-clock-ios/Sources/App/LifeClockLaunchConfiguration.swift):
  env probes like `LIFECLOCK_JUMP_TO`, `LIFECLOCK_HEALTH_PROFILE`,
  `LIFECLOCK_SEED_BAD_DAY`. **Every probe is wrapped in `#if DEBUG`** so the
  fixture surface cannot exist in the App Store binary — a safety boundary,
  not just a test convenience.

## 3. The polish loop

Defined canonically in
[`skills/canonical/simulator-driven-polish/skill.md`](../skills/canonical/simulator-driven-polish/skill.md),
operator guide in
[`docs/skills/simulator-driven-polish-guide.md`](skills/simulator-driven-polish-guide.md),
traversal standardized in
[`docs/ux-audit-playbook.md`](ux-audit-playbook.md).

The loop screenshots the running app, compares against the reference
design-intent spec, fixes, and re-screenshots — bounded by explicit
safeguards:

- **Four modes:** `fix-list`, `freeform-polish`, `reference-match`,
  `vision-driven` (lower iteration cap, requires an acceptance pass).
- **Autonomy contract — four decision tiers:** Polish (auto-fix, silent
  commit) → Stretch (auto-fix, flag in session log) → Feature (always ask)
  → Vision-question (always ask). Asks are **batched at end of cycle**, not
  one interruption per finding.
- **Golden screenshot regression:** captures land in
  `products/life-clock-ios/.polish/goldens/<screen>.png`; a diff on a screen
  the fix did not touch is flagged as an unintended regression.
- **Two-recurrence rule:** if the same finding survives two fix attempts,
  the loop stops and escalates instead of thrashing.
- **Build-fail gate:** refuses to iterate past two consecutive build
  failures.
- **Vision is non-negotiable:** the loop may append Open Questions to
  `vision.md` but may never edit the "Decided constraints" section — that is
  operator-only.

Each session produces a stack of focused commits and an append-only,
date-stamped session log under `docs/products/life-clock/polish-*.md`.

## 4. Approval-gated App Store handoff

The iOS lane produces a release-ready build and stops. The App Store lane
([`docs/appstore-lane.md`](appstore-lane.md)) takes over and **never touches
application code**. It drafts metadata, manages screenshots, and validates a
submission checklist (`docs/products/<id>/submission-checklist.md`) —
refusing to proceed if it is incomplete. Positioning copy is produced by
[`skills/canonical/shared/app-store-positioning-pack.md`](../skills/canonical/shared/app-store-positioning-pack.md),
which is forbidden from promising features beyond `mvp-spec.md`.

Per [`docs/approval-policy.md`](approval-policy.md), the irreversible steps —
**TestFlight upload, App Review submission, public release** — each require
an explicit human approval gate. Everything up to that line is automated;
nothing past it happens without a person.

## 5. Why this is the flagship

This is the whole thesis in one workflow: an agent fleet does the slow,
real work of polishing a shipping app against a competitive bar, every
iteration is screenshot-audited and regression-checked, the autonomy
boundary is explicit and tiered, and the only irreversible action — putting
it in front of real users — is gated on a human.

**Evidence it actually ran** (real session logs, not examples):
`docs/products/life-clock/polish-2026-05-05.md`,
`polish-2026-05-06-accessibility-color-matrix.md`,
`polish-2026-05-06-plan-editor-pro-and-free-walk.md`, and ~20 more dated
logs in `docs/products/life-clock/`.
