---
description: Drive an iOS app live in Simulator, identify gaps with explicit decision authority (Polish/Stretch/Feature/Vision-question), fix them in tight commits, and surface only the decisions that need the operator. Modes — fix-list, freeform-polish, reference-match, vision-driven.
canonical_source: skills/canonical/simulator-driven-polish/skill.md
---

# Simulator-Driven Polish — Claude adapter

Follow the canonical procedure at `skills/canonical/simulator-driven-polish/skill.md`. This adapter is Claude-specific runtime guidance — read it once at session start, then drive off the canonical body for the contract.

This is the **editing** counterpart to `ios-simulator-ux-audit`. That skill audits and reports without changing code. This skill audits AND edits AND commits, under the explicit decision layer in the canonical body.

## Confirm before you start

Surface these inputs explicitly to the operator (do not silently guess):

- `product_id` and the product path under `products/<product-id>-ios/`
- Xcode scheme (verify with `xcodebuild -list -project ...`)
- Simulator device + iOS (default — newest installed iPhone via `xcrun simctl list devices available`)
- **Mode**: `fix-list` | `freeform-polish` | `reference-match` | `vision-driven`
- Mode payload: the fix list, the reference slot path, or "use vision.md"
- Iteration cap (default 8 in polish/reference, 6 in vision)
- `final_check`: opt-in for the computer-use acceptance pass; mandatory in vision mode

If working tree is dirty, ask before starting. If `vision-driven` and `vision.md` is missing, offer bootstrap (interview-style) before any code work.

## Tools to reach for, in order

**Build / run:**

- `xcodebuild -list -project <path>` — confirm scheme.
- `xcrun simctl list devices available` — pick deterministic device.
- `xcodebuild ... -destination 'platform=iOS Simulator,name=...'` — headless build (use the existing `ios-build-and-sign` path; do NOT open Xcode).
- `xcrun simctl boot|install|launch` — drive the device.
- The product's launch-config env-vars (e.g. `LIFECLOCK_UI_TEST_SCENARIO=onboarded`) — pick the right seed.

**Drive the app:**

- **Accessibility tree first** — cheap, deterministic. ~10 tokens vs ~3k for a screenshot. Use AX-tree dump every iteration; only screenshot when the tree is insufficient.
- Screenshots — one per visited screen per iteration, saved as goldens under `products/<product-id>-ios/.polish/goldens/<screen>.png`.
- `simctl spawn ... log stream` — surface NEW warnings/errors only; ignore baseline noise.
- **Computer-use** — reserve for: gestures AX-tree can't express; the final acceptance checkpoint. Always check frontmost app before using.

**Reference-match mode extras:**

- `gemini-imagegen` skill — for brand-asset generation matching reference palette/style.
- `frontend-design` skill — for design-intent extraction prompts.
- `content-voice-guardrail` (canonical) — for matching copy voice.

**Vision-driven mode extras:**

- Read `docs/products/<product-id>/vision.md` at the start of every cycle.
- Read prior session logs under `docs/products/<product-id>/polish-*.md` for accumulated context.
- The user's auto-memory — convention memories (e.g. lighting convention) act as additional observers.

## Per-iteration loop (Claude rhythm)

1. AX-tree dump of the screen under work.
2. Compare to the mode's observer (fix list / design system / reference intent / vision).
3. Generate findings; classify each into **Polish / Stretch / Feature / Vision-question**.
4. Pick highest-impact Polish or Stretch finding. Edit. Rebuild headlessly.
5. Re-drive the same flow. Re-dump AX-tree. Recapture goldens for changed screens; diff goldens for screens you did NOT touch and flag any unintended diffs.
6. If green: commit (`<type>(<product>): <one-line>`), one fix per commit. Append one line to the session log.
7. If a driven element lacked an `accessibilityIdentifier`, add one in source and commit `chore(<product>): a11y id for <element>`. This compounds across sessions — do NOT skip it.
8. If two recurrences of the same finding → stop, queue as Ask, move on or end cycle.

## When to STOP and ask (cycle-end batch — not per finding)

Queue Asks during the cycle; surface them in ONE batched prompt at cycle close:

- Any **Feature**-tier finding (always Ask, no exceptions).
- Any **Vision-question** (no clear precedent in vision.md or memory).
- Any direction with two valid alternatives where you cannot pick on evidence.
- Any contradiction with `Decided constraints` in vision.md.
- Reference-match: a recognizable third-party app would be visually cloned (escalate; "translate, don't clone").

For each Ask in the batch, include: a short statement, the relevant screenshot, and 2–3 concrete options with tradeoffs. Do not let Asks dribble in one at a time — operators hate that.

## Commit style (matches existing life-clock cadence)

- One logical fix per commit. Short imperative subject.
- Prefix: `feat(<product>):` / `fix(<product>):` / `chore(<product>):`. Examples:
  - `fix(life-clock): thinner mascot bezel rim`
  - `feat(life-clock): persistent mascot header + v2 onboarding copy`
  - `chore(life-clock): a11y id for history.row`
- Body optional; only add when WHY isn't obvious from the subject + diff.

## Session log

Path: `docs/products/<product-id>/polish-<YYYY-MM-DD>-<slug>.md`. Structured per the canonical Output Style.

**Pick the slug at session start.** 2–5 kebab-case words that describe the session's focus, derived from the operator's idea + mode. Examples:

- `polish-2026-05-05-today-screen-morning-greeting.md`
- `polish-2026-05-05-history-density-match.md`
- `polish-2026-05-05-vision-day7-returning-user.md`
- `polish-2026-05-05-fix-list-onboarding-back-nav.md`

Surface the slug to the operator before starting and let them override if it doesn't read right. If the file already exists, append `-2`, `-3`, etc. Don't merge unrelated work into one file. Same-day continuation (paused mid-session, resumed) MAY append `## Session HH:MM` H2 to the existing file — but only with operator confirmation that it is a continuation.

The log IS the handoff — keep it complete enough that the PR body can be derived directly from it.

## At session end

1. Run a changed-surface check (`verification-loop` or its lighter variant) on the diff.
2. Confirm goldens for touched screens are intentional; revert any unintended regressions or surface as Ask.
3. Emit a PR body derived from the session log: summary line, list of commits with rationale, screenshots for visually-meaningful changes, queued Asks (resolved + outstanding), "next pass" section.
4. If `final_check=true` (or vision mode): run the computer-use acceptance pass before declaring done.
5. Memory ratchet: when an Ask resolves with a generally-applicable rule (like the lighting convention), save to memory. With operator approval, also append to `Decided constraints` in vision.md.

## Boundaries (don't cross)

- Edit only `products/<product-id>-ios/**` and `docs/products/<product-id>/**`. Forbidden: `packages/policies/`, `state/`, other products.
- Never edit `vision.md`'s `## Decided constraints` section. Operator-only. Append to `## Open Questions` is fine.
- Never introduce a new feature autonomously. Propose, don't ship.
- Never deploy / ship / archive — chain to `ios-to-appstore-handoff` for that.
- Never run autonomously past a non-launching app. Fix the crash first; if you can't, stop and ask.

## Failure handling

The canonical body lists the failure modes. Claude-specific notes:

- **Build fails 2 cycles in a row that the loop introduced** → stop, paste the diagnostic, ask. Do not try a third time.
- **AX-tree dump returns nothing meaningful** → take one screenshot, compare, and either fix the missing `accessibilityElement` or fall back to computer-use for that one screen — note in session log.
- **Reference is ambiguous** (operator dropped a single image with no context) → ask which dimension matters most: palette, layout, motion, copy.
- **Vision interview produces a vision.md the operator hasn't approved** → save it as a draft (`vision.draft.md`); first cycle is review-only.

## Disambiguation

If the operator's request could route to either `ios-simulator-ux-audit` (review-only) OR this skill (review + edit), ASK. Never silently route. Trigger phrases for *this* skill imply editing; trigger phrases for the audit imply reporting.
